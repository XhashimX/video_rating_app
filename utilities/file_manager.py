import os
import re
from flask import session, flash
from .config import ALLOWED_EXTENSIONS
# تعديل اسم الملف بناءً على مستواه باستخدام بادئة رقمية
def rename_file(video_name, rating):
    # إزالة جميع البادئات الرقمية المتبوعة بـ "_"
    base_name = re.sub(r'^(\d+_)+', '', video_name)
    # إزالة المسافات الزائدة أو الرموز الخاصة
    base_name = base_name.strip().replace(' ', '_')
    # إضافة التقييم كبادئة
    new_name = f"{int(round(rating))}_{base_name}"
    return new_name

# تحديث قائمة الفيديوهات وإضافة تصنيف افتراضي
def update_video_list(data):
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        return data
    video_files = [
        f for f in os.listdir(selected_folder)
        if os.path.isfile(os.path.join(selected_folder, f)) and f.lower().endswith(tuple(ALLOWED_EXTENSIONS))
    ]
    for video in video_files:
        if video not in data:
            data[video] = {
                'rating': 1000,
                'win_streak': 0,
                'loss_streak': 0
            }  # التصنيف الافتراضي مع الستيك
            print(f"Added new video to data: {video} with rating 1000")
    return data

# تحديث أسماء الملفات والتحقق من التعديلات اليدوية
def update_file_names(data):
    """
    يعيد تسمية ملفات الفيديو بناءً على تقييماتها ويحدث بيانات JSON.
    """
    updated_data = {}
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        return data
    folder_files = os.listdir(selected_folder)
    print(f"Folder files: {folder_files}")

    # إنشاء قاموس مؤقت للتتبع الملفات التي تمت معالجتها
    processed_files = set()

    for video_name, info in list(data.items()):
        # تخطي الملفات غير الموجودة في المجلد
        if video_name not in folder_files:
            continue

        rating = info.get('rating', 1000)
        win_streak = info.get('win_streak', 0)
        loss_streak = info.get('loss_streak', 0)
        
        new_name = rename_file(video_name, rating)

        # إعادة تسمية الملف إذا لزم الأمر
        if video_name != new_name:
            old_path = os.path.join(selected_folder, video_name)
            new_path = os.path.join(selected_folder, new_name)
            try:
                os.rename(old_path, new_path)
                print(f"Renamed: {video_name} -> {new_name}")
            except Exception as e:
                print(f"Error renaming file {video_name}: {e}")
                continue

        # تحديث البيانات بالاسم الجديد
        updated_data[new_name] = {
            'rating': rating,
            'win_streak': win_streak,
            'loss_streak': loss_streak
        }
        processed_files.add(new_name)

    # إضافة أي ملفات جديدة تمت إضافتها يدويًا
    for file in folder_files:
        if (file not in processed_files and 
            file.lower().endswith(tuple(ALLOWED_EXTENSIONS))):
            print(f"New file found: {file}. Adding with default rating 1000.")
            updated_data[file] = {
                'rating': 1000,
                'win_streak': 0,
                'loss_streak': 0
            }

    return updated_data

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS