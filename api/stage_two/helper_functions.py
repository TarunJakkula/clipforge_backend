from moviepy.editor import VideoFileClip, concatenate_videoclips
from fastapi import HTTPException
import json
import re

def parse_unstructured_json_respose(json_structure_1):
    json_pattern = r'```json\n(.*?)\n```'
    match = re.search(json_pattern, json_structure_1, re.DOTALL)
    if match:
        json_data = match.group(1)
        try:
            parsed_data = json.loads(json_data)
            return parsed_data
        except json.JSONDecodeError as e:
            raise ValueError(f'Error decoding JSON :{e}')
    else:
        raise ValueError('No JSON data found in the response.')

def get_text_for_timestamp(transcript, start_time, end_time):
    extracted_text = []
    for segment in transcript:
        if isinstance(segment['timestamp'], (list, tuple)):
          segment_start, segment_end = map(float, segment['timestamp'])
        # Check if segment overlaps with the desired time range
        if (start_time <= segment_start < end_time) or (start_time < segment_end <= end_time):
            if start_time==segment_start :
                list(segment['timestamp'])[0] = start_time
            if end_time==segment_end :
                list(segment['timestamp'])[1] = end_time
            json_segment = {'timestamp': segment['timestamp'], 'text': segment['text']}
            extracted_text.append(json_segment)
    return extracted_text

def get_remixed_transcript(remix_data, transcript_json):
    remix_text = []
    if isinstance(remix_data['timestamps'], list):
        for timestamp in remix_data['timestamps']:
            if isinstance(timestamp, str):
                start_time, end_time = map(float, timestamp.split('-'))
            elif isinstance(timestamp, (list, tuple)):
                start_time, end_time = map(float, timestamp)
            remix_text.extend(get_text_for_timestamp(transcript_json, start_time, end_time))

    elif isinstance(remix_data['timestamps'], str):
        start_time, end_time = map(float, remix_data['timestamps'].split('-'))
        remix_text.extend(get_text_for_timestamp(transcript_json, start_time, end_time))
    return remix_text

def trim_remix_grouped(video_path, output_path, timestamps):
    with VideoFileClip(video_path) as video:
        video_duration = video.duration
        clips = []
        if isinstance(timestamps, str):
            try:
                timestamps = [tuple(map(float, timestamps.split('-')))]
            except ValueError:
                raise ValueError(f'Invalid timestamp string format: {timestamps}')
        elif isinstance(timestamps, list):
            processed_timestamps = []
            for timestamp in timestamps:
                if isinstance(timestamp, str):
                    try:
                        processed_timestamps.append(tuple(map(float, timestamp.split('-'))))
                    except ValueError:
                        raise ValueError(f'Invalid timestamp string format in list: {timestamp}')
                elif isinstance(timestamp, (list, tuple)):
                    try:
                        processed_timestamps.append(tuple(map(float, timestamp)))
                    except ValueError:
                        raise ValueError(f'Invalid timestamp format in list: {timestamp}')
            timestamps = processed_timestamps

        for start_time, end_time in timestamps:
            if start_time < 0 or end_time > video_duration:
                raise ValueError(f'Timestamps out of bounds: {start_time} - {end_time}')
            subclip = video.subclip(start_time, min(end_time + 0.100, video_duration))
            clips.append(subclip)

        if not clips:
            raise HTTPException(status_code=404, detail='No valid clips found. Aborting.')
        if len(clips) == 1:
            remixed_video = clips[0]
        else:
            remixed_video = concatenate_videoclips(clips, method='compose')
        remixed_video.write_videofile(output_path, codec='libx264', audio_codec='aac')