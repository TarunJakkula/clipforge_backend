from api.stage_three import add_brolls, add_music, add_presets
from utils.s3_session import download_from_s3, upload_to_s3
from models.pydantic_models import AddBrollMusicPresets
from fastapi import HTTPException, BackgroundTasks
from utils.log_errors import logger
from utils.mongodb_schemas import *
from fastapi import APIRouter
from itertools import cycle
import uuid, os, copy

router = APIRouter()
OUTPUT_DIR_3 = 'project_clips'
os.makedirs(OUTPUT_DIR_3, exist_ok=True)

def add_broll_music_presets(space_id, subclip_id):
    logger.info('Stage 3 started...')
    subclip_info = subclips_collection.find_one({'subclip_id': subclip_id})
    if not subclip_info:
        raise HTTPException(status_code=500, detail='subclip not found, skipping...')
    
    output_path = ''
    used_files = []
    broll_dict_info = {}
    music_dict_info = {}
    preset_data_info = list(presets_collection.find({'spaces': {'$in': [space_id]}}))
    if not preset_data_info: 
        raise HTTPException(status_code=404, detail='No presets found')
    preset_cycle = cycle(preset_data_info)

    for remixed_clip_info in remixed_clips_collection.find({'subclip_id': subclip_id}):
        if remixed_clip_info['preset']:
            continue
        preset_toggle = next(preset_cycle)
        local_video_path = f"{OUTPUT_DIR_3}/{uuid.uuid4()}.mp4"
        download_from_s3(remixed_clip_info['remixed_clip_link'], local_video_path)
        final_input_path = ''
        
        try:
            # Apply B-roll
            logger.info('Applying broll...')
            remixed_transcript_broll = copy.deepcopy(remixed_clip_info)
            broll_added_clip_path, broll_dict_info, used_brolls = add_brolls.add_brolls(remixed_transcript_broll, space_id, broll_dict_info, local_video_path, preset_toggle['options']['brollToggle'])
            used_files.extend(used_brolls)

            # Apply Music
            logger.info('Applying music...')
            remixed_transcript_music = copy.deepcopy(remixed_clip_info)
            music_added_clip_path, music_dict_info, used_music = add_music.add_music(broll_added_clip_path, remixed_transcript_music['remixed_clip_transcript'], space_id, music_dict_info)
            if used_music is not None : 
                logger.info(f'{music_added_clip_path}, {used_music}')
                used_files.extend(used_music)
            
            # Apply Presets
            logger.info('Applying presets...')
            remixed_transcript_presets = copy.deepcopy(remixed_clip_info)
            final_input_path = music_added_clip_path if music_added_clip_path and os.path.exists(music_added_clip_path) else (
                broll_added_clip_path if broll_added_clip_path and os.path.exists(broll_added_clip_path) else None)
            if not final_input_path:
                logger.error("No valid input path available for applying presets.")
                continue
            output_path, transcript, video_path = add_presets.add_presets(final_input_path, remixed_transcript_presets['remixed_clip_transcript'], preset_toggle['options'], subclip_info['clip_id'])
            used_files.extend([video_path])
        except HTTPException as e:
            if 'video_fps' in str(e):
                logger.warning("Skipping video due to FPS error")
                continue
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Exception : {e}')

        if not output_path or not os.path.exists(output_path):
            logger.error(f"Final input path exists: {os.path.exists(final_input_path)}")
            continue
        
        # for file in used_files:
        #     if file and os.path.exists(file):
        #         try:
        #             os.remove(file)
        #         except Exception as e:
        #             logger.info(f'Error while deleting file : {e}')
        #             continue

        preset_clip_id = str(uuid.uuid4())
        s3_key = f'project_clips/{preset_clip_id}.mp4'

        try:
            preset_clip_link = upload_to_s3(output_path, s3_key)
        except Exception as e:
            logger.error(f"Error uploading file to S3: {e}")
            continue

        preset_added_clip_info = {
            'preset_clip_id': preset_clip_id,
            'preset_clip_name': remixed_clip_info['remixed_clip_name'],
            'preset_clip_link': preset_clip_link,
            'preset_clip_transcript': transcript,
            'preset_id': preset_toggle['preset_id'],
            'aspect_ratio': remixed_clip_info['aspect_ratio'],
            'space_id': space_id
        }
        projects_collection.insert_one(preset_added_clip_info)
        remixed_clips_collection.update_one(
            {'remixed_clip_id': remixed_clip_info['remixed_clip_id']},
            {'$set': {'preset': True}}
        )

        if os.path.exists(output_path):
            os.remove(output_path)
        if os.path.exists(local_video_path):
            os.remove(local_video_path)

@router.post('/stage_three/', tags=['Stage-3'])
async def stage_three(request: AddBrollMusicPresets, backgroundtasks: BackgroundTasks):
    try:
        backgroundtasks.add_task(add_broll_music_presets, request.space_id, request.subclip_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {e}')
    return {'message': 'Process started.'}