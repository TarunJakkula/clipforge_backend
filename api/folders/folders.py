from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from models.pydantic_models import CreateFolder
from utils.env_variables import S3_BUCKET_NAME
from models.pydantic_models import AccessFolder
from utils.log_errors import logger
from utils.mongodb_schemas import *
import uuid, boto3

router = APIRouter()
s3 = boto3.resource('s3')

@router.post('/create_folder/', tags=['Folder'])
async def create_folder(request: CreateFolder):
    try:
        if request.parent_id == 'root':
            spaces = [request.space_id]
        else :
            parent_info = folders_collection.find_one({'folder_id': request.parent_id})
            spaces = parent_info['spaces'] + [request.space_id]
        folder_id = str(uuid.uuid4())
        folders_collection.insert_one({
            'folder_id': folder_id,
            'folder_name': request.folder_name,
            'category': request.category,
            'parent_id': request.parent_id,
            'space_id': request.space_id,
            'spaces': spaces
        })
        return {'message': 'Folder created successfully', 'folder_id': folder_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail='Folder creation failed')

@router.get('/fetch_folders/', tags=['Folder'])
async def fetch_folders(parent_id: str = Query(...), category: str = Query(...), space_id: str = Query(...)):
    if parent_id != 'root':
        parent_info = folders_collection.find_one({'folder_id': parent_id})
        if not parent_info:
            raise HTTPException(status_code=404, detail='Folder not found')
    else :
        parent_info = {'space_id': space_id}
    try:
        folders_cursor = folders_collection.find({'parent_id': parent_id, 'category': category, 'spaces': {'$in': [space_id]}})
        folders = [{'id': folder['folder_id'], 'name': folder['folder_name'], 'parent': folder['parent_id'], 'owner_id': folder['space_id']} for folder in folders_cursor]
        return {'folders': folders, 'parent_id': parent_id, 'owner_id': parent_info['space_id']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Folder fetching failed: {str(e)}')
    
def delete_files(files: list):
    for file in files:
        try:
            file_key = '/'.join(file['file_storage_link'].split('/')[-2:])
            s3.Object(S3_BUCKET_NAME, file_key).delete()
            if file['file_storage_link'].split('/')[-2] == 'broll':
                brolls_collection.delete_one({'file_id': file['file_id']})
                tasks_collection.delete_many({'file_id': file['file_id'], 'category': 'broll'})
            elif file['file_storage_link'].split('/')[-2] == 'music':
                music_collection.delete_one({'file_id': file['file_id']})
                tasks_collection.delete_many({'file_id': file['file_id'], 'category': 'music'})
        except Exception as e:
            logger.error(f"Error deleting file {file['file_storage_link']}: {e}")

def delete_folders(folders: list):
    for sub_folder in folders:
        sub_folders = list(folders_collection.find({'parent_id': sub_folder['folder_id']}))
        brolls = list(brolls_collection.find({'parent_id': sub_folder['folder_id']}))
        music = list(music_collection.find({'parent_id': sub_folder['folder_id']}))
        delete_files(brolls)
        delete_files(music)
        
        if sub_folders:
            delete_folders(sub_folders)
    try:
        folders_collection.delete_one({'folder_id': sub_folder['folder_id']})
    except Exception as e:
        logger.error(f"Error deleting folder {sub_folder['folder_id']}: {e}")

def deleting_process(folder_id: str):
    try:
        folders = list(folders_collection.find({'parent_id': folder_id}))
        brolls = list(brolls_collection.find({'parent_id': folder_id}))
        music = list(music_collection.find({'parent_id': folder_id}))
        delete_files(brolls)
        delete_files(music)
        if folders:
            delete_folders(folders)
        folders_collection.delete_one({'folder_id': folder_id})
        return {'message': 'Subfolders and files deleted successfully.'}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting folder {folder_id}: {e}")
    
@router.delete('/delete/', tags=['Delete', 'Folder'])
async def delete_folder(id: str = Query(...), category: str = Query(...), space_id: str = Query(...), backgroundtasks: BackgroundTasks = BackgroundTasks()):
    try:
        if category == 'folder':
            folder_info = folders_collection.find_one({'folder_id': id})
            if not folder_info:
                raise HTTPException(status_code=404, detail='Folder not found.')
            if space_id!=folder_info['space_id']:
                return HTTPException(status_code=403, detail='You are not authorized to delete this folder.')
            backgroundtasks.add_task(deleting_process, id)
            return {'message': 'Folder deletion initiated.'} 
        elif category == 'broll':
            file_data = brolls_collection.find_one({'file_id': id})
            delete_files([file_data])
        elif category == 'music':
            file_data = music_collection.find_one({'file_id': id})
            delete_files([file_data])
        else:
            raise HTTPException(status_code=400, detail='Invalid category.') 

        return {'message': 'File deleted successfully.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while deleting: {e}")

@router.get('/fetch_spaces_of_user/', tags=['Folder Sharing', 'Preset Sharing'])
async def fetch_spaces_of_user(email: str = Query(...)):
    try:
        user_info = users_collection.find_one({'email': email})
        if not user_info:
            return {'spaces': []}
        spaces = list(spaces_collection.find({'user_id': user_info['user_id']}))
        spaces_names = [{'space_id': space['space_id'], 'space_name': space['name']} for space in spaces]
        
        return {'spaces': spaces_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error fetching spaces: {e}')
    
@router.get('/fetch_shared_spaces_folders/', tags=['Folder Sharing'])
async def fetch_shared_spaces(folder_id: str = Query(...), space_id: str = Query(...)):
    folder_info = folders_collection.find_one({'folder_id': folder_id, 'space_id': space_id})
    if not folder_info:
        raise HTTPException(status_code=404, detail=f'Folder not found.')
    spaces = []
    for spaceid in folder_info['spaces']:
        space_info = spaces_collection.find_one({'space_id': spaceid})
        if not space_info:
            continue
        spaces.append({'space_id': spaceid, 'space_name': space_info['name'], 'owner': True if folder_info['space_id']==spaceid else False})
    return {'spaces': spaces}

@router.post('/grant_folder_access/', tags=['Folder Sharing'])
async def grant_folder_access(request: AccessFolder):
    try:
        folder_info = folders_collection.find_one({'folder_id': request.folder_id, 'space_id': request.space_id})
        if not folder_info:
            raise HTTPException(status_code=404, detail='Folder not found.')
        spaces_list = []
        for space_info in request.spaces:
            spaces_list.append(space_info['space_id'])
        folders_collection.update_one({'folder_id': request.folder_id}, {'$set': {'spaces': spaces_list}})
        folders_collection.update_many({'parent_id': request.folder_id}, {'$set': {'spaces': spaces_list}})
            
        if request.category == 'broll':
            brolls_collection.update_many({'parent_id': request.folder_id}, {'$set': {'spaces': spaces_list}})
        elif request.category == 'music':
            music_collection.update_many({'parent_id': request.folder_id}, {'$set': {'spaces': spaces_list}})
        return {'message': 'Folder access granted successfully.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error granting access: {e}')