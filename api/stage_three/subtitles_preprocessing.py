from fastapi import HTTPException
import re

def extract_word_level(formatted_word_level, transcript):
    try:
        extracted_data = []
        for stamp in transcript:
            start_time, end_time = stamp['timestamp']
            expected_text = stamp['text'].strip().lower().split()
            words_in_range = []
            extracted_words = []

            for word_level in formatted_word_level:
                if not (word_level['timestamp'][1] < start_time or word_level['timestamp'][0] > end_time):
                    for word in word_level['word_level']:
                        word_start, word_end = word['timestamp']
                        word_text = word['word'].strip().lower()

                        if start_time <= word_start <= end_time and start_time <= word_end <= end_time:
                            if word_text in expected_text:
                                words_in_range.append({
                                    'word': word['word'],
                                    'timestamp': word['timestamp']
                                })
                                extracted_words.append(word_text)
            if len(extracted_words) < len(expected_text):
                for word in expected_text[len(extracted_words):]:
                    words_in_range.append({
                        'word': word,
                        'timestamp': [end_time, end_time + 0.2]
                    })

            extracted_data.append({
                'timestamp': stamp['timestamp'],
                'text': stamp['text'],
                'word_level': words_in_range
            })
        return extracted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unable to extract word-level timestamps: {str(e)}')

def normalize_sequential_timestamps(word_data, video_duration, max_words=4, max_chars=20, pause_threshold=0.6):
    try:
        all_words = []
        for segment in word_data:
            all_words.extend(segment.get("word_level", []))

        captions = []
        current_caption = []
        group_start = None
        prev_end = 0.0

        for i, word_info in enumerate(all_words):
            word = word_info["word"]
            start, end = word_info["timestamp"]

            if group_start is None:
                group_start = start

            if current_caption and start - prev_end > pause_threshold:
                group_end = current_caption[-1]["timestamp"][1]
                text = " ".join(w["word"] for w in current_caption)
                captions.append({
                    "text": text,
                    "timestamp": [round(group_start, 3), round(group_end, 3)]
                })
                current_caption = []
                group_start = start

            current_caption.append({"word": word, "timestamp": [start, end]})
            prev_end = end

            # Conditions to break caption
            words_so_far = len(current_caption)
            text_so_far = " ".join(w["word"] for w in current_caption)
            ends_with_punct = re.search(r"[.?!]", word)

            if words_so_far >= max_words or len(text_so_far) >= max_chars or ends_with_punct:
                group_end = current_caption[-1]["timestamp"][1]
                captions.append({
                    "text": text_so_far,
                    "timestamp": [round(group_start, 3), round(group_end, 3)]
                })
                current_caption = []
                group_start = None

        if current_caption:
            group_end = current_caption[-1]["timestamp"][1]
            text = " ".join(w["word"] for w in current_caption)
            captions.append({
                "text": text,
                "timestamp": [round(group_start, 3), round(group_end, 3)]
            })
        if not captions:
            return []
        real_start = captions[0]['timestamp'][0]
        real_end = captions[-1]['timestamp'][1]
        real_span = real_end - real_start
        scaling_factor = video_duration / real_span if abs(video_duration - real_span) > 0.2 else 1.0

        adjusted = []
        current_time = 0.0
        for i, cap in enumerate(captions):
            if i == 0:
                start = 0.0
            else:
                raw_gap = cap["timestamp"][0] - captions[i-1]["timestamp"][1]
                start = current_time + (raw_gap * scaling_factor)
            duration = (cap["timestamp"][1] - cap["timestamp"][0]) * scaling_factor
            end = start + duration
            current_time = end
            adjusted.append({
                "text": cap["text"],
                "timestamp": [round(start, 3), round(end, 3)]
            })

        if abs(adjusted[-1]["timestamp"][1] - video_duration) > 0.1:
            adjusted[-1]["timestamp"][1] = round(video_duration, 3)
        return adjusted
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while normalizing timestamps: {e}")
    
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))