from moviepy.editor import CompositeVideoClip, ColorClip, VideoFileClip
from moviepy.video.fx import all as vfx
from .subtitles_preprocessing import *
from utils.mongodb_schemas import *
from utils.log_errors import logger
from fastapi import HTTPException
from .filters import filters
from .effects import *
import uuid, os

OUTPUT_DIR_3 = 'project_clips'

def add_presets(video_path, transcript, preset, clip_id):
    try:
        video = VideoFileClip(video_path).subclip(0, -0.1)
        clip_shape = video.size
        font_size_for_clip = {
            'small': clip_shape[0]//25, 
            'medium': clip_shape[0]//20, 
            'large': clip_shape[0]//15
        }
        font_positions = {
            'bottom': (0, 0.2),
            'center': (0, 0),  
            'top': (0, -0.3),  
        }
        aspect_ratios = {
            'longform': {
                '1_1': (clip_shape[0], clip_shape[0]),
                '16_9': (clip_shape[0], clip_shape[1]),
                '4_3': (clip_shape[0], int(clip_shape[0]*(3/4))),
                '9_16': (clip_shape[0], int(clip_shape[0]*(16/9))),
                '3_4': (clip_shape[0], int(clip_shape[0]*(4/3))),
                '4_5': (clip_shape[0], int(clip_shape[0]*(5/4))),
                '5_4': (clip_shape[0], int(clip_shape[0]*(4/5))),
                '3_2': (clip_shape[0], int(clip_shape[0]*(2/3))),
                '2_3': (clip_shape[0], int(clip_shape[0]*(3/2))),
                '5_8': (clip_shape[0], int(clip_shape[0]*(8/5))),
            },
            'shortform': {
                '1_1': (clip_shape[1], clip_shape[1]),
                '16_9': (int(clip_shape[1]*(9/16)), clip_shape[1]),
                '4_3': (int(clip_shape[1]*(3/4)), clip_shape[1]),
                '9_16': (clip_shape[0], clip_shape[1]),
                '3_4': (int(clip_shape[1]*(4/3)), clip_shape[1]),
                '4_5': (int(clip_shape[1]*(5/4)), clip_shape[1]),
                '5_4': (int(clip_shape[1]*(4/5)), clip_shape[1]),
                '3_2': (int(clip_shape[1]*(2/3)), clip_shape[1]),
                '2_3': (int(clip_shape[1]*(3/2)), clip_shape[1]),
                '5_8': (int(clip_shape[1]*(8/5)), clip_shape[1]),
            }
        }
        stroke_offset = {
            'small': {
                'thin': font_size_for_clip['small'] // 30,
                'regular': font_size_for_clip['small'] // 25,
                'semibold': font_size_for_clip['small'] // 20,
                'bold': font_size_for_clip['small'] // 15
            }, 
            'medium': {
                'thin': font_size_for_clip['medium'] // 30, 
                'regular': font_size_for_clip['medium'] // 25,
                'semibold': font_size_for_clip['medium'] // 20,
                'bold': font_size_for_clip['medium'] // 15 
            }, 
            'large': {
                'thin': font_size_for_clip['large'] // 30, 
                'regular': font_size_for_clip['large'] // 25, 
                'semibold': font_size_for_clip['large'] // 20,
                'bold': font_size_for_clip['large'] // 15 
            }
        }
        shadow_offset = {
            'small': {
                'thin': {
                    'shadow_offset': (font_size_for_clip['small']//30, font_size_for_clip['small']//30), 
                    'shadow_blur': font_size_for_clip['small']//25
                },
                'regular': {
                    'shadow_offset': (font_size_for_clip['small']//25, font_size_for_clip['small']//25), 
                    'shadow_blur': font_size_for_clip['small']//20
                },
                'semibold': {
                    'shadow_offset': (font_size_for_clip['small']//20, font_size_for_clip['small']//20), 
                    'shadow_blur': font_size_for_clip['small']//15
                },
                'bold': {
                    'shadow_offset': (font_size_for_clip['small']//15, font_size_for_clip['small']//15), 
                    'shadow_blur': font_size_for_clip['small']//10
                }
            },
            'medium': {
                'thin': {
                    'shadow_offset': (font_size_for_clip['medium']//30, font_size_for_clip['medium']//30), 
                    'shadow_blur': font_size_for_clip['medium']//25
                },
                'regular': {
                    'shadow_offset': (font_size_for_clip['medium']//25, font_size_for_clip['medium']//25), 
                    'shadow_blur': font_size_for_clip['medium']//20
                },
                'semibold': {
                    'shadow_offset': (font_size_for_clip['medium']//20, font_size_for_clip['medium']//20), 
                    'shadow_blur': font_size_for_clip['medium']//15
                },
                'bold': {
                    'shadow_offset': (font_size_for_clip['medium']//15, font_size_for_clip['medium']//15), 
                    'shadow_blur': font_size_for_clip['medium']//10
                }
            },
            'large': {
                'thin': {
                    'shadow_offset': (font_size_for_clip['large']//30, font_size_for_clip['large']//30), 
                    'shadow_blur': font_size_for_clip['large']//25
                },
                'regular': {
                    'shadow_offset': (font_size_for_clip['large']//25, font_size_for_clip['large']//25), 
                    'shadow_blur': font_size_for_clip['large']//20
                },
                'semibold': {
                    'shadow_offset': (font_size_for_clip['large']//20, font_size_for_clip['large']//20), 
                    'shadow_blur': font_size_for_clip['large']//15
                },
                'bold': {
                    'shadow_offset': (font_size_for_clip['large']//15, font_size_for_clip['large']//15), 
                    'shadow_blur': font_size_for_clip['large']//10
                }
            }
        }
        video_aspect_ratio = video.size
        if video_aspect_ratio[0] > video_aspect_ratio[1]:
            video_aspect_form = 'longform'
        elif video_aspect_ratio[0] < video_aspect_ratio[1]:
            video_aspect_form = 'shortform'
            
        # Variables
        logger.info(f'Preset options : {preset}')
        aspect_ratio = preset['aspectRatio']
        apply_filter = filters.get(preset['filter'])
        if apply_filter is None:
            raise HTTPException(status_code=400, detail=f"Invalid filter preset: {preset['filter']}")
        
        background_color = preset['backgroundColor']
        font_style = preset['font']
        font_color = preset['fontColor']
        font_size = preset['fontSize'].lower()
        font_position = font_positions[preset['fontPosition'].lower()]
        scale_value = int(preset['scaling'])
        font_case = preset['fontCapitalization']
        
        stroke_width_key = preset.get('strokeWidth', '').lower()
        shadow_width_key = preset.get('shadowWidth', '').lower()
        stroke_width = stroke_offset[font_size].get(stroke_width_key, 0)
        shadow_params = shadow_offset[font_size].get(shadow_width_key, {'shadow_offset': (0, 0), 'shadow_blur': 0})
        shadow_offset_value = shadow_params['shadow_offset']
        shadow_blur = shadow_params['shadow_blur']
        stroke_color = preset['strokeColor']
        shadow_color = (0, 0, 0)
        glow_color = preset['glowColor']
        
        logger.info('Applying filters started...')
        try:
            clip_with_filter = apply_filter(video)
            logger.info('Filter applied...')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Error applying filter :{e}')
        
        output_path = f'{OUTPUT_DIR_3}/{str(uuid.uuid4())}.mp4'
        scaling_factor = max(0.1, 1 + ((int(scale_value) - 100) / 100.0))
        scaled_video = vfx.resize(clip_with_filter, scaling_factor)
        clip_word_level = clips_collection.find_one({'clip_id': clip_id})
        extracted_word_level = extract_word_level(clip_word_level['clip_transcript']['word_level_timestamps'], transcript)
        transcript = normalize_sequential_timestamps(extracted_word_level, video.duration)
        logger.info(transcript)
        final_clip = overlay_subtitles_with_effects(
            scaled_video, 
            transcript, 
            font_style, 
            font_size_for_clip[font_size], 
            font_color,
            glow_color=glow_color,
            glow_intensity=10,
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            shadow_offset=shadow_offset_value,
            shadow_blur=shadow_blur,
            shadow_color=shadow_color,
            position=font_position,
            font_case=font_case
        )
        logger.info('All text effects applied in a single layer.')
        
        background_clip = ColorClip(size=aspect_ratios[video_aspect_form][aspect_ratio], color=hex_to_rgb(background_color), duration=scaled_video.duration)
        aspected_clip = CompositeVideoClip([background_clip, final_clip.set_position('center')])
        logger.info('Aspect ratio created and video overlayed.')
        
        output_fps = video.fps or 60
        safe_duration = round(min(aspected_clip.duration, getattr(aspected_clip, 'end', aspected_clip.duration)) - 0.05, 3)
        aspected_clip = aspected_clip.set_duration(safe_duration)
        aspected_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=output_fps, preset='medium', bitrate='8000k')

        aspected_clip.close()
        scaled_video.close()
        final_clip.close()
        video.close()
        return output_path, transcript, video_path
    
    except Exception as e:
        logger.error(f"Error in add_presets: {e}")
        raise HTTPException(status_code=500, detail=f'Error applying presets: {e}')