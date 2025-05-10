from utils.mongodb_schemas import spaces_collection, clips_collection, subclips_collection, remixed_clips_collection, projects_collection
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

@router.get('/get_all_clips/', tags=['Clips'])
async def get_all_clips(space_id: str = Query(...)) :
    space_info = spaces_collection.find_one({'space_id': space_id})
    if not space_info:
      raise HTTPException(status_code=500, detail='Space not found')

    clips_info = []
    for clip_info in list(clips_collection.find({'space_id': space_id, 'subclips': True})):
        clips_info.append({
            'clip_id': clip_info.get('clip_id'),
            'clip_name': clip_info.get('clip_name').split('.')[0],
            'aspect_ratio': clip_info.get('aspect_ratio')
        })
    return {'clips_info': clips_info[::-1]}

@router.get('/get_stage1_clips/', tags=['Stage-1'])
async def get_stage1_clips(space_id: str = Query(...), clip_id: str = Query(...)) :
    try:
        clip_info = clips_collection.find_one({'clip_id': clip_id, 'space_id': space_id})
        if not clip_info:
            raise HTTPException(status_code=500, detail='Clip not found')
        clips_data = list(subclips_collection.find({'clip_id': clip_id}))
        subclips_info = []
        remix_clips_info = []
        for subclip_info in clips_data:
            if subclip_info.get('remixes') :
                remix_clips_info.append({
                    'clip_id': subclip_info.get('subclip_id'),
                    'clip_name': subclip_info.get('subclip_name').split('.')[0],
                    'clip_link': subclip_info.get('subclip_storage_link'),
                    'aspect_ratio': clip_info.get('aspect_ratio')
                })
            else :
                subclips_info.append({
                    'clip_id': subclip_info.get('subclip_id'),
                    'clip_name': subclip_info.get('subclip_name').split('.')[0],
                    'clip_link': subclip_info.get('subclip_storage_link'),
                    'aspect_ratio': clip_info.get('aspect_ratio')
                })

        return {
                'clip_id': clip_info.get('clip_id'),
                'clip_name': clip_info.get('clip_name'),
                'clip_link': clip_info.get('clip_storage_link'),
                'clips_info': subclips_info[::-1],
                'aspect_ratio': clip_info.get('aspect_ratio'),
                'folder_info': remix_clips_info
                }
    except Exception as e:
        raise HTTPException(status_code=403, detail='Clip not found')

@router.get('/get_stage2_clips/', tags=['Stage-2'])
async def get_stage2_clips(space_id: str = Query(...), clip_id: str = Query(...)) :
    try:
        subclip_info = subclips_collection.find_one({'subclip_id': clip_id})
        if not subclip_info:
            raise HTTPException(status_code=404, detail='Clip not found')
        if not clips_collection.find_one({'clip_id': subclip_info['clip_id'], 'space_id': space_id}):
            raise HTTPException(status_code=403, detail='Clip not found')
        remixed_data = list(remixed_clips_collection.find({'subclip_id': clip_id}))
        remixed_clips_info = []
        for remix_clip_info in remixed_data:
            remixed_clips_info.append({
                'clip_id': remix_clip_info.get('remixed_clip_id'),
                'clip_name': remix_clip_info.get('remixed_clip_name'),
                'clip_link': remix_clip_info.get('remixed_clip_link'),
                'aspect_ratio': remix_clip_info.get('aspect_ratio')
            })
        return {'clip_name': subclip_info.get('subclip_name'), 'clip_link': subclip_info.get('subclip_storage_link'), 'clips_info': remixed_clips_info[::-1], 'aspect_ratio': subclip_info.get('aspect_ratio')}
    except Exception as e:
        raise HTTPException(status_code=403, detail='Clips not found')
    
@router.get('/get_stage3_clips/', tags=['Stage-3'])
async def get_stage3_clips(preset_id: str = Query(...), aspect_ratio: str = Query(...)):
    project_info = list(projects_collection.find({'preset_id': preset_id, 'aspect_ratio': aspect_ratio}))    
    preset_applied_clips = []
    for preset_applied_info in project_info :
        preset_info = {
            'clip_id': preset_applied_info['preset_clip_id'],
            'clip_name': preset_applied_info['preset_clip_name'],
            'clip_link': preset_applied_info['preset_clip_link']
        }
        preset_applied_clips.append(preset_info)
    return {'data': preset_applied_clips[::-1]}