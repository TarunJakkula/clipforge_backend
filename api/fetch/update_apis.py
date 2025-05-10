from models.pydantic_models import Move, Rename, EditTags
from fastapi import APIRouter, HTTPException
from utils.mongodb_schemas import *

router = APIRouter()

@router.post('/update_name/', tags=['Rename'])
async def update_name(request: Rename):
    if request.category not in ['folder', 'broll', 'music', 'clip', 'subclip', 'remixclip']:
        raise HTTPException(status_code=422, detail='Invalid Category')
    if request.category=='folder':
        folder_info = folders_collection.find_one({'folder_id': request.id})
        if not folder_info:
            raise HTTPException(status_code=404, detail='Folder not found')
        folders_collection.update_one(
            {'folder_id': request.id},
            {'$set':{'folder_name': request.name}}
        )
    elif request.category=='broll':
        broll_info = brolls_collection.find_one({'file_id': request.id})
        if not broll_info:
            raise HTTPException(status_code=404, detail='broll not found')
        brolls_collection.update_one(
            {'file_id': request.id},
            {'$set':{'file_name': request.name}}
        )
    elif request.category=='music':
        music_info = music_collection.find_one({'file_id': request.id})
        if not music_info:
            raise HTTPException(status_code=404, detail='music not found')
        music_collection.update_one(
            {'file_id': request.id},
            {'$set':{'file_name': request.name}}
        )
    elif request.category=='clip':
        clip_info = clips_collection.find_one({'clip_id': request.id})
        if not clip_info:
            raise HTTPException(status_code=500, detail='Clip not found')
        clips_collection.update_one(
            {'clip_id': request.id},
            {'$set':{'clip_name': request.name}}
        )
    elif request.category=='subclip':
        subclip_info = subclips_collection.find_one({'subclip_id': request.id})
        if not subclip_info:
            raise HTTPException(status_code=500, detail='Sublip not found')
        subclips_collection.update_one(
            {'subclip_id': request.id},
            {'$set':{'subclip_name': request.name}}
        )
    elif request.category=='remixclip':
        remixed_clip_info = remixed_clips_collection.find_one({'remixed_clip_id': request.id})
        if not remixed_clip_info:
            raise HTTPException(status_code=500, detail='Remixed clip not found')
        remixed_clips_collection.update_one(
            {'remixed_clip_id': request.id},
            {'$set':{'remixed_clip_name': request.name}}
        )
    return {'message': 'Rename successful'}
    
@router.post('/move/', tags=['Move'])
async def move(request: Move):  # Space id required from FEnd
    if request.category not in ['folder', 'broll', 'music']:
        raise HTTPException(status_code=422, detail='Invalid Category')
    if request.category=='folder':
        folder_info = folders_collection.find_one({'folder_id': request.sour_id})
        if not folder_info:
            raise HTTPException(status_code=404, detail='Folder not found')
        # if request.dest_id=='root' and request.space_id!=folder_info['space_id']:   
        #     raise HTTPException(status_code=400, detail='You are not authorized to move this folder.')
        folders_collection.update_one(
            {'folder_id': request.sour_id},
            {'$set':{'parent_id': request.dest_id}}
        )
    elif request.category=='broll':
        broll_info = brolls_collection.find_one({'file_id': request.sour_id})
        if not broll_info:
            raise HTTPException(status_code=404, detail='broll not found')
        # if request.dest_id=='root' and request.space_id==broll_info['space_id']: 
        #     raise HTTPException(status_code=400, detail='You are not authorized to move this file.')
        brolls_collection.update_one(
            {'file_id': request.sour_id},
            {'$set':{'parent_id': request.dest_id}}
        )
    elif request.category=='music':
        music_info = music_collection.find_one({'file_id': request.sour_id})
        if not music_info:
            raise HTTPException(status_code=404, detail='music not found')
        # if request.dest_id=='root' and request.space_id==music_info['space_id']:
        #     raise HTTPException(status_code=400, detail='You are not authorized to move this file.')
        music_collection.update_one(
            {'file_id': request.sour_id},
            {'$set':{'parent_id': request.dest_id}}
        )
    return {'message': 'Successfully Moved'}

@router.post('/edit_tags/', tags=['Tags'])
async def edit_tags(request: EditTags):
    if request.category == 'broll':
        file_info = brolls_collection.find_one({'file_id': request.file_id})
        if not file_info:
            raise HTTPException(status_code=500, detail='File not found.')
        brolls_collection.update_one(
            {'file_id': request.file_id},
            {'$set': {'tags': request.tags}}
        )
        existing_tags = set(tag_['tag_name'] for tag_ in tags_collection.find({'file_id': request.file_id, 'space_id': file_info['space_id'], 'category': 'broll'}))
        new_tags = set(tag.lower() for tag in request.tags)
        
        tags_to_add = new_tags - existing_tags
        for tag in tags_to_add:
            tag_info = {
                'tag_name': tag,
                'file_id': request.file_id,
                'space_id': file_info['space_id'],
                'category': 'broll'
            }
            tags_collection.insert_one(tag_info)

        tags_to_remove = existing_tags - new_tags
        tags_collection.delete_many({
            'file_id': request.file_id,
            'space_id': file_info['space_id'],
            'category': 'broll',
            'tag_name': {'$in': list(tags_to_remove)}
        })
        return {'message': 'Tags updated successfully.'}

    elif request.category == 'music':
        file_info = music_collection.find_one({'file_id': request.file_id})
        if not file_info:
            raise HTTPException(status_code=500, detail='File not found.')
        music_collection.update_one(
            {'file_id': request.file_id},
            {'$set': {'tags': request.tags}}
        )
        existing_tags = set(tag_['tag_name'] for tag_ in tags_collection.find(
            {'file_id': request.file_id, 'space_id': file_info['space_id'], 'category': 'music'}
        ))

        new_tags = set(tag.lower() for tag in request.tags)
        tags_to_add = new_tags - existing_tags
        for tag in tags_to_add:
            tag_info = {
                'tag_name': tag,
                'file_id': request.file_id,
                'space_id': file_info['space_id'],
                'category': 'music'
            }
            tags_collection.insert_one(tag_info)

        tags_to_remove = existing_tags - new_tags
        tags_collection.delete_many({
            'file_id': request.file_id,
            'space_id': file_info['space_id'],
            'category': 'music',
            'tag_name': {'$in': list(tags_to_remove)}
        })
        return {'message': 'Tags updated successfully.'}