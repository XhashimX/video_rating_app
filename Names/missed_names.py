import json
import os
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed # للتسريع (المعالجة المتوازية)

# -------------------------------------------------------------------------------------
# الإعدادات والمسارات
# -------------------------------------------------------------------------------------
videos_source_directory = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"
json_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"
names_directory = r"C:\Users\Stark\Download\myhome\video_rating_app\Names"
no_ids_file_path = os.path.join(names_directory, "no_ids.txt")

# عدد العمليات المتوازية (يمكنك زيادته إذا كان جهازك قوياً جداً، مثلاً 8 أو 16)
MAX_WORKERS = os.cpu_count() or 4 

# -------------------------------------------------------------------------------------
# دوال مساعدة (Helper Functions)
# -------------------------------------------------------------------------------------

def load_blacklist():
    """قراءة قائمة التجاهل."""
    blacklisted_sizes = set()
    if os.path.exists(no_ids_file_path):
        with open(no_ids_file_path, 'r') as f:
            for line in f:
                try:
                    blacklisted_sizes.add(int(line.strip()))
                except ValueError:
                    continue
    return blacklisted_sizes

def extract_screenshot(video_path, image_output_path):
    """استخراج لقطة شاشة فقط إذا لم تكن موجودة."""
    # التحقق الذكي: إذا الصورة موجودة وحجمها أكبر من 0، نتخطى
    if os.path.exists(image_output_path) and os.path.getsize(image_output_path) > 0:
        return False # لم نقم بشيء جديد (موجودة مسبقاً)
        
    cmd = [
        'ffmpeg',
        '-ss', '00:00:01',
        '-i', video_path,
        '-frames:v', '1',
        '-q:v', '2',
        '-y',
        image_output_path,
        '-loglevel', 'error'
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True # تم الإنشاء بنجاح
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        print("Error: FFmpeg not found.")
        return False

def write_image_metadata(image_path, person_name):
    """كتابة الميتاداتا."""
    # ملاحظة: Exiftool بطيء قليلاً، لذا نتأكد أولاً
    if not os.path.exists(image_path):
        return False

    cmd = [
        'exiftool',
        f'-RegionPersonDisplayName={person_name}',
        f'-RegionName={person_name}',
        '-overwrite_original',
        image_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        print("Error: ExifTool not found.")
        return False

# -------------------------------------------------------------------------------------
# المهمة 1: تصدير غير المسمى (To-Do List)
# -------------------------------------------------------------------------------------
def process_single_unnamed_video(item_data):
    """دالة لمعالجة فيديو واحد (تستخدم داخل ThreadPool)."""
    filename, source_path, dest_video_path, dest_image_path = item_data
    
    actions_taken = []
    
    # 1. نسخ الفيديو (فقط إذا لم يكن موجوداً)
    if not os.path.exists(dest_video_path):
        try:
            shutil.copy(source_path, dest_video_path)
            actions_taken.append("Video Copied")
        except Exception:
            pass # فشل النسخ
    
    # 2. استخراج الصورة (فقط إذا لم تكن موجودة)
    # نستخدم extract_screenshot التي تتحقق بنفسها من الوجود
    if extract_screenshot(source_path, dest_image_path):
        actions_taken.append("Screenshot Created")
        
    return filename, actions_taken

def export_unnamed_videos():
    print("\n--- Task 1: Export Unnamed Videos (Parallel Mode) ---")
    
    if not os.path.exists(json_file_path): return
    os.makedirs(names_directory, exist_ok=True)
    blacklisted_sizes = load_blacklist()
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        video_data = json.load(f)
        
    tasks = []
    
    # تحضير قائمة المهام
    for filename, details in video_data.items():
        if details.get("name", "").strip():
            continue
            
        file_size = details.get("file_size")
        if file_size and file_size in blacklisted_sizes:
            continue

        source_path = os.path.join(videos_source_directory, filename)
        if not os.path.exists(source_path):
            continue

        dest_video_path = os.path.join(names_directory, filename)
        
        # اسم الصورة
        image_filename = os.path.splitext(filename)[0] + ".jpg"
        dest_image_path = os.path.join(names_directory, image_filename)
        
        # التحقق الذكي قبل الإضافة للمهام:
        # إذا كان الفيديو موجوداً والصورة موجودة، لا داعي لإضافة المهمة أصلاً!
        video_exists = os.path.exists(dest_video_path)
        image_exists = os.path.exists(dest_image_path)
        
        if video_exists and image_exists:
            continue # تخطي كامل (توفير وقت)

        tasks.append((filename, source_path, dest_video_path, dest_image_path))

    print(f"Prepared {len(tasks)} items to process. Starting parallel execution with {MAX_WORKERS} workers...")
    
    new_count = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # إرسال المهام
        future_to_file = {executor.submit(process_single_unnamed_video, task): task[0] for task in tasks}
        
        for future in as_completed(future_to_file):
            filename = future_to_file[future]
            try:
                fname, actions = future.result()
                if actions:
                    print(f"  [To-Do] {fname}: {', '.join(actions)}")
                    new_count += 1
            except Exception as e:
                print(f"  [Error] {filename}: {e}")
            
    print(f"\n--- Done. Processed {new_count} new items. ---")

# -------------------------------------------------------------------------------------
# المهمة 2: استيراد المصنف (Import Logic) - سريعة بطبيعتها ولا تحتاج توازي
# -------------------------------------------------------------------------------------
def import_sorted_names():
    print("\n--- Task 2: Import Sorted Names ---")
    
    if not os.path.exists(json_file_path): return

    stem_to_name_map = {}
    print("Scanning subdirectories...")
    for dirpath, _, filenames in os.walk(names_directory):
        if dirpath == names_directory: continue
        creator_name = os.path.basename(dirpath)
        for f in filenames:
            if f.lower().endswith(('.mp4', '.jpg', '.jpeg', '.png')):
                stem_to_name_map[os.path.splitext(f)[0]] = creator_name
    
    print(f"Found {len(stem_to_name_map)} classified items.")

    with open(json_file_path, 'r', encoding='utf-8') as f:
        video_data = json.load(f)
    
    shutil.copy(json_file_path, json_file_path.replace('.json', '_BACKUP.json'))

    updated_count = 0
    for filename, details in video_data.items():
        if not details.get("name", "").strip():
            current_stem = os.path.splitext(filename)[0]
            if current_stem in stem_to_name_map:
                details["name"] = stem_to_name_map[current_stem]
                print(f"  - [Matched] '{filename}' -> '{stem_to_name_map[current_stem]}'")
                updated_count += 1
            
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(video_data, f, indent=4, ensure_ascii=False)
    
    print(f"\nUpdated {updated_count} records.")
    
    # Blacklist check
    remaining_files = [f for f in os.listdir(names_directory) 
                       if f.endswith('.mp4') and os.path.isfile(os.path.join(names_directory, f))]
    
    if remaining_files:
        print(f"\nFound {len(remaining_files)} remaining un-sorted videos.")
        if input("Add remaining to Blacklist? (y/n): ").lower() == 'y':
            with open(no_ids_file_path, 'a') as f:
                for filename in remaining_files:
                    path = os.path.join(names_directory, filename)
                    f.write(f"{os.path.getsize(path)}\n")
            print("Blacklist updated.")

# -------------------------------------------------------------------------------------
# المهمة 3: وضع التدريب (Training Mode) - المسرع جداً
# -------------------------------------------------------------------------------------
def process_single_training_item(item_data):
    """دالة لمعالجة عنصر تدريب واحد (توازي)."""
    name, filename, source_path, names_dir = item_data
    
    # 1. إنشاء المجلد (Thread-safe عادةً في OS الحديثة، لكن وجود exists يحمينا)
    person_folder = os.path.join(names_dir, name)
    if not os.path.exists(person_folder):
        try:
            os.makedirs(person_folder, exist_ok=True)
        except FileExistsError:
            pass 

    image_filename = os.path.splitext(filename)[0] + ".jpg"
    image_path = os.path.join(person_folder, image_filename)
    
    # التحقق الذكي: هل الصورة موجودة؟
    if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
        # هنا يمكنك إضافة فحص للميتاداتا إذا أردت دقة قصوى، لكن للسرعة سنفترض أنها جاهزة
        return None # تخطي
    
    # إذا لم تكن موجودة، قم بالعملية الكاملة
    if extract_screenshot(source_path, image_path):
        if write_image_metadata(image_path, name):
            return f"{name}/{image_filename}"
            
    return None

def training_mode():
    print("\n--- Task 3: Training Mode (Parallel & Smart) ---")
    
    if not os.path.exists(json_file_path): return
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        video_data = json.load(f)
        
    named_videos = {k: v for k, v in video_data.items() if v.get("name", "").strip()}
    
    if not named_videos:
        print("No named videos found.")
        return
        
    print(f"Found {len(named_videos)} named videos. Preparing tasks...")
    
    tasks = []
    # تحضير المهام
    for filename, details in named_videos.items():
        name = details["name"]
        source_path = os.path.join(videos_source_directory, filename)
        
        # فحص سريع لوجود الملف المصدري
        if not os.path.exists(source_path):
            continue
            
        # التحقق الذكي المسبق (لتوفير إنشاء الـ Threads إذا لم يكن هناك داعٍ)
        person_folder = os.path.join(names_directory, name)
        image_filename = os.path.splitext(filename)[0] + ".jpg"
        final_image_path = os.path.join(person_folder, image_filename)
        
        if os.path.exists(final_image_path):
            continue # تخطي فوري
            
        tasks.append((name, filename, source_path, names_directory))
    
    if not tasks:
        print("All training images are already up to date! Nothing to do.")
        return

    print(f"Starting processing for {len(tasks)} new/missing images using {MAX_WORKERS} threads...")
    
    processed_count = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_item = {executor.submit(process_single_training_item, task): task for task in tasks}
        
        for future in as_completed(future_to_item):
            try:
                result = future.result()
                if result:
                    print(f"  [New] Generated: {result}")
                    processed_count += 1
            except Exception as e:
                print(f"  [Error] {e}")

    print(f"\n--- Training Update Complete. Generated {processed_count} new images. ---")

# -------------------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------------------
if __name__ == "__main__":
    while True:
        print("\n======================================")
        print("Digikam Workflow (Parallel Optimized)")
        print("  1. Export Unnamed (Smart & Fast)")
        print("  2. Import Sorted")
        print("  3. Training Mode (Smart & Fast)")
        print("  4. Exit")
        print("======================================")
        choice = input("Choice: ")
        
        if choice == '1': export_unnamed_videos()
        elif choice == '2': import_sorted_names()
        elif choice == '3': training_mode()
        elif choice == '4': break