from utils.env_variables import S3_BUCKET_NAME
from moviepy.editor import VideoFileClip
from utils.log_errors import logger
from fastapi import HTTPException
import re, json

def extract_json(response):
    try:
        start = response.find('{')
        end = response.rfind('}')
        if start>=0 and end>start:
            json_part = response[start:end+1]
            logger.info('Json extraction :: %s', json_part)
            data = json.loads(json_part)
            return data
        else:
            raise ValueError('No valid JSON found in the response.')
    except json.JSONDecodeError as e:
        raise ValueError(f'JSON decoding error: {e}')
    
def get_text_for_timestamp(transcript, start_time, end_time):
    extracted_text = []
    if isinstance(start_time, str) and isinstance(end_time, str):
        try:
            start_time = float(start_time)
            end_time = float(end_time)
        except ValueError:
            raise HTTPException(status_code=500, detail=f'Invalid start_time or end_time format.')
    elif isinstance(start_time, (list, tuple)) and isinstance(end_time, (list, tuple)):
        try:
            start_time = float(start_time[0])
            end_time = float(end_time[0])
        except (ValueError, IndexError):
            raise HTTPException(status_code=500, detail=f'Invalid list/tuple format for start_time or end_time')

    for segment in transcript:
        try:
            segment_start = float(segment['timestamp'][0])
            segment_end = float(segment['timestamp'][1])
            if(
                float(start_time) <= float(segment_start) <= float(end_time)
                or float(start_time) <= float(segment_end) <= float(end_time)
            ):
                json_segment = {'timestamp': segment['timestamp'], 'text': segment['text']}
                extracted_text.append(json_segment)
        except (KeyError, ValueError, IndexError) as e:
            raise HTTPException(status_code=500, detail=f'Skipping invalid segment due to error: {e}')

    return extracted_text

def return_timestamps_with_transcripts(response, original_transcript):
    data = extract_json(response)
    topics_with_transcripts = []
    time_stamps = []
    for topic in data['clips']:
        title = topic['title']
        timestamp = topic['timestamp']
        if isinstance(timestamp, str):
            try:
                start_time, end_time = map(float, timestamp.split('-'))
            except ValueError:
                raise HTTPException(status_code=500, detail='Invalid timestamp format')
        elif isinstance(timestamp, (list, tuple)) and len(timestamp) >= 2:
            try:
                start_time, end_time = map(float, timestamp[:2])
            except ValueError:
                raise HTTPException(status_code=500, detail=f'Invalid list/tuple format for timestamp')
        else:
            raise HTTPException(status_code=500, detail=f'Unsupported timestamp format: {timestamp}. Skipping this clip.')
        transcript_text = get_text_for_timestamp(original_transcript, start_time, end_time)
        time_stamps.append((start_time, end_time))
        topics_with_transcripts.append({
            'title': title,
            'timestamp': (start_time, end_time),
            'transcript': transcript_text
        })
    return time_stamps, topics_with_transcripts

def sanitize_filename(filename):
    filename = re.sub(r'\s+', ' ', filename.strip())
    return re.sub(r'[^\w\s]', '', filename)

def trim_video(input_path, output_path, start_time, end_time):
    try:
        video = VideoFileClip(input_path)
        start_time = float(start_time)
        end_time = float(end_time)
        if start_time >= end_time or start_time < 0 or end_time > video.duration:
            raise ValueError('Invalid start or end time for trimming')
        # if end_time - start_time >= 45.00 : 
        trimmed_video = video.subclip(start_time, end_time)
        trimmed_video.write_videofile(output_path, codec='libx264', audio_codec='aac', preset='fast')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred during video trimming: {str(e)}')