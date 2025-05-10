from moviepy.editor import VideoFileClip, CompositeVideoClip
from api.stage_one.helper_functions import extract_json
from utils.s3_session import download_from_s3
from utils.mongodb_schemas import *
from utils.log_errors import logger
from fastapi import HTTPException
from utils.openai_init import llm
import json, re, uuid, openai, math
from utils.log_errors import logger

OUTPUT_DIR_3 = 'project_clips'
    
def normalize_timestamps(timestamps):
    for index, stamp in enumerate(timestamps):
        start, end = stamp['timestamp']
        start = float(start)
        end = float(end)
        if index == 0:
            new_start = 0.0
            new_end = round(end - start, 2)
        else:
            prev_end = timestamps[index - 1]['timestamp'][1]
            new_start = round(prev_end, 2)
            new_end = round(new_start + (end - start), 2)
        timestamps[index]['timestamp'] = [new_start, new_end]
    return timestamps

def get_relevant_broll(broll_dict, keyword, batch_size=50):
    if keyword not in broll_dict or not broll_dict[keyword]:
        return None 
    available_brolls = [entry for entry in broll_dict[keyword] if not entry[1]]
    if not available_brolls:
        return None 

    total_batches = math.ceil(len(available_brolls) / batch_size)
    relevant_brolls = []

    for batch_num in range(total_batches):
        batch = available_brolls[batch_num * batch_size : (batch_num + 1) * batch_size]
        batch_links = {entry[0]: entry[2] for entry in batch}

        prompt = f"Get the most relevant B-roll from the following list: \n{batch_links}\n for the keyword: {keyword}\n**JUST THE LINK**"
        response = llm.predict(prompt)
        match = re.search(r'https?://[^\s]+\.mp4', response)
        if match:
            relevant_broll = match.group(0)
            if relevant_broll in batch_links:
                relevant_brolls.append(relevant_broll)
                logger.info(f'Selected B-roll: {relevant_broll}')
                break

    if not relevant_brolls:
        relevant_brolls.append(available_brolls[0][0])
        logger.warning(f'LLM failed after all retries! Using fallback B-roll: {relevant_brolls[0]}')

    for keyword in broll_dict:
        for entry in broll_dict[keyword]:
            if entry[0] in relevant_brolls:
                entry[1] = True

    return relevant_brolls[0]

def add_brolls(clip_info, space_id, broll_dict, video_path, toggle):
    def mark_broll_as_used(keyword, broll_path):
        if keyword in broll_dict:
            for broll_entry in broll_dict[keyword]:
                if broll_entry[0] == broll_path:
                    broll_entry[1] = True
                    break
    try :
        tags = set()
        video = VideoFileClip(video_path)
        normalized_timestamps = normalize_timestamps(clip_info['remixed_clip_transcript'])
        for broll in brolls_collection.find({'spaces': {'$in': [space_id]}}) :
            tags.update(broll['tags'])
        broll_prompt = prompts_collection.find_one({'space_id': space_id})['broll_prompt']
        json_structure = '''
            % START OF EXAMPLES
            EXAMPLE :
            {
                "broll": [
                    {
                        "timestamp": [start, end],
                        "keyword": "running"
                    },
                    {
                        "timestamp": [start, end],
                        "keyword": "exercise"
                    }
                ]
            }
            % END OF EXAMPLES
        '''
        try :
            response = llm.predict(str(normalized_timestamps) + broll_prompt + json_structure + f'Select the keywords from the AVAILABLE TAGS ONLY : {tags}, IT SHOULDNT BE EMPTY')
            json_response = extract_json(response)
        except openai.RateLimitError as e:
            return HTTPException(status_code=429, detail='Rate limit exceeded.')
        except Exception as e :
            return HTTPException(status_code=404, detail=f'Error getting the response from llm :{e}')
        
        broll_clips, broll_used_list = [], []
        for entry in json_response['broll']:
            keyword = entry['keyword']
            brolls_info = list(brolls_collection.find({'spaces': {'$in': [space_id]}, 'tags': keyword}))
            for broll_info in brolls_info:
                if keyword in broll_info['tags']:
                    if broll_info['file_storage_link'] not in [entry[0] for entries in broll_dict.values() for entry in entries]:
                        if keyword not in broll_dict:
                            broll_dict[keyword] = []
                        broll_dict[keyword].append([broll_info['file_storage_link'], False, broll_info['tags']])
            broll_video_path = get_relevant_broll(broll_dict, keyword)
            if broll_video_path is None:
                continue
            local_broll_path = f'{OUTPUT_DIR_3}/{str(uuid.uuid4())}.mp4'
            download_from_s3(broll_video_path, local_broll_path)
            
            try:
                broll_used_list.append(local_broll_path)
                with VideoFileClip(local_broll_path).without_audio() as broll_video:
                    if video.aspect_ratio < broll_video.aspect_ratio:
                        broll_video = broll_video.resize(height=video.h)
                    elif video.aspect_ratio > broll_video.aspect_ratio:
                        broll_video = broll_video.resize(width=video.w)
                    else:
                        broll_video = broll_video.resize(newsize=video.size)

                    start_time = float(entry['timestamp'][0])
                    safe_margin_broll_time = 0.05
                    max_broll_duration = broll_video.duration
                    subclip_duration = min(2, max_broll_duration - safe_margin_broll_time)
                    broll_clip = broll_video.subclip(0, subclip_duration).set_start(start_time)
                    if toggle: broll_clip = broll_clip.fadein(0.2).fadeout(0.2)

                    broll_clips.append(broll_clip)
                    broll_clip.close()
                    mark_broll_as_used(keyword, broll_video_path)
                    broll_video.close() 
            except Exception as e:
                logger.error(f'Error processing B-roll for keyword {keyword}: {e}')
                continue

        try:
            if not broll_clips:
                logger.info('No brolls available...')
                return video_path, broll_dict, broll_used_list
            final_video = CompositeVideoClip([video] + broll_clips).set_fps(video.fps)
            safe_duration = round(min(final_video.duration, getattr(final_video, 'end', final_video.duration)) - 0.05, 3)
            final_video = final_video.set_duration(safe_duration)
            
            final_video_path = f'{OUTPUT_DIR_3}/{str(uuid.uuid4())}.mp4'
            final_video.write_videofile(final_video_path, fps=video.fps)
            final_video.close()
            logger.info('Brolls applied')
            return final_video_path, broll_dict, broll_used_list
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Error creating final video: {e}')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error in add_brolls: {e}')