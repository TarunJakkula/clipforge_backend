from moviepy.editor import AudioFileClip, CompositeAudioClip, concatenate_audioclips, VideoFileClip
from api.stage_one.helper_functions import extract_json
from utils.s3_session import download_from_s3
from utils.mongodb_schemas import *
from fastapi import HTTPException
from utils.log_errors import logger
from utils.openai_init import llm
import re, uuid, math, random, os

OUTPUT_DIR_3 = 'project_clips'

def get_relevant_music(music_dict, keyword, batch_size=50):
    def fallback_any_music():
        unused = [
            entry[0]
            for entries in music_dict.values()
            for entry in entries
            if not entry[1]
        ]
        if unused:
            choice = random.choice(unused)
            for entries in music_dict.values():
                for entry in entries:
                    if entry[0] == choice:
                        entry[1] = True
                        break
            logger.warning(f"Fallback: using unused music: {choice}")
            return choice

        used = [
            entry[0]
            for entries in music_dict.values()
            for entry in entries
        ]
        if used:
            choice = random.choice(used)
            logger.warning(f"Fallback: reusing used music: {choice}")
            return choice
        logger.error("No music found at all in music_dict.")
        return None

    if keyword not in music_dict or not music_dict[keyword]:
        logger.warning(f"No entries found for keyword '{keyword}'. Falling back...")
        return fallback_any_music()

    all_music = sorted(music_dict[keyword], key=lambda x: x[1])  # unused first
    total_batches = math.ceil(len(all_music) / batch_size)

    for batch_num in range(total_batches):
        batch = all_music[batch_num * batch_size : (batch_num + 1) * batch_size]
        prompt = (
            f"Given the keyword '{keyword}', select the most relevant music from the list below. "
            f"Reply ONLY with the best matching direct .mp3 link (no other text):\n\n" +
            "\n".join(f"- {link} : {', '.join(tags)}" for link, used, tags in batch)
        )
        response = llm.predict(prompt)
        logger.info(f'LLM responded with : {response}')
        matches = re.findall(r'https?://[^\s]+\.mp3', response)
        logger.info(f"LLM suggested matches: {matches}")

        for match in matches:
            for entry in all_music:
                if entry[0] == match and not entry[1]:
                    entry[1] = True
                    logger.info(f"Selected music: {match}")
                    return match

    for entry in all_music:
        if not entry[1]:
            entry[1] = True
            logger.warning(f"LLM failed. Using fallback music under keyword '{keyword}': {entry[0]}")
            return entry[0]

    return fallback_any_music()

def add_music(video_path, transcript, space_id, music_dict):
    def mark_music_as_used(keyword, music_path):
        if keyword not in music_dict:
            return
        for music_entry in music_dict[keyword]:
            if music_entry[0] == music_path:
                music_entry[1] = True
                break

    try:
        tags = set()
        for music in music_collection.find({'spaces': {'$in': [space_id]}}):
            tags.update(music['tags'])

        music_prompt_doc = prompts_collection.find_one({'space_id': space_id})
        if not music_prompt_doc or not tags:
            raise HTTPException(status_code=404, detail='No music prompt or tags available.')

        music_prompt = music_prompt_doc['music_prompt']
        json_response = '''
        {
            "music": "music_keyword"
        }
        '''
        try:
            response = llm.predict(music_prompt + json_response + str(transcript) + f'Select the keywords from the AVAILABLE TAGS ONLY : {tags}')
            logger.info(f'{response}')
            json_response = extract_json(response)
            keyword = json_response['music']
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Error processing response from LLM: {e}')

        music_info = list(music_collection.find({'spaces': {'$in': [space_id]}, 'tags': keyword}))
        for music in music_info:
            if keyword in music['tags']:
                if keyword not in music_dict:
                    music_dict[keyword] = []
                if music['file_storage_link'] not in [entry[0] for entry in music_dict[keyword]]:
                    music_dict[keyword].append([music['file_storage_link'], False, music['tags']])

        music_path = get_relevant_music(music_dict, keyword)
        if music_path is None:
            logger.info('No music available...')
            return video_path, music_dict, None

        local_music_path = f'{OUTPUT_DIR_3}/{str(uuid.uuid4())}.mp3'
        download_from_s3(music_path, local_music_path)

        video = VideoFileClip(video_path)
        original_audio = video.audio.volumex(1.0) if video.audio else None
        background_music = AudioFileClip(local_music_path).volumex(0.75)

        if background_music.duration < video.duration:
            music_clips = []
            total_duration = 0
            while total_duration < video.duration:
                music_clips.append(background_music)
                total_duration += background_music.duration
            background_music = concatenate_audioclips(music_clips).set_duration(video.duration)
        else:
            background_music = background_music.set_duration(video.duration)
            if original_audio:
                original_audio = original_audio.set_duration(video.duration)

        safe_duration = round(min(video.duration, getattr(video, 'end', video.duration)) - 0.05, 3)
        video = video.set_duration(safe_duration)
        background_music = background_music.set_duration(safe_duration)
        if original_audio:
            original_audio = original_audio.set_duration(safe_duration)

        composite_audio = CompositeAudioClip([original_audio, background_music]).set_duration(safe_duration) if original_audio else background_music
        music_video = video.set_audio(composite_audio).set_duration(safe_duration)

        music_video_path = f'{OUTPUT_DIR_3}/{str(uuid.uuid4())}.mp4'
        music_video.write_videofile(music_video_path, fps=video.fps, remove_temp=True)
        if not os.path.exists(music_video_path):
            logger.error(f"Music video not created at: {music_video_path}")
            return video_path, music_dict, None
        music_video.close()
        background_music.close()
        logger.info('Background music applied.')
        mark_music_as_used(keyword, music_path)
        return music_video_path, music_dict, [local_music_path, video_path]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error adding the music: {e}')