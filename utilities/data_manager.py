import os
import json
from datetime import datetime
from flask import session, flash
from .config import SCRIPT_FOLDER, BACKUP_FOLDER
from urllib.parse import quote
# مسار النسخ الاحتياطية الإضافي
ADDITIONAL_BACKUP_FOLDER = "/storage/emulated/0/mybackup"

# وظيفة لإنشاء نسخة احتياطية
def create_backup(data):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = os.path.basename(session.get('selected_folder', ''))
    backup_filename = f"elo_videos_{folder_name}_backup_{timestamp}.json"
    backup_path = os.path.join(BACKUP_FOLDER, backup_filename)

    # إضافة مسار النسخ الاحتياطي الثاني
    additional_backup_folder = "/storage/emulated/0/mybackup"
    additional_backup_path = os.path.join(additional_backup_folder, backup_filename)

    try:
        # حفظ النسخة الاحتياطية في المجلد الافتراضي
        with open(backup_path, "w", encoding='utf-8') as backup_file:
            json.dump(data, backup_file, indent=4, ensure_ascii=False)
        print(f"Backup created: {backup_filename}")

        # حفظ النسخة الاحتياطية في المجلد الثاني
        if not os.path.exists(additional_backup_folder):
            os.makedirs(additional_backup_folder)
        with open(additional_backup_path, "w", encoding='utf-8') as additional_backup_file:
            json.dump(data, additional_backup_file, indent=4, ensure_ascii=False)
        print(f"Backup also created at: {additional_backup_path}")
    except Exception as e:
        print(f"Error creating backup: {e}")

# Function to load or create the database
def load_data():
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return {}

    folder_name = os.path.basename(selected_folder)
    data_file = os.path.join(SCRIPT_FOLDER, f"elo_videos_{folder_name}.json")
    print(f"Attempting to load data from: {data_file}")

    # إذا كان الملف موجوداً، قم بتحميل البيانات
    if os.path.exists(data_file):
        try:
            with open(data_file, "r", encoding='utf-8') as file:
                data = json.load(file)
            print(f"Data loaded successfully from {data_file}")
            return data
        except Exception as e:
            print(f"Error loading data file: {e}")
            flash("تعذر تحميل بيانات المسابقة.", "danger")
            return {}
    else:
        # إنشاء قاعدة بيانات جديدة وتحديثها مباشرة مع الفيديوهات الموجودة
        print(f"Data file {data_file} does not exist. Creating a new one...")
        try:
            data = {}
            # استخدام update_video_list لإضافة الفيديوهات الموجودة
            from .file_manager import update_video_list
            data = update_video_list(data)
            
            # حفظ البيانات في الملف الجديد
            with open(data_file, "w", encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            print(f"Created new data file at {data_file}")
            return data
        except Exception as e:
            print(f"Error creating data file: {e}")
            flash("تعذر إنشاء ملف البيانات الجديد.", "danger")
            return {}


# Function to save the database with automatic backup
def save_data(data):
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return
    create_backup(data)
    folder_name = os.path.basename(selected_folder)
    data_file = os.path.join(SCRIPT_FOLDER, f"elo_videos_{folder_name}.json")
    try:
        # حفظ البيانات كما هي دون تعديل الأسماء
        with open(data_file, "w", encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        print(f"Data saved to {data_file}")
    except Exception as e:
        print(f"Error saving data file: {e}")
        flash("تعذر حفظ بيانات المسابقة.", "danger")