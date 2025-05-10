from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import CompositeVideoClip, ImageClip
from .subtitles_preprocessing import hex_to_rgb
from utils.log_errors import logger
import numpy as np

def create_text_with_all_effects(text, font, font_size, text_color, glow_color, 
                                glow_intensity, stroke_width, stroke_color, 
                                shadow_offset, shadow_blur, shadow_color, font_case):
    if font_case:
        text = text.upper()
    else:
        text = text.lower()
    
    if isinstance(text_color, str):
        text_color = hex_to_rgb(text_color)
    if glow_color and isinstance(glow_color, str):
        glow_color = hex_to_rgb(glow_color)
    if stroke_color and isinstance(stroke_color, str):
        stroke_color = hex_to_rgb(stroke_color)
    if shadow_color and isinstance(shadow_color, str):
        shadow_color = hex_to_rgb(shadow_color)
    
    try:
        font_obj = ImageFont.truetype(font, font_size)
        if glow_color:
            glow_font_obj = ImageFont.truetype(font, font_size)
    except Exception:
        font_obj = ImageFont.load_default(font_size)
        if glow_color:
            glow_font_obj = ImageFont.load_default(font_size)
    
    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    
    text_bbox_base = draw.textbbox((0, 0), text, font=font_obj)
    text_width_base = text_bbox_base[2] - text_bbox_base[0]
    text_height_base = text_bbox_base[3] - text_bbox_base[1]
    
    if stroke_width > 0 :
        text_width_with_stroke = text_width_base + (stroke_width * 2)
        text_height_with_stroke = text_height_base + (stroke_width * 2)
    else:
        text_width_with_stroke = text_width_base
        text_height_with_stroke = text_height_base
        
    text_width = text_width_with_stroke
    text_height = text_height_with_stroke
    
    padding_x = max(100, stroke_width * 3, abs(shadow_offset[0]) + shadow_blur * 3)
    padding_y = max(100, stroke_width * 3, abs(shadow_offset[1]) + shadow_blur * 3)
    
    if glow_color:
        glow_padding = int(font_size * glow_intensity * 0.5)
        padding_x = max(padding_x, glow_padding)
        padding_y = max(padding_y, glow_padding)
    
    canvas_w = text_width + padding_x * 2
    canvas_h = text_height + padding_y * 2
    center_x = canvas_w // 2
    center_y = canvas_h // 2
    result_img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    
    text_x = center_x - text_width_base // 2
    text_y = center_y - text_height_base // 2
    
    if shadow_color and (shadow_offset[0] != 0 or shadow_offset[1] != 0 or shadow_blur > 0):
        shadow_img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        shadow_x = text_x + shadow_offset[0]
        shadow_y = text_y + shadow_offset[1]
        
        if stroke_width > 0:
            shadow_draw.text((shadow_x, shadow_y), text, font=font_obj, fill=shadow_color + (255,), stroke_width=stroke_width, stroke_fill=shadow_color + (255,))
        else:
            shadow_draw.text((shadow_x, shadow_y), text, font=font_obj, fill=shadow_color + (255,))
        if shadow_blur > 0:
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        
        result_img = Image.alpha_composite(result_img, shadow_img)
    
    if glow_color:
        transparency_values = [80, 70, 60, 50, 40, 30, 20, 10]
        num_layers = len(transparency_values)
        stroke_factors = [i / num_layers for i in range(1, num_layers + 1)]
        glow_stroke_widths = [max(1, int(font_size * factor * 0.1)) for factor in stroke_factors]
        
        for gstroke, alpha in zip(glow_stroke_widths, transparency_values):
            temp_img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(temp_img)
            glow_rgba = glow_color + (alpha,)
            draw.text((text_x, text_y), text, font=glow_font_obj, fill=glow_rgba, stroke_width=gstroke)
            result_img = Image.alpha_composite(result_img, temp_img)
    
    if stroke_width > 0 and stroke_color:
        stroke_img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
        stroke_draw = ImageDraw.Draw(stroke_img)
        stroke_draw.text((text_x, text_y), text, font=font_obj, fill=None, stroke_width=stroke_width, stroke_fill=stroke_color + (255,))
        result_img = Image.alpha_composite(result_img, stroke_img)
    
    text_img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_img)
    text_draw.text((text_x, text_y), text, font=font_obj, fill=text_color + (255,))
    result_img = Image.alpha_composite(result_img, text_img)
    return result_img

def overlay_subtitles_with_effects(video_clip, subtitles, font, font_size, text_color, 
                                   glow_color, glow_intensity, stroke_width, stroke_color, 
                                   shadow_offset, shadow_blur, shadow_color, position, font_case):
    try:
        x_offset, y_offset = position
        subtitle_clips = []
        
        for subtitle in subtitles:
            try:
                start_time = float(subtitle['timestamp'][0])
                end_time = float(subtitle['timestamp'][1])
                text = subtitle['text']
                
                effect_img = create_text_with_all_effects(
                    text, font, font_size, text_color, glow_color, 
                    glow_intensity, stroke_width, stroke_color, 
                    shadow_offset, shadow_blur, shadow_color, font_case
                )
                effect_np = np.array(effect_img)
                text_clip = ImageClip(effect_np, transparent=True).set_start(start_time).set_end(end_time)
                
                w, h = video_clip.size
                x = int((w - effect_img.width) // 2 + x_offset * w)
                y = int((h - effect_img.height) // 2 + y_offset * h)
                
                text_clip = text_clip.set_position((x, y))
                subtitle_clips.append(text_clip)
            except Exception as e:
                logger.error(f"Error processing subtitle: {e}")
                continue
                
        return CompositeVideoClip([video_clip, *subtitle_clips])
    except Exception as e:
        logger.error(f"Global error in overlay_subtitles_with_effects: {e}")
        return video_clip