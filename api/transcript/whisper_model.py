from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from models.pydantic_models import TranscriptRequest
from utils.mongodb_schemas import clips_collection
from utils.s3_session import download_from_s3
from moviepy.editor import VideoFileClip
from utils.log_errors import logger
import re, os, uuid
import whisper

OUTPUT_DIR_0 = 'transcript_files'
os.makedirs(OUTPUT_DIR_0, exist_ok=True)

router = APIRouter()
model = whisper.load_model('large-v3-turbo')

def cleanup_files(file_paths: list):
    for file_path in file_paths:
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass
        
def format_word_level(segments: list):
    try:
        formatted_word_level = []
        for segment in segments:
            data = {
                'text': segment['text'].strip(),
                'timestamp': [segment['start'], segment['end']],
                'word_level': [{'word': word['word'].strip(), 'timestamp': [word['start'], word['end']]} for word in segment['words']]
            }
            formatted_word_level.append(data)
        return formatted_word_level
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unable to format word level timestamps :{e}')

def transcribe_with_sentences(audio_path):
    result = model.transcribe(audio_path, task='transcribe', language='en', word_timestamps=True, initial_prompt='Please, do not forget punctuations!')
    sentences = []
    current_sentence = []
    sentence_start_time = None

    for segment in result['segments']:
        for word in segment['words']:
            if sentence_start_time is None:
                sentence_start_time = word['start']

            current_sentence.append(word)
            if re.search(r'[.!?]$', word['word']):
                sentence_text = ' '.join([w['word'] for w in current_sentence]).strip()
                sentence_end_time = word['end']
                sentences.append({
                    'text': sentence_text,
                    'timestamp': [sentence_start_time, sentence_end_time]
                })
                current_sentence = []
                sentence_start_time = None
    return sentences, result

def process_generate_transcript(clip_id: str):
    file_name = str(uuid.uuid4())
    video_filename = f'{OUTPUT_DIR_0}/{file_name}.mp4'
    audio_filename = f'{OUTPUT_DIR_0}/{file_name}.mp3'

    clip_data = clips_collection.find_one({'clip_id': clip_id})
    if not clip_data or 'clip_storage_link' not in clip_data:
        raise HTTPException(status_code=404, detail='Clip not found')

    try:
        clips_collection.update_one(
            {'clip_id': clip_id},
            {'$set': {
                'clip_transcript': {
                    'word_level_timestamps': None,
                    'transcript_text': None,
                    'transcript_json': None
                }
            }}
        )
    except Exception as e:
        cleanup_files([video_filename, audio_filename])
        raise HTTPException(status_code=500, detail=f'Failed to update transcript state: {str(e)}')

    try:
        clip_url = clip_data['clip_storage_link']
        download_from_s3(clip_url, video_filename)
        video = VideoFileClip(video_filename)
        video.audio.write_audiofile(audio_filename)
        video.close()
    except Exception as e:
        cleanup_files([video_filename])
        clips_collection.update_one({'clip_id': clip_id}, {'$set': {'clip_transcript': None}})
        raise HTTPException(status_code=500, detail=f'Failed to process video: {str(e)}')

    clips_collection.update_one(
        {'clip_id': clip_id},
        {'$set': {'clip_duration': video.duration}}
    )

    try:
        transcribed_json, result = transcribe_with_sentences(audio_filename)
        word_level_transcript = format_word_level(result['segments'])
        clips_collection.update_one(
            {'clip_id': clip_id},
            {'$set': {
                'clip_transcript': {
                    'word_level_timestamps': word_level_transcript,
                    'transcript_text': result['text'],
                    'transcript_json': transcribed_json
                }
            }}
        )
    except Exception as e:
        clips_collection.update_one({'clip_id': clip_id}, {'$set': {'clip_transcript': None}})
        raise HTTPException(status_code=500, detail=f'Failed to generate transcript: {str(e)}')
    finally:
        cleanup_files([video_filename, audio_filename])

@router.post('/transcript/', tags=['Transcript'])
async def generate_transcript(requestTranscript: TranscriptRequest, background_tasks: BackgroundTasks):
    clip_info = clips_collection.find_one({'clip_id': requestTranscript.clip_id})
    if clip_info:
        clip_transcript = clip_info.get('clip_transcript')
        if clip_transcript is not None and clip_transcript.get('transcript_text') is None:
            return Response(status_code=202, content='Transcript generation already in progress.')
        else:
            try:
                background_tasks.add_task(process_generate_transcript, requestTranscript.clip_id)
                return {'status': 'Transcript generation process started'}
            except Exception as e:
                clips_collection.update_one({'clip_id': requestTranscript.clip_id}, {'$set': {'clip_transcript': None}})
                logger.error(f'Error starting background task: {str(e)}')
                raise HTTPException(status_code=500, detail='Failed to start transcript generation.')
    else:
        raise HTTPException(status_code=404, detail='Clip not found')