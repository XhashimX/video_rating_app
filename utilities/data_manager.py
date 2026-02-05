import os
import json
from datetime import datetime
from flask import session, flash
from .config import SCRIPT_FOLDER, BACKUP_FOLDER
from urllib.parse import quote

ADDITIONAL_BACKUP_FOLDER = "/storage/emulated/0/mybackup"


def create_backup(data, is_topcut=False, is_archive=False):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = os.path.basename(session.get('selected_folder', ''))

    if is_topcut:
        backup_filename = f"topcut_backup_{timestamp}.json"
    elif is_archive:
        backup_filename = f"tournamentarchive_backup_{timestamp}.json"
    else:
        backup_filename = f"elo_videos_{folder_name}_backup_{timestamp}.json"

    backup_path = os.path.join(BACKUP_FOLDER, backup_filename)

    additional_backup_folder = "/storage/emulated/0/mybackup"
    additional_backup_path = os.path.join(
        additional_backup_folder, backup_filename)

    try:
        with open(backup_path, "w", encoding='utf-8') as backup_file:
            json.dump(data, backup_file, indent=4, ensure_ascii=False)
        print(f"Backup created: {backup_filename}")

        if not os.path.exists(additional_backup_folder):
            os.makedirs(additional_backup_folder)
        with open(additional_backup_path, "w", encoding='utf-8') as additional_backup_file:
            json.dump(
                data,
                additional_backup_file,
                indent=4,
                ensure_ascii=False)
        print(f"Backup also created at: {additional_backup_path}")
    except Exception as e:
        print(f"Error creating backup: {e}")




# --- START OF FILE utilities/data_manager.py (Modified Function Only) ---

def load_data():
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return {}

    folder_name = os.path.basename(selected_folder)
    data_file = os.path.join(SCRIPT_FOLDER, f"elo_videos_{folder_name}.json")
    
    # لا حاجة لطباعة هذه الرسالة في كل مرة لتقليل الضجيج في التيرمينال
    # print(f"Attempting to load data from: {data_file}")

    if os.path.exists(data_file):
        try:
            with open(data_file, "r", encoding='utf-8') as file:
                data = json.load(file)
            
            # START: MODIFIED SECTION
            # لقد قمنا بإلغاء التحديث التلقائي هنا لتسريع البرنامج
            # الفحص اليدوي سيتم عبر دالة منفصلة في app.py
            # from .file_manager import update_video_list
            # data = update_video_list(data)
            # END: MODIFIED SECTION

            # التأكد من صحة البيانات الأساسية فقط دون فحص القرص
            for video_id in data:
                if 'times_shown' not in data[video_id]:
                    data[video_id]['times_shown'] = 0
                if 'name' not in data[video_id]:
                    data[video_id]['name'] = ''

            return data
        except Exception as e:
            print(f"Error loading data file: {e}")
            flash("تعذر تحميل بيانات المسابقة.", "danger")
            return {}
    else:
        print(f"Data file {data_file} does not exist. Creating a new one...")
        try:
            data = {}
            # هنا فقط (عند إنشاء الملف لأول مرة) نحتاج للفحص الإجباري
            from .file_manager import update_video_list
            data = update_video_list(data)

            # ضمان وجود الحقول الأساسية
            for video_id in data:
                if 'times_shown' not in data[video_id]:
                    data[video_id]['times_shown'] = 0
                if 'name' not in data[video_id]: 
                    data[video_id]['name'] = '' 

            with open(data_file, "w", encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            print(f"Created new data file at {data_file}")
            return data
        except Exception as e:
            print(f"Error creating data file: {e}")
            flash("تعذر إنشاء ملف البيانات الجديد.", "danger")
            return {}


def save_data(data):
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return
    create_backup(data)
    folder_name = os.path.basename(selected_folder)
    data_file = os.path.join(SCRIPT_FOLDER, f"elo_videos_{folder_name}.json")
    try:
        with open(data_file, "w", encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        print(f"Data saved to {data_file}")
    except Exception as e:
        print(f"Error saving data file: {e}")
        flash("تعذر حفظ بيانات المسابقة.", "danger")