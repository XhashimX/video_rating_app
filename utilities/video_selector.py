import random
from flask import flash

# دالة اختيار الفيديوهات بناءً على الوضع
def choose_videos(data, mode, value=None, num_videos=2):
    """
    Selects videos based on the given mode.
    :param data: Dictionary containing video details.
    :param mode: Competition mode (e.g., top-rated, lowest-rated, etc.).
    :param value: Additional parameter for certain modes.
    :param num_videos: Number of videos to select.
    :return: List of tuples (video_name, rating).
    """
    videos = list(data.items())  # قائمة من tuples (video_name, video_info)

    if mode == 1:  # اختيار فيديوهات عشوائية
        selected = random.sample(videos, min(len(videos), num_videos))
        return [(vid, info['rating']) for vid, info in selected]

    elif mode == 2:  # اختيار أفضل فيديوهات
        sorted_videos = sorted(videos, key=lambda x: x[1]['rating'], reverse=True)
        return [(vid, info['rating']) for vid, info in sorted_videos[:num_videos]]

    elif mode == 3:  # اختيار فيديوهات بتقييم أقل من قيمة معينة
        filtered = [(k, v.get('rating', 1000)) for k, v in videos if v.get('rating', 1000) < (value or float('inf'))]
        random.shuffle(filtered)
        return filtered[:num_videos]

    elif mode == 4:  # اختيار فيديوهات بتقييم أعلى من قيمة معينة
        filtered = [(k, v.get('rating', 1000)) for k, v in videos if v.get('rating', 1000) > (value or 0)]
        random.shuffle(filtered)
        return filtered[:num_videos]

    elif mode == 5:  # اختيار فيديوهات بين رقمين
        # التعامل مع None بشكل آمن
        if value is None or not isinstance(value, dict):
            flash("يجب تحديد قيمتي min_value و max_value.", "danger")
            return []
        min_value = value.get('min_value', 0)
        max_value = value.get('max_value', float('inf'))

        # تصفية الفيديوهات بين القيمتين
        filtered = [(k, v.get('rating', 1000)) for k, v in videos if min_value <= v.get('rating', 1000) <= max_value]
        random.shuffle(filtered)
        return filtered[:num_videos]

    else:
        return []  # إرجاع قائمة فارغة إذا كان الوضع غير صالح