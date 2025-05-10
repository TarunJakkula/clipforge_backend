from utils.mongodb_schemas import clips_collection, prompts_collection, subclips_collection
from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.pydantic_models import GenerateClipsRequest
from utils.s3_session import download_from_s3
from api.stage_one.helper_functions import *
from utils.s3_session import upload_to_s3
from utils.log_errors import logger
from utils.openai_init import llm
import json
import uuid
import os

router = APIRouter()
OUTPUT_DIR_1 = 'output_clips'
os.makedirs(OUTPUT_DIR_1, exist_ok=True)

def process_clips(space_id, clip_info):
    try:
        local_video_path = f"{OUTPUT_DIR_1}/{uuid.uuid4()}.mp4"
        download_from_s3(clip_info['clip_storage_link'], local_video_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error downloading video from S3 :{e}')
    
    transcript_json = clip_info['clip_transcript']['transcript_json']
    text_with_timestamps = ''.join(
        f"Start time: {segment['timestamp'][0]} - {segment['text']} End time: {segment['timestamp'][1]}, "
        for segment in transcript_json
    )
    text_splitter = RecursiveCharacterTextSplitter(separators=['\n\n', '\n', ' '], chunk_size=10000, chunk_overlap=2200)
    docs = text_splitter.create_documents([text_with_timestamps])
    
    try:
        prompt_data = prompts_collection.find_one({'space_id': space_id})
        if not prompt_data:
            raise HTTPException(status_code=404, detail='Stage 1 prompt not found')
        latest_prompt = prompt_data.get('stage_1_prompt', '').strip()
    except Exception as e:
        raise HTTPException(status_code=404, detail='Stage 1 prompt does not exist')
    stage_1_prompt = f'''
        Prompt for GPT-4:
        Analyze the following podcast transcript and extract key topics along with their timestamps.
        
        {latest_prompt}
        
        Output Format:
        Provide the results in structured JSON format. Each topic should include:
        - 'title': A short, descriptive title summarizing the topic.
        - 'timestamp': The start and end times of the segment in seconds with millisecond precision.
    '''
    json_structure = '''
        % START OF EXAMPLES
        EXAMPLE STRUCTURE:
        {
            "clips": [
            {
                "title": "The Duality of Divine Knowledge",
                "timestamp": '235.32-390.08'
            },
            {
                "title": "Shaan's Interesting Projects",
                "timestamp": "413.45-570.10"
            }
            ]
        }
        % END OF EXAMPLES
        '''
    try:
        responses = [llm.predict(doc.page_content + stage_1_prompt + json_structure) for doc in docs]
        num_of_clips = 0
        for response in responses:
            try:
                clips = extract_json(response).get('clips', [])
                if isinstance(clips, list):
                    num_of_clips += len(clips)
                else:
                    raise ValueError('Invalid format for clips: Expected a list.')
            except json.JSONDecodeError:
                raise ValueError(f'Failed to decode JSON response: {response}')

        clips_collection.update_one(
            {'clip_id': clip_info['clip_id']},
            {'$set': {'total_possible_clips': num_of_clips}}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail='Failed to generate clips')
    
    for response in responses:
        time_stamps, topics_with_transcripts = return_timestamps_with_transcripts(response, transcript_json)
        for stamp, script in zip(time_stamps, topics_with_transcripts):
            start_time, end_time = stamp
            title = script['title']
            transcript = script['transcript']
            output_file = f'{OUTPUT_DIR_1}/{str(uuid.uuid4())}.mp4'
            trim_video(local_video_path, output_file, start_time, end_time)
            subclip_id = str(uuid.uuid4())
            s3_key = f'subclips/{subclip_id}.mp4'
            try:
                clip_storage_link = upload_to_s3(output_file, s3_key)
            except Exception as e:
                continue

            subclip_data = {
                'subclip_id': subclip_id,
                'subclip_name': sanitize_filename(title),
                'subclip_storage_link': clip_storage_link,
                'subclip_transcript': transcript,
                'parent_name': clip_info.get('clip_name'),
                'aspect_ratio': clip_info.get('aspect_ratio'),
                'clip_id': clip_info['clip_id'],
                'remixes': False
            }
            subclips_collection.insert_one(subclip_data)
            if os.path.exists(output_file):
                os.remove(output_file)
    
    # Remove the downloaded video file
    if os.path.exists(local_video_path):
        os.remove(local_video_path)

@router.post('/generate_clips/', tags=['Stage-1'])
async def generate_clips(request: GenerateClipsRequest, background_tasks: BackgroundTasks):
    logger.info('Stage 1 started...')
    clip = clips_collection.find_one({'clip_id': request.clip_id})
    if not clip:
        raise HTTPException(status_code=404, detail='Clip not found')

    updated_count = clips_collection.update_one(
        {'clip_id': request.clip_id},
        {'$set': {'subclips': True}}
    )
    background_tasks.add_task(process_clips, request.space_id, clip)
    return {'message': 'Clip generation and Remixing started in the background'}