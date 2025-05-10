from utils.mongodb_schemas import spaces_collection, presets_collection, projects_collection
from models.pydantic_models import CreatePresetRequest, UpdatePresetRequest
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from utils.env_variables import S3_BUCKET_NAME
from models.pydantic_models import AccessPreset
from utils.log_errors import logger
import uuid, boto3

router = APIRouter()
s3 = boto3.resource('s3')

@router.post('/create_preset/', tags=['Preset'])
async def create_preset(request: CreatePresetRequest):
    existing_space = spaces_collection.find_one({'space_id': request.space_id})
    if not existing_space:
        raise HTTPException(status_code=404, detail='Space does not exist')

    preset_id = str(uuid.uuid4())
    preset = {
        'preset_id': preset_id,
        'name': request.name,
        'color': request.color,
        'options': request.options,
        'media_ids': request.media_ids,
        'space_id': request.space_id,
        'spaces': [request.space_id]
    }
    presets_collection.insert_one(preset)
    return {'message': 'Preset created successfully', 'preset_id': preset_id}

@router.post('/update_preset/', tags=['Preset'])
async def update_preset(request: UpdatePresetRequest):
    existing_space = spaces_collection.find_one({'space_id': request.space_id})
    if not existing_space:
        raise HTTPException(status_code=404, detail='Space does not exist')
    updated_preset = presets_collection.find_one_and_update(
        {'preset_id': request.preset_id},
        {
            '$set': {
                'name': request.name,
                'color': request.color,
                'options': request.options,
                'media_ids':request.media_ids
            }
        },
    )
    if not updated_preset:
        raise HTTPException(status_code=404, detail='Preset not found')
    return {'message': 'Preset updated successfully'}

@router.get('/get_presets/', tags=['Preset'])
async def get_presets(space_id: str = Query(...)):
    space = spaces_collection.find_one({'space_id': space_id})
    if not space:
        raise HTTPException(status_code=404, detail='Space not found')
    presets = []
    for preset in list(presets_collection.find({'spaces': {'$in': [space_id]}})):
        if not preset:
            return HTTPException(status_code=500, detail='Preset not found')
        if preset:
            temp = {
                'preset_id': preset['preset_id'],
                'name': preset.get('name'),
                'color': preset.get('color'),
                'options': preset.get('options'),
                'media_ids': preset.get('media_ids'),
                'isOwner': True if preset.get('space_id')==space_id else False
            }
            presets.append(temp)
    return {'presets': presets}

def delete_preset_clips(files: list):
    for file in files:
        try:
            file_key = '/'.join(file['preset_clip_link'].split('/')[-2:])
            s3.Object(S3_BUCKET_NAME, file_key).delete()
            projects_collection.delete_one({'preset_clip_id': file['preset_clip_id']})
        except Exception as e:
            logger.error(f"Error deleting file {file['preset_clip_link']}: {e}")
            continue

@router.delete('/delete_preset/', tags=['Preset'])
async def delete_preset(space_id: str = Query(...), preset_id: str = Query(...), backgroundtasks: BackgroundTasks = BackgroundTasks(None)):
    space = spaces_collection.find_one({'space_id': space_id})
    if not space:
        raise HTTPException(status_code=404, detail='Space does not exist')
    preset_clips = list(projects_collection.find({'preset_id': preset_id}))
    if preset_clips:
        backgroundtasks.add_task(delete_preset_clips, preset_clips)
    delete_result = presets_collection.delete_one({'preset_id': preset_id})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Preset not found in preset collection')
    return {'message': 'Preset deleted successfully'}

@router.post('/grant_preset_access/', tags=['Preset Sharing'])
async def grant_preset_access(request: AccessPreset):
    try:
        preset_info = presets_collection.find_one({'preset_id': request.preset_id, 'space_id': request.space_id})
        if not preset_info:
            raise HTTPException(status_code=404, detail='Preset not found')
        spaces_list = []
        for space_info in request.spaces:
            spaces_list.append(space_info['space_id'])
        presets_collection.update_one({'preset_id': request.preset_id}, {'$set': {'spaces': spaces_list}})
        return {'message': 'Preset access granted successfully.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error granting access to preset: {e}')
    
@router.get('/fetch_shared_spaces/', tags=['Preset Sharing'])
async def fetch_shared_spaces(preset_id: str = Query(...)):
    preset_info = presets_collection.find_one({'preset_id': preset_id})
    if not preset_info:
        raise HTTPException(status_code=404, detail=f'Preset not found.')
    spaces = []
    for spaceid in preset_info['spaces']:
        space_info = spaces_collection.find_one({'space_id': spaceid})
        if not space_info:
            continue
        spaces.append({'space_id': spaceid, 'space_name': space_info['name'], 'owner': True if preset_info['space_id']==spaceid else False})
    return {'spaces': spaces}