from fastapi import APIRouter, BackgroundTasks, HTTPException
from utils.s3_session import download_from_s3, upload_to_s3
from models.pydantic_models import GenerateRemixedClips
from api.stage_two.helper_functions import *
from utils.log_errors import logger
from utils.mongodb_schemas import *
from utils.openai_init import llm
import uuid, os

router = APIRouter()
OUTPUT_DIR_2 = 'remixed_clips'
os.makedirs(OUTPUT_DIR_2, exist_ok=True)

def remix_transcripts(space_id, clip_data):
    try:
        try:
            video_path = f"{OUTPUT_DIR_2}/{str(uuid.uuid4())}.mp4"
            download_from_s3(clip_data['clip_storage_link'], video_path)
        except Exception as e:
            logger.error(f'Failed to download the viral section : {e}')
        for subclip_info in list(subclips_collection.find({'clip_id': clip_data['clip_id']})):
            if not subclip_info:
                raise HTTPException(status_code=500, detail='Subclip not found')
            if subclip_info['remixes']: 
                continue
            subclips_collection.update_one(
                {'subclip_id': subclip_info.get('subclip_id')},
                {'$set': {'remixes': True}}
            )
            transcript_json = clip_data['clip_transcript']['transcript_json']
            
            try:
                prompt_data = prompts_collection.find_one({'space_id': space_id})
                if not prompt_data:
                    raise HTTPException(status_code=404, detail='Stage 2 prompt not found')
                latest_prompt = prompt_data.get('stage_2_prompt', '').strip()
            except Exception as e:
                raise HTTPException(status_code=500, detail='Stage 2 prompt does not exist')
            stage_2_prompt = f'''{latest_prompt}'''
            json_structure = '''
                % START OF EXAMPLES
                {
                'remixed': [
                    {
                        'title': 'The Secret to Finding Business Opportunities',
                        'timestamps': [[start-end], [start-end], [start-end]]
                    },
                    {
                        'title': 'Why Passion is Overrated in Business',
                        'timestamp': [[start-end], [start-end], [start-end]]
                    }
                ]
                }
                % END OF EXAMPLES
            '''
            response = llm.predict('Heres the mother video transcript: ' + str(transcript_json) + '\n Heres the viral section' + str(subclip_info['subclip_transcript']) + stage_2_prompt)
            json_structure_1 = llm.predict(response + f'''\n\nStructure this response into formatted JSON structure \n{json_structure}''')
            try:
                json_data = parse_unstructured_json_respose(json_structure_1)
            except Exception as e:
                raise HTTPException(status_code=500, detail='Failed to load JSON Response')
            
            for remix in json_data['remixed']:
                output_path = f"{OUTPUT_DIR_2}/{str(uuid.uuid4())}.mp4"
                try:
                    trim_remix_grouped(video_path, output_path, remix['timestamps'])
                except Exception as e:
                    logger.error(f"Error making remixes for this clip: {output_path}: {e}")
                    continue
                remixed_clip_id = str(uuid.uuid4())
                s3_key = f'remixed_clips/{remixed_clip_id}.mp4'
                try:
                    remix_clip_storage_link = upload_to_s3(output_path, s3_key)
                except Exception as e:
                    continue
                transcript_remix = get_remixed_transcript(remix, transcript_json)
                remixed_clips_collection.insert_one({
                    'remixed_clip_id': remixed_clip_id,
                    'remixed_clip_name': remix['title'],
                    'remixed_clip_link': remix_clip_storage_link,
                    'remixed_clip_transcript': transcript_remix,
                    'aspect_ratio': subclip_info.get('aspect_ratio'),
                    'subclip_id': subclip_info['subclip_id'],
                    'preset': False
                })
                if os.path.exists(output_path):
                    os.remove(output_path)
        if os.path.exists(video_path):
            os.remove(video_path)
        for temp_file in os.listdir(OUTPUT_DIR_2):
            os.remove(f'{OUTPUT_DIR_2}/{temp_file}')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error in remixing clips: {e}')

@router.post('/generate_remixed_clips/', tags=['Stage-2'])
async def generate_remixed_clips(request: GenerateRemixedClips, background_tasks: BackgroundTasks):
    logger.info('Stage 2 started...')
    clip_info = clips_collection.find_one({'clip_id': request.clip_id})
    if not clip_info:
        raise HTTPException(status_code=404, detail='Clip not found')

    background_tasks.add_task(remix_transcripts, request.space_id, clip_info)
    return {'message': 'Clip generation and Remixing started in the background'}