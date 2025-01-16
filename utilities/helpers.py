from urllib.parse import quote, unquote
from flask import render_template, session, flash
from .data_manager import load_data, save_data
from .file_manager import update_video_list, update_file_names
from .video_selector import choose_videos
from .config import BACKUP_FOLDER
import os
from flask import send_from_directory
# تعريف فلتر 'quote' ليكون متاحاً في القوالب
def url_quote_filter(s):
    return quote(s)

# تحديد المستوى بناءً على التقييم
def get_level(rating):
    if rating > 2000:
        return 1
    elif rating > 1800:
        return 2
    elif rating > 1600:
        return 3
    elif rating > 1400:
        return 4
    elif rating > 1200:
        return 5
    else:
        return 6
    
def start_new_competition(mode=None, num_videos=2, value=None):
    """
    Starts a new competition by selecting videos based on the mode.
    :param mode: Competition mode.
    :param num_videos: Number of videos to select (>=2).
    :param value: Additional parameter for certain modes.
    :return: List of selected videos or None if not enough videos.
    """
    data = load_data()
    if not data:
        flash("لا توجد بيانات للمنافسة.", "danger")
        return None

    data = update_video_list(data)  # تحديث قائمة الفيديوهات
    data = update_file_names(data)  # تعديل أسماء الفيديوهات
    save_data(data)  # حفظ البيانات

    if mode is None:
        mode = 1  # الوضع الافتراضي (عشوائي)

    # التأكد من وجود عدد كافٍ من الفيديوهات
    num_videos = max(2, num_videos)
    available_videos = len(data)
    if available_videos < num_videos:
        flash("لا يوجد عدد كافٍ من الفيديوهات للمسابقة.", "danger")
        return None

    # إعداد القيم الخاصة بالوضع 5 (بين قيمتين)
    if mode == 5:
        min_value = value.get('min_value', 0)
        max_value = value.get('max_value', float('inf'))
        value = {'min_value': min_value, 'max_value': max_value}

    chosen_videos = choose_videos(data, mode, value, num_videos)
    if not chosen_videos or len(chosen_videos) < num_videos:
        flash("لا يوجد عدد كافٍ من الفيديوهات بعد الفلترة.", "danger")
        return None

    # إنشاء قائمة الفيديوهات للمسابقة
    competition_videos = [
        {'id': vid, 'rating': data.get(vid, {}).get('rating', 1000), 'title': vid}
        for vid, rating in chosen_videos
    ]
    for video in competition_videos:
        video['id_encoded'] = quote(video['id'])

    print(f"Rendering select_winner.html with competition_videos: {competition_videos}")
    return competition_videos

def video_handler(filename):
    # فك التشفير مرة واحدة فقط
    filename_decoded = unquote(filename)
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))
    
    # التأكد من وجود الملف
    file_path = os.path.join(selected_folder, filename_decoded)
    if not os.path.exists(file_path):
        flash(f"الملف {filename_decoded} غير موجود.", "danger")
        return redirect(url_for('index'))
    
    return send_from_directory(selected_folder, filename_decoded)