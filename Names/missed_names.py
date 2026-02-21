import json
import os
import shutil
import subprocess
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------------------------------------------------------------------
# الإعدادات والمسارات
# -------------------------------------------------------------------------------------
videos_source_directory = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"
json_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"
names_directory = r"C:\Users\Stark\Download\myhome\video_rating_app\Names"
no_ids_file_path = os.path.join(names_directory, "no_ids.txt")
output_ids_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\video_ids_output.txt"
all_collected_videos_dir = r"C:\Users\Stark\Download\myhome\video_rating_app\All_Collected_Videos"
MAX_WORKERS = os.cpu_count() or 4

# -------------------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------------------
def load_blacklist():
    blacklisted_sizes = set()
    if os.path.exists(no_ids_file_path):
        with open(no_ids_file_path, 'r') as f:
            for line in f:
                try: blacklisted_sizes.add(int(line.strip()))
                except ValueError: continue
    return blacklisted_sizes

def extract_screenshot(video_path, image_output_path):
    if os.path.exists(image_output_path) and os.path.getsize(image_output_path) > 0: return False
    cmd = ['ffmpeg', '-ss', '00:00:01', '-i', video_path, '-frames:v', '1', '-q:v', '2', '-y', image_output_path, '-loglevel', 'error']
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError): return False

def write_image_metadata(image_path, person_name):
    if not os.path.exists(image_path): return False
    cmd = ['exiftool', f'-RegionPersonDisplayName={person_name}', f'-RegionName={person_name}', '-overwrite_original', image_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError): return False

def smart_extract_id(filename):
    match = re.search(r'(\d{10,})', filename)
    if match: return match.group(1)
    return filename

# -------------------------------------------------------------------------------------
# Tasks 1, 2, 3
# -------------------------------------------------------------------------------------
def process_single_unnamed_video(item_data):
    filename, source_path, dest_video_path, dest_image_path = item_data
    actions_taken = []
    if not os.path.exists(dest_video_path):
        try:
            shutil.copy(source_path, dest_video_path)
            actions_taken.append("Video Copied")
        except Exception: pass
    if extract_screenshot(source_path, dest_image_path):
        actions_taken.append("Screenshot Created")
    return filename, actions_taken

def export_unnamed_videos():
    print("\n--- Task 1: Export Unnamed Videos ---")
    if not os.path.exists(json_file_path): return
    os.makedirs(names_directory, exist_ok=True)
    blacklisted_sizes = load_blacklist()
    with open(json_file_path, 'r', encoding='utf-8') as f: video_data = json.load(f)
    tasks = []
    for filename, details in video_data.items():
        if details.get("name", "").strip(): continue
        if details.get("file_size") in blacklisted_sizes: continue
        source_path = os.path.join(videos_source_directory, filename)
        if not os.path.exists(source_path): continue
        dest_video_path = os.path.join(names_directory, filename)
        image_filename = os.path.splitext(filename)[0] + ".jpg"
        dest_image_path = os.path.join(names_directory, image_filename)
        if os.path.exists(dest_video_path) and os.path.exists(dest_image_path): continue
        tasks.append((filename, source_path, dest_video_path, dest_image_path))
    print(f"Prepared {len(tasks)} items...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {executor.submit(process_single_unnamed_video, task): task[0] for task in tasks}
        for future in as_completed(future_to_file):
            try: future.result()
            except Exception: pass
    print("Done.")

def import_sorted_names():
    print("\n--- Task 2: Import Sorted Names ---")
    if not os.path.exists(json_file_path): return
    stem_to_name_map = {}
    for dirpath, _, filenames in os.walk(names_directory):
        if dirpath == names_directory: continue
        creator_name = os.path.basename(dirpath)
        for f in filenames:
            if f.lower().endswith(('.mp4', '.jpg', '.png')):
                stem_to_name_map[os.path.splitext(f)[0]] = creator_name
    with open(json_file_path, 'r', encoding='utf-8') as f: video_data = json.load(f)
    shutil.copy(json_file_path, json_file_path.replace('.json', '_BACKUP.json'))
    count = 0
    for filename, details in video_data.items():
        if not details.get("name", "").strip():
            stem = os.path.splitext(filename)[0]
            if stem in stem_to_name_map:
                details["name"] = stem_to_name_map[stem]
                count += 1
    with open(json_file_path, 'w', encoding='utf-8') as f: json.dump(video_data, f, indent=4)
    print(f"Updated {count} records.")

def process_single_training_item(item_data):
    name, filename, source_path, names_dir = item_data
    person_folder = os.path.join(names_dir, name)
    os.makedirs(person_folder, exist_ok=True)
    image_path = os.path.join(person_folder, os.path.splitext(filename)[0] + ".jpg")
    if os.path.exists(image_path) and os.path.getsize(image_path) > 0: return None
    if extract_screenshot(source_path, image_path):
        write_image_metadata(image_path, name)
        return name
    return None

def training_mode():
    print("\n--- Task 3: Training Mode ---")
    with open(json_file_path, 'r', encoding='utf-8') as f: video_data = json.load(f)
    named = {k: v for k, v in video_data.items() if v.get("name", "").strip()}
    tasks = []
    for filename, details in named.items():
        if not os.path.exists(os.path.join(videos_source_directory, filename)): continue
        if os.path.exists(os.path.join(names_directory, details["name"], os.path.splitext(filename)[0] + ".jpg")): continue
        tasks.append((details["name"], filename, os.path.join(videos_source_directory, filename), names_directory))
    if not tasks: 
        print("Up to date.")
        return
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for _ in as_completed({executor.submit(process_single_training_item, t): t for t in tasks}): pass
    print("Done.")

# -------------------------------------------------------------------------------------
# Task 5: Export IDs (MODIFIED)
# -------------------------------------------------------------------------------------
def export_ids_to_txt_mode():
    print("\n--- New Option: Export IDs to Text File ---")
    
    output_dir = os.path.dirname(output_ids_file_path)
    if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
    if not os.path.exists(all_collected_videos_dir): os.makedirs(all_collected_videos_dir, exist_ok=True)

    # 1. تحميل الـ IDs الموجودة
    existing_ids = set()
    try:
        if os.path.exists(output_ids_file_path):
            with open(output_ids_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if ":" in line: existing_ids.add(line.split(":")[0].strip())
    except Exception: pass

    lines_to_write = []
    files_found_list = [] # قائمة لتخزين كل الملفات التي وجدناها في المجلدات الفرعية
    
    print(f"Scanning subfolders in: {names_directory}")
    
    # 2. المسح (Scan)
    for entry in os.scandir(names_directory):
        if entry.is_dir():
            creator_name = entry.name
            folder_path = entry.path
            for file_entry in os.scandir(folder_path):
                if file_entry.is_file():
                    filename = file_entry.name
                    if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                        
                        # استخراج الـ ID
                        video_id = smart_extract_id(filename)
                        
                        # تجهيز البيانات للملف النصي (فقط إذا كان جديداً)
                        if video_id and video_id not in existing_ids:
                            lines_to_write.append(f"{video_id} : {creator_name}")
                            existing_ids.add(video_id) # نضيفه محلياً لمنع التكرار
                        
                        # *** التغيير هنا ***
                        # نضيف الملف لقائمة المعالجة (للنقل/الحذف) سواء كان الـ ID جديداً أم لا
                        files_found_list.append({
                            'path': file_entry.path,
                            'name': filename,
                            'folder': folder_path
                        })

    # 3. الكتابة في الملف النصي (إذا وجد جديد)
    if lines_to_write:
        with open(output_ids_file_path, 'a', encoding='utf-8') as f:
            for line in lines_to_write: f.write(line + "\n")
        print(f"\n[TXT] Appended {len(lines_to_write)} new IDs.")
    else:
        print("\n[TXT] No new IDs to add (all exist in file).")

    # 4. منطق النقل والحذف (يعتمد على وجود ملفات فعلية وليس على الـ IDs الجديدة)
    total_files = len(files_found_list)
    if total_files == 0:
        print("No videos found in subfolders to move or delete.")
        return

    print(f"\nFound {total_files} videos in subfolders.")
    
    # سؤال النقل
    do_move = input(f"Do you want to MOVE these {total_files} videos to '{os.path.basename(all_collected_videos_dir)}'? (y/n): ").lower()
    
    moved_count = 0
    
    if do_move == 'y':
        for item in files_found_list:
            src = item['path']
            dst = os.path.join(all_collected_videos_dir, item['name'])
            
            if os.path.exists(dst):
                # إذا الملف موجود هناك، لا ننقله لكن نعتبره "تمت معالجته" لغرض الحذف
                pass 
            else:
                try:
                    shutil.move(src, dst)
                    moved_count += 1
                except Exception as e:
                    print(f"Error moving {item['name']}: {e}")
        print(f"Moved {moved_count} files (others already existed).")

    # سؤال الحذف
    # صيغة السؤال تتغير بناء على قرار النقل
    if do_move == 'y':
        confirm_msg = "Do you want to DELETE the source files from subfolders (since they are safe in destination)? (y/n): "
    else:
        confirm_msg = "Do you want to DELETE ALL these files from subfolders (Warning: You chose NOT to move them)? (y/n): "
        
    if input(confirm_msg).lower() == 'y':
        deleted_count = 0
        for item in files_found_list:
            # حذف الفيديو
            video_path = item['path']
            # قد يكون قد تم نقله بالفعل (shutil.move يحذف المصدر)، لذا نتحقق
            if os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    deleted_count += 1
                except Exception: pass
            
            # حذف الصورة المرافقة دائماً
            base_name = os.path.splitext(item['name'])[0]
            img_path = os.path.join(item['folder'], base_name + ".jpg")
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception: pass
                
        print(f"Cleanup complete. Deleted/Cleaned up source files.")
    else:
        print("No files deleted.")

# -------------------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------------------
if __name__ == "__main__":
    while True:
        print("\n======================================")
        print("Digikam Workflow (Parallel Optimized)")
        print("  1. Export Unnamed")
        print("  2. Import Sorted")
        print("  3. Training Mode")
        print("  5. Export IDs & Manage Files")
        print("  4. Exit")
        print("======================================")
        choice = input("Choice: ")
        
        if choice == '1': export_unnamed_videos()
        elif choice == '2': import_sorted_names()
        elif choice == '3': training_mode()
        elif choice == '5': export_ids_to_txt_mode()
        elif choice == '4': break