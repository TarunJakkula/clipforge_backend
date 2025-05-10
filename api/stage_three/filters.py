import moviepy.video.fx.all as vfx
from moviepy.video.fx import blackwhite
import cv2

def gaussian_blur(clip, kernel_size):
    if kernel_size%2==0:
        kernel_size+=1
    def apply_blur(get_frame, t):
        frame = get_frame(t)
        blurred_frame = cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)
        return blurred_frame
    return clip.fl(apply_blur)

def vivid_highlights(clip):
    clip = clip.fx(vfx.colorx, 1.4)
    clip = vfx.lum_contrast(clip, lum=1.4, contrast=0.1)
    return clip

def clean_pop(clip):
    clip = clip.fx(vfx.colorx, 1.3)
    clip = vfx.lum_contrast(clip, lum=1.3, contrast=0.1)
    return clip

def crisp_bright(clip):
    clip = vfx.gamma_corr(clip, 1.1)
    clip = clip.fx(vfx.colorx, 1.3)
    return clip

def modern_pop(clip):
    clip = clip.fx(vfx.colorx, 1.2)
    clip = vfx.lum_contrast(clip, lum=1.4, contrast=0.2)
    return clip

def retro_glow(clip):
    clip = vfx.gamma_corr(clip, 0.9)
    clip = clip.fx(vfx.colorx, 1.2)
    clip = gaussian_blur(clip, 3)
    return clip

def bright_bold(clip):
    clip = vfx.lum_contrast(clip, lum=1.6, contrast=0.2)
    clip = clip.fx(vfx.colorx, 1.3)
    return clip

def cinematic_sharp(clip):
    clip = vfx.gamma_corr(clip, 0.85)
    clip = clip.fx(vfx.colorx, 1.1)
    clip = gaussian_blur(clip, 1)
    return clip

def neon_dream(clip):
    clip = clip.fx(vfx.colorx, 1.5)
    clip = vfx.invert_colors(clip)
    clip = vfx.mask_color(clip, color=(0, 255, 255))
    return clip

def sharp_contrast(clip):
    clip = vfx.lum_contrast(clip, lum=1.8, contrast=0.1)
    clip = clip.fx(vfx.colorx, 1.2)
    return clip

def sleek_fade(clip):
    clip = vfx.lum_contrast(clip, 1.1)
    clip = gaussian_blur(clip, 1)
    return clip

def vivid_glow(clip):
    clip = clip.fx(vfx.colorx, 1.4)
    clip = vfx.gamma_corr(clip, 1.2)
    return clip

def high_contrast_dream(clip):
    clip = vfx.lum_contrast(clip, lum=2.0, contrast=0.2)
    return clip

def golden_hour(clip):
    clip = vfx.gamma_corr(clip, 1.15)
    clip = clip.fx(vfx.colorx, 1.2)
    return clip

def cinematic_contrast(clip):
    clip = vfx.lum_contrast(clip, lum=1.8, contrast=0.1)
    clip = gaussian_blur(clip, 1)
    return clip

def pop_art(clip):
    clip = clip.fx(vfx.colorx, 1.5)
    clip = vfx.lum_contrast(clip, lum=1.3, contrast=0.1)
    clip = vfx.mask_color(clip, color=(255, 0, 0))
    return clip

def film_noir(clip):
    clip = vfx.gamma_corr(clip, 0.85)
    clip = gaussian_blur(clip, 1)
    return clip

def sleep_monochrome(clip):
    clip = vfx.blackwhite(clip)
    return clip

def vibrant_bliss(clip):
    clip = clip.fx(vfx.colorx, 1.6)
    clip = vfx.gamma_corr(clip, 1.1)
    return clip

def urban_chill(clip):
    clip = vfx.lum_contrast(clip, lum=1.4, contrast=0.1)
    clip = clip.fx(vfx.colorx, 1.3)
    clip = gaussian_blur(clip, 1)
    return clip

def neon_nights(clip):
    clip = vfx.invert_colors(clip)
    clip = clip.fx(vfx.colorx, 1.4)
    return clip

def elegant_glow(clip):
    clip = vfx.gamma_corr(clip, 1.2)
    clip = gaussian_blur(clip, 1)
    return clip

def pop_color(clip):
    clip = clip.fx(vfx.colorx, 1.5)
    clip = vfx.mask_color(clip, color=(0, 255, 255))
    return clip

def vintage_cool(clip):
    clip = vfx.gamma_corr(clip, 0.95)
    clip = gaussian_blur(clip, 1)
    return clip

def retro_glow(clip):
    clip = vfx.gamma_corr(clip, 1.1)
    clip = clip.fx(vfx.colorx, 1.3)
    return clip

def crisp_clean(clip):
    clip = vfx.lum_contrast(clip, lum=1.6, contrast=0.1)
    clip = gaussian_blur(clip, 1)
    return clip

def vivid_dream(clip):
    clip = vfx.colorx(clip, 1.7)
    clip = vfx.gamma_corr(clip, 1.3)
    return clip

def cool_breeze(clip):
    clip = vfx.lum_contrast(clip, lum=1.4, contrast=0.2)
    clip = gaussian_blur(clip, 1)
    return clip

def luxe_gold(clip):
    clip = vfx.colorx(clip, 1.5)
    clip = vfx.gamma_corr(clip, 1.2)
    return clip

def monochrome_gold(clip):
    clip = vfx.blackwhite(clip)
    clip = vfx.gamma_corr(clip, 1.1)
    return clip

def electric_blue(clip):
    clip = vfx.colorx(clip, 1.6)
    clip = vfx.mask_color(clip, color=(0, 0, 255))
    return clip

def rose_tint(clip):
    clip = vfx.gamma_corr(clip, 1.2)
    clip = vfx.colorx(clip, 1.4) 
    return clip

def solar_flare(clip):
    clip = vfx.colorx(clip, 1.8)
    clip = vfx.gamma_corr(clip, 1.3)
    return clip

def city_lights(clip):
    clip = vfx.lum_contrast(clip, lum=1.7, contrast=0.1)
    clip = gaussian_blur(clip ,3)  
    return clip

def sunset_vibes(clip):
    clip = vfx.gamma_corr(clip, 1.15)
    clip = vfx.colorx(clip, 1.4)
    return clip

def bold_bright(clip):
    clip = vfx.lum_contrast(clip, lum=2.0, contrast=0.2)
    clip = vfx.colorx(clip, 1.5) 
    return clip

def crimson_tide(clip):
    clip = vfx.colorx(clip, 1.8)
    clip = vfx.gamma_corr(clip, 1.1) 
    return clip

def frosted_glass(clip):
    clip = gaussian_blur(clip, 3)
    clip = vfx.gamma_corr(clip, 1.2)
    return clip

def sunlit_bloom(clip):
    clip = vfx.colorx(clip, 1.5)
    clip = vfx.gamma_corr(clip, 1.3)
    return clip

def cinematic_fade(clip):
    clip = vfx.lum_contrast(clip, lum=1.5, contrast=0.1)
    return clip

def golden_hour(clip):
    clip = vfx.colorx(clip, 1.4)
    clip = vfx.gamma_corr(clip, 1.15)
    return clip

def neon_rush(clip):
    clip = vfx.colorx(clip, 2)
    clip = vfx.mask_color(clip, color=(0, 255, 255))
    return clip

def vibrant_pop(clip):
    clip = vfx.lum_contrast(clip, lum=1.6, contrast=0.2)
    clip = vfx.colorx(clip, 1.6)
    return clip

def urban_grind(clip):
    clip = vfx.colorx(clip, 1.3)
    clip = vfx.gamma_corr(clip, 1.1)
    return clip

def muted_vintage(clip):
    clip = blackwhite(clip)
    clip = vfx.gamma_corr(clip, 0.9)
    return clip

def electric_sunset(clip):
    clip = vfx.colorx(clip, 1.7)
    clip = vfx.gamma_corr(clip, 1.2)
    return clip

def twilight_glow(clip):
    clip = vfx.colorx(clip, 1.6)
    clip = vfx.gamma_corr(clip, 1.1)
    return clip

def epic_fade(clip):
    clip = vfx.lum_contrast(clip, lum=1.7, contrast=0.2)
    clip = vfx.gamma_corr(clip, 1.2)
    return clip

def film_noir_blackandwhite(clip):
    clip = blackwhite(clip)
    clip = vfx.lum_contrast(clip, lum=1.8, contrast=0.1)
    return clip

def golden_fade(clip):
    clip = vfx.colorx(clip, 1.5)
    clip = vfx.gamma_corr(clip, 1.15)
    return clip

def dreamy_bokeh(clip):
    clip = gaussian_blur(clip, 3)
    clip = vfx.lum_contrast(clip, lum=1.4, contrast=0.3)
    return clip

def midnight_glow(clip):
    clip = vfx.colorx(clip, 1.8)
    clip = vfx.gamma_corr(clip, 1.1)
    return clip

def urban_lights(clip):
    clip = vfx.colorx(clip, 1.8)
    clip = vfx.mask_color(clip, color=(0, 255, 255))
    return clip

def mystic_shadows(clip):
    clip = vfx.colorx(clip, 1.5)
    clip = vfx.lum_contrast(clip, lum=2, contrast=-0.1)
    return clip

def desert_mirage(clip):
    clip = vfx.colorx(clip, 1.3)
    clip = vfx.gamma_corr(clip, 1.2)
    return clip

def shadow_play(clip):
    clip = vfx.lum_contrast(clip, lum=1.6, contrast=0.3)
    return clip

def twilight_drift(clip):
    clip = vfx.colorx(clip, 1.4)
    clip = vfx.gamma_corr(clip, 1.1)
    return clip

filters = {
    'vivid_highlights': vivid_highlights,
    'clean_pop': clean_pop,
    'crisp_bright': crisp_bright,
    'modern_pop': modern_pop,
    'retro_glow': retro_glow,
    'bright_bold': bright_bold,
    'cinematic_sharp': cinematic_sharp,
    'neon_dream': neon_dream,
    'sharp_contrast': sharp_contrast,
    'sleek_fade': sleek_fade,
    'vivid_glow': vivid_glow,
    'high_contrast_dream': high_contrast_dream,
    'golden_hour': golden_hour,
    'cinematic_contrast': cinematic_contrast,
    'pop_art': pop_art,
    'film_noir': film_noir,
    'sleep_monochrome': sleep_monochrome,
    'vibrant_bliss': vibrant_bliss,
    'urban_chill': urban_chill,
    'neon_nights': neon_nights,
    'elegant_glow': elegant_glow,
    'pop_color': pop_color,
    'vintage_cool': vintage_cool,
    'retro_glow': retro_glow,
    'crisp_clean': crisp_clean,
    'vivid_dream': vivid_dream,
    'cool_breeze': cool_breeze,
    'luxe_gold': luxe_gold,
    'monochrome_gold': monochrome_gold,
    'electric_blue': electric_blue,
    'rose_tint': rose_tint,
    'solar_flare': solar_flare,
    'city_lights': city_lights,
    'sunset_vibes': sunset_vibes,
    'bold_bright': bold_bright,
    'crimson_tide': crimson_tide,
    'frosted_glass': frosted_glass,
    'sunlit_bloom': sunlit_bloom,
    'cinematic_fade': cinematic_fade,
    'golden_hour': golden_hour,
    'neon_rush': neon_rush,
    'vibrant_pop': vibrant_pop,
    'urban_grind': urban_grind,
    'muted_vintage': muted_vintage,
    'electric_sunset': electric_sunset,
    'twilight_glow': twilight_glow,
    'epic_fade': epic_fade,
    'film_noir_blackandwhite': film_noir_blackandwhite,
    'golden_fade': golden_fade,
    'dreamy_bokeh': dreamy_bokeh,
    'midnight_glow': midnight_glow,
    'urban_lights': urban_lights,
    'mystic_shadows': mystic_shadows,
    'desert_mirage': desert_mirage,
    'shadow_play': shadow_play,
    'twilight_drift': twilight_drift
}