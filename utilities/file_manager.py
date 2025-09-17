from flask import session, flash, redirect, url_for, render_template
from .config import ALLOWED_EXTENSIONS
from utilities.data_manager import load_data, save_data
from urllib.parse import quote
import os
import re

def url_quote_filter(s):
    return quote(s)


def rename_file(video_name, rating):
    base_name = re.sub(r'^(\d+_)+', '', video_name)
    base_name = base_name.strip().replace(' ', '_')
    new_name = f"{int(round(rating))}_{base_name}"
    return new_name


def update_video_list(data):
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        return data

    video_files = [
        f for f in os.listdir(selected_folder)
        if os.path.isfile(os.path.join(selected_folder, f)) and f.lower().endswith(tuple(ALLOWED_EXTENSIONS))
    ]

    for video in video_files:
        file_path = os.path.join(selected_folder, video)
        try:
            file_size = os.path.getsize(file_path)
        except Exception as e:
            print(f"Error getting file size for {video}: {e}")
            file_size = None

        found = False
        for existing_video, info in data.items():
            if 'file_size' in info and info['file_size'] == file_size:
                found = True
                break
        if not found:
            data[video] = {
                'rating': 1000,
                'win_streak': 0,
                'loss_streak': 0,
                'file_size': file_size,
                'times_shown': 0,
                'total_wins': 0,
                'total_losses': 0,
                'win_rate': 0.0,
                'tags': '',  # إضافة قيمة افتراضية للوسم
                'name': '' # إضافة قيمة افتراضية لـ name
            }
            print(f"Added new video to data: {video} with rating 1000")
    return data


def update_file_names(data):
    updated_data = {}
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        return data
    folder_files = os.listdir(selected_folder)

    processed_files = set()

    for video_name, info in list(data.items()):
        if video_name not in folder_files:
            continue

        rating = info.get('rating', 1000)
        win_streak = info.get('win_streak', 0)
        loss_streak = info.get('loss_streak', 0)
        times_shown = info.get('times_shown', 0)
        total_wins = info.get('total_wins', 0)
        total_losses = info.get('total_losses', 0)
        win_rate = info.get('win_rate', 0.0)
        tags = info.get('tags', '')  # استرداد قيمة الوسم
        name = info.get('name', '')  # <--- إضافة هذا السطر

        file_path = os.path.join(selected_folder, video_name)
        try:
            file_size = os.path.getsize(file_path)
        except Exception as e:
            print(f"Error getting file size for {video_name}: {e}")
            file_size = None

        new_name = rename_file(video_name, rating)

        if video_name != new_name:
            old_path = os.path.join(selected_folder, video_name)
            new_path = os.path.join(selected_folder, new_name)
            try:
                os.rename(old_path, new_path)
                print(f"Renamed: {video_name} -> {new_name}")
            except Exception as e:
                print(f"Error renaming file {video_name}: {e}")
                continue

        updated_data[new_name] = {
            'rating': rating,
            'win_streak': win_streak,
            'loss_streak': loss_streak,
            'file_size': file_size,
            'times_shown': times_shown,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'win_rate': win_rate,
            'tags': tags,  # حفظ قيمة الوسم
            'name': name  # <--- إضافة هذا السطر
        }
        processed_files.add(new_name)

    for file in folder_files:
        if (file not in processed_files and
           file.lower().endswith(tuple(ALLOWED_EXTENSIONS))):

            file_path = os.path.join(selected_folder, file)
            try:
                file_size = os.path.getsize(file_path)
            except Exception as e:
                print(f"Error getting file size for new file {file}: {e}")
                file_size = None

            existing_file = next((name for name, info in data.items()
                                  if info.get('file_size') == file_size), None)

            if existing_file:
                existing_info = data[existing_file]
                updated_data[file] = {
                    'rating': existing_info.get('rating', 1000),
                    'win_streak': existing_info.get('win_streak', 0),
                    'loss_streak': existing_info.get('loss_streak', 0),
                    'file_size': file_size,
                    'times_shown': existing_info.get('times_shown', 0),
                    'total_wins': existing_info.get('total_wins', 0),
                    'total_losses': existing_info.get('total_losses', 0),
                    'win_rate': existing_info.get('win_rate', 0.0),
                    'tags': existing_info.get('tags', ''),  # استرداد قيمة الوسم
                    'name': existing_info.get('name', '')  # <--- إضافة هذا السطر
                }
                print(f"Matched existing file: {file} with {existing_file}")
            else:
                print(
                    f"New file found: {file}. Adding with default rating 1000.")
                updated_data[file] = {
                    'rating': 1000,
                    'win_streak': 0,
                    'loss_streak': 0,
                    'file_size': file_size,
                    'times_shown': 0,
                    'total_wins': 0,
                    'total_losses': 0,
                    'win_rate': 0.0,
                    'tags': '',  # قيمة افتراضية للوسم
                    'name': ''  # <--- إضافة هذا السطر
                }

    return updated_data


def rename_all_videos():
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    data = load_data()
    if not data:
        flash("لا توجد بيانات لإعادة التسمية.", "danger")
        return redirect(url_for('top_videos'))

    updated_data = update_file_names(data)

    save_data(updated_data)
    flash("تمت إعادة تسمية جميع الفيديوهات بنجاح.", "success")
    return redirect(url_for('top_videos'))


def top_videos():
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    data = load_data()
    if not data:
        flash("لا توجد بيانات لعرض الفيديوهات.", "danger")
        return redirect(url_for('index'))

    all_videos_list = sorted(
        data.items(),
        key=lambda x: x[1]['rating'],
        reverse=True)

    # في هذه الدالة، يجب أن تعرض name بدلاً من اسم الملف إذا كانت موجودة
    all_videos_encoded = []
    for video_name, video_info in all_videos_list:
        display_name = video_info.get('name', video_name)  # استخدم 'name' إذا كانت موجودة وإلا فاسم الملف
        all_videos_encoded.append((video_name, video_info['rating'], url_quote_filter(video_name), display_name)) # أضف display_name هنا

    video_count = len(all_videos_encoded)

    return render_template(
        'top_videos.html', all_videos=all_videos_encoded, video_count=video_count)


def allowed_file(filename):
    return '.' in filename and filename.rsplit(
        '.', 1)[1].lower() in ALLOWED_EXTENSIONS