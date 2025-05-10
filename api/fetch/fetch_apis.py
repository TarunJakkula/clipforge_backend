from fastapi import APIRouter, HTTPException, Query
from utils.mongodb_schemas import *

router = APIRouter()

@router.get('/get_clip_info/', tags=['Clips'])
async def get_clip_info(clip_id: str = Query(...)) :
    clip = clips_collection.find_one({'clip_id': clip_id})
    if not clip :
        raise HTTPException(status_code=404, detail='Clip not found')
    return {'clip_name': clip['clip_name'], 'video_link': clip['clip_storage_link'], 'aspect_ratio': clip['aspect_ratio']}

@router.get('/get_clip_transcript/', tags=['Transcript'])
async def get_clip_transcript(clip_id: str = Query(...)) :
    clip = clips_collection.find_one({'clip_id': clip_id})
    if not clip :
        raise HTTPException(status_code=404, detail='Clip not found')
    return {'transcript': clip['clip_transcript']['transcript_text']}

@router.get('/get_clips_without_transcript/', tags=['Clips'])
async def get_clips_without_transcript(space_id: str = Query(...)) :
    space = spaces_collection.find_one({'space_id': space_id})
    if not space:
        raise HTTPException(status_code=404, detail='Space not found')

    clips_info = []
    for clip_info in list(clips_collection.find({'space_id': space_id})):
        if not clip_info:
          raise HTTPException(status_code=404, detail='Clip not found')
        clip_transcript = clip_info.get('clip_transcript', None)
        if not clip_transcript:
          clips_info.append({
              'clip_id': clip_info.get('clip_id'),
              'clip_name': clip_info.get('clip_name'),
              'clip_storage_link': clip_info.get('clip_storage_link'),
              'aspect_ratio': clip_info.get('aspect_ratio')
          })
        elif not clip_transcript.get('transcript_text'):
          clips_info.append({
              'clip_id': clip_info.get('clip_id'),
              'clip_name': clip_info.get('clip_name'),
              'clip_storage_link': clip_info.get('clip_storage_link'),
              'aspect_ratio': clip_info.get('aspect_ratio')
          })
    return {'data': clips_info[::-1]}

@router.get('/get_clips_with_transcript_without_subclips/', tags=['Clips'])
async def get_clips_with_transcript_without_subclips(space_id: str = Query(...)) :
    space = spaces_collection.find_one({'space_id': space_id})
    if not space:
        raise HTTPException(status_code=404, detail='Space not found')

    clips_info = []
    for clip_info in list(clips_collection.find({'space_id': space_id})) :
        if clip_info and clip_info.get('clip_transcript') and clip_info['clip_transcript']['transcript_text'] and not clip_info['subclips']:
            clips_info.append({
                'clip_id': clip_info.get('clip_id'),
                'clip_name': clip_info.get('clip_name'),
                'clip_storage_link': clip_info.get('clip_storage_link'),
                'clip_transcript': clip_info.get('clip_transcript'),
                'aspect_ratio': clip_info.get('aspect_ratio')
            })
    return {'data': clips_info[::-1]}

@router.get('/get_transcript_status/', tags=['Transcript'])
async def get_transcript_status(clip_id: str = Query(...)) :
    clip = clips_collection.find_one({'clip_id': clip_id})
    if not clip:
        raise HTTPException(status_code=404, detail='Clip not found')
    return {'transcript_status': clip['clip_transcript'] is not None and clip['clip_transcript']['transcript_text'] is not None}

@router.get('/fetch_possible_clips/', tags=['Clips'])
async def fetch_possible_clips(clip_id: str = Query(...)) :
    clip = clips_collection.find_one({'clip_id': clip_id})
    if not clip:
        raise HTTPException(status_code=404, detail='Clip not found')
    return {'total_possible_clips': clip.get('total_possible_clips')}
    
@router.get('/get_breadcrumbs/', tags=['Breadcrumbs'])
async def get_breadcrumbs(id: str = Query(...)):
    folder_info = folders_collection.find_one({'folder_id': id})
    if not folder_info:
        return {'breadcrumbs': []} 

    breadcrumbs = []
    current_id = id
    while current_id != 'root':
        folder_info = folders_collection.find_one({'folder_id': current_id})
        if folder_info:
            breadcrumbs.append({'name': folder_info['folder_name'], 'id': folder_info['folder_id']})
            current_id = folder_info.get('parent_id', 'root') 
        else:
            break
    return {'breadcrumbs': list(reversed(breadcrumbs))}

@router.get('/fetch_broll/', tags=['Broll'])
async def fetch_folders(space_id: str = Query(...), parent_id: str = Query(...)):
    if parent_id!='root' :
        parent_info = folders_collection.find_one({'folder_id': parent_id, 'spaces': {'$in' :[space_id]}})
        if not parent_info :
            raise HTTPException(status_code=404, detail='File not found')
    try:
        broll_files = brolls_collection.find({'parent_id': parent_id, 'spaces': {'$in': [space_id]}})
        data = [{'id': broll_file['file_id'], 'name': broll_file['file_name'], 'link': broll_file['file_storage_link'], 'tags': broll_file['tags'], 
                'parent': broll_file['parent_id'], 'aspect_ratio': broll_file['aspect_ratio'], 'owner_id': broll_file['space_id']} for broll_file in broll_files]
        return {'brolls': data[::-1], 'parent_id': parent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Files fetching failed: {str(e)}')
    
@router.get('/fetch_music/', tags=['Music'])
async def fetch_folders(space_id: str = Query(...), parent_id: str = Query(...)):
    if parent_id!='root' :
        parent_info = folders_collection.find_one({'folder_id': parent_id, 'spaces': {'$in': [space_id]}})
        if not parent_info :
            raise HTTPException(status_code=404, detail='File not found')
    try:
        music_files = music_collection.find({'parent_id': parent_id, 'spaces': {'$in': [space_id]}})
        data = [{'id': music_file['file_id'], 'name': music_file['file_name'], 'link': music_file['file_storage_link'], 'tags': music_file['tags'], 
                 'parent': music_file['parent_id'], 'owner_id': music_file['space_id']} for music_file in music_files]
        return {'music': data[::-1],'parent_id':parent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Files fetching failed: {str(e)}')
    
@router.get('/fetch_all_tags/', tags=['Tags'])
async def get_all_broll_music_tags(space_id: str = Query(...), category: str = Query(...)):
    all_tags = [{'value': tag['tag_name'], 'label': tag['tag_name']} for tag in list(tags_collection.find({'space_id': space_id, 'category': category}))]  
    return {'tags': all_tags}