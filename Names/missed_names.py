import json
import os
import shutil

# -------------------------------------------------------------------------------------
# الإعدادات والمسارات - الرجاء تعديلها لتناسب جهازك
# -------------------------------------------------------------------------------------
videos_source_directory = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"
json_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"
names_directory = r"C:\Users\Stark\Download\myhome\video_rating_app\Names"

# START: MODIFIED SECTION
# مسار ملف التجاهل (سيتم إنشاؤه تلقائياً)
no_ids_file_path = os.path.join(names_directory, "no_ids.txt")
# END: MODIFIED SECTION

# --- دالة لقراءة قائمة التجاهل ---
def load_blacklist():
    """تقرأ ملف no_ids.txt وتعيد مجموعة (set) من أحجام الملفات لتجاهلها."""
    blacklisted_sizes = set()
    if os.path.exists(no_ids_file_path):
        with open(no_ids_file_path, 'r') as f:
            for line in f:
                try:
                    # تحويل كل سطر إلى رقم وإضافته إلى المجموعة
                    blacklisted_sizes.add(int(line.strip()))
                except ValueError:
                    # تجاهل أي أسطر غير صالحة
                    continue
    return blacklisted_sizes

# --- الدالة الخاصة بالمهمة الأولى: تصدير الفيديوهات غير المسماة ---
def export_unnamed_videos():
    print("--- بدء المهمة 1: تصدير الفيديوهات غير المسماة ---")
    
    if not os.path.exists(json_file_path) or not os.path.isdir(videos_source_directory):
        print("خطأ: تأكد من صحة مسار ملف JSON ومجلد الفيديوهات المصدر.")
        return
        
    os.makedirs(names_directory, exist_ok=True)
    
    # START: MODIFIED SECTION
    # تحميل قائمة التجاهل قبل البدء
    blacklisted_sizes = load_blacklist()
    print(f"تم تحميل {len(blacklisted_sizes)} حجم ملف من قائمة التجاهل (no_ids.txt).")
    # END: MODIFIED SECTION
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        video_data = json.load(f)
        
    names_found = set()
    videos_to_copy = []
    
    for filename, details in video_data.items():
        name = details.get("name", "").strip()
        if name:
            names_found.add(name)
        else:
            # START: MODIFIED SECTION
            # التحقق من أن حجم الفيديو ليس في قائمة التجاهل
            file_size = details.get("file_size")
            if file_size and file_size not in blacklisted_sizes:
                videos_to_copy.append(filename)
            elif file_size in blacklisted_sizes:
                # طباعة رسالة للمستخدم بأن الفيديو تم تخطيه
                print(f"  - تخطي الفيديو '{filename}' لأنه موجود في قائمة التجاهل.")
            # END: MODIFIED SECTION

    print(f"\nتم العثور على {len(names_found)} اسم فريد. جاري إنشاء المجلدات...")
    for name in names_found:
        folder_path = os.path.join(names_directory, name)
        os.makedirs(folder_path, exist_ok=True)

    print(f"\nتم العثور على {len(videos_to_copy)} فيديو جديد بدون اسم. جاري نسخها...")
    copied_count = 0
    for filename in videos_to_copy:
        source_path = os.path.join(videos_source_directory, filename)
        destination_path = os.path.join(names_directory, filename)
        
        if os.path.exists(source_path):
            if not os.path.exists(destination_path): # لا ننسخ الملف إذا كان موجودًا بالفعل
                try:
                    shutil.copy(source_path, destination_path)
                    print(f"  - تم نسخ: {filename}")
                    copied_count += 1
                except Exception as e:
                    print(f"  - فشل نسخ {filename}: {e}")
            else:
                print(f"  - الملف '{filename}' موجود بالفعل في الوجهة، تم تخطي النسخ.")
        else:
            print(f"  - تنبيه: لم يتم العثور على الملف المصدر للفيديو {filename}")
            
    print(f"\n--- اكتملت المهمة 1. تم نسخ {copied_count} ملف جديد بنجاح. ---")


# --- الدالة الخاصة بالمهمة الثانية: استيراد الأسماء من المجلدات ---
def import_sorted_names():
    print("\n--- بدء المهمة 2: استيراد الأسماء من المجلدات المصنفة ---")
    
    if not os.path.exists(json_file_path) or not os.path.isdir(names_directory):
        print("خطأ: تأكد من صحة مسار ملف JSON ومجلد الأسماء.")
        return

    size_to_name_map = {}
    print("جاري فحص المجلدات الفرعية...")
    for dirpath, _, filenames in os.walk(names_directory):
        if dirpath != names_directory:
            creator_name = os.path.basename(dirpath)
            for f in filenames:
                if f.endswith('.mp4'):
                    file_path = os.path.join(dirpath, f)
                    file_size = os.path.getsize(file_path)
                    size_to_name_map[file_size] = creator_name
    
    print(f"تم العثور على {len(size_to_name_map)} فيديو مصنف في المجلدات الفرعية.")

    with open(json_file_path, 'r', encoding='utf-8') as f:
        video_data = json.load(f)
    
    backup_path = json_file_path.replace('.json', '_BACKUP.json')
    shutil.copy(json_file_path, backup_path)
    print(f"تم إنشاء نسخة احتياطية للملف في: {backup_path}")

    updated_count = 0
    print("جاري تحديث ملف JSON...")
    for filename, details in video_data.items():
        if not details.get("name", "").strip():
            file_size = details.get("file_size")
            if file_size in size_to_name_map:
                new_name = size_to_name_map[file_size]
                details["name"] = new_name
                print(f"  - تم تحديث اسم الفيديو '{filename}' إلى '{new_name}'")
                updated_count += 1

    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(video_data, f, indent=4, ensure_ascii=False)
    
    print(f"\nتم تحديث {updated_count} سجل في ملف JSON بنجاح.")
    
    # START: MODIFIED SECTION
    # الخطوة الأخيرة: البحث عن الملفات المتبقية وإضافتها إلى قائمة التجاهل
    remaining_files = [f for f in os.listdir(names_directory) if f.endswith('.mp4') and os.path.isfile(os.path.join(names_directory, f))]
    
    if remaining_files:
        print("\n-------------------------------------------------------------")
        print(f"تم العثور على {len(remaining_files)} فيديو متبقي في المجلد الرئيسي '{os.path.basename(names_directory)}'.")
        print("هذه الفيديوهات لم يتم تصنيفها في مجلدات فرعية.")
        
        answer = input("هل تريد إضافتها إلى قائمة التجاهل (no_ids.txt) لتجنب نسخها مستقبلاً؟ (ن/ل): ").lower()
        
        if answer == 'ن' or answer == 'y':
            added_to_blacklist_count = 0
            with open(no_ids_file_path, 'a') as f: # 'a' تعني append (إضافة إلى نهاية الملف)
                for filename in remaining_files:
                    file_path = os.path.join(names_directory, filename)
                    file_size = os.path.getsize(file_path)
                    f.write(f"{file_size}\n")
                    added_to_blacklist_count += 1
            print(f"تمت إضافة أحجام {added_to_blacklist_count} ملف إلى 'no_ids.txt'.")
    # END: MODIFIED SECTION
    
    print(f"\n--- اكتملت المهمة 2. ---")


# --- القائمة الرئيسية لتشغيل السكربت ---
if __name__ == "__main__":
    while True:
        print("\n======================================")
        print("اختر المهمة التي تريد تنفيذها:")
        print("  1. تصدير الفيديوهات غير المسماة (مع تجاهل القائمة السوداء)")
        print("  2. استيراد الأسماء من المجلدات المصنفة (مع تحديث القائمة السوداء)")
        print("  3. خروج")
        print("======================================")
        
        choice = input("الرجاء إدخال رقم الخيار (1, 2, or 3): ")
        
        if choice == '1':
            export_unnamed_videos()
        elif choice == '2':
            import_sorted_names()
        elif choice == '3':
            print("شكراً لاستخدام السكربت. إلى اللقاء!")
            break
        else:
            print("خيار غير صالح. الرجاء إدخال 1, 2, أو 3.")