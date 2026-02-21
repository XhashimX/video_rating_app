import os
import json
import subprocess
import shutil
import cv2

# الإعدادات
WORKING_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\Names"
PHOTO_DB = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo pic.json"
VIDEO_DB = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"
EXIFTOOL_PATH = "exiftool.exe"
NAME_CACHE_FILE = os.path.join(WORKING_DIR, "name_to_folder_cache.json")

def load_cache():
    if os.path.exists(NAME_CACHE_FILE):
        try:
            with open(NAME_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_cache(cache_data):
    with open(NAME_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=4)

def get_metadata_name(file_path):
    try:
        cmd = [EXIFTOOL_PATH, "-s3", "-RegionName", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        name = result.stdout.strip()
        if "," in name: name = name.split(",")[0].strip()
        return name if name else None
    except Exception as e:
        print(f"Error reading metadata: {e}")
        return None

def process_photos():
    print("--- Start Processing Photos ---")
    with open(PHOTO_DB, 'r', encoding='utf-8') as f: data = json.load(f)
    updated_count = 0
    for filename in os.listdir(WORKING_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            file_path = os.path.join(WORKING_DIR, filename)
            person_name = get_metadata_name(file_path)
            if person_name:
                file_size = os.path.getsize(file_path)
                for key, value in data.items():
                    if value.get("file_size") == file_size:
                        value["name"] = person_name
                        print(f"Updated: {key} -> Name: {person_name}")
                        updated_count += 1
                        break
    with open(PHOTO_DB, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Finished. Updated {updated_count} entries.")

def extract_video_frame(video_path, output_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return False
    cap.set(cv2.CAP_PROP_POS_MSEC, 2000)
    success, frame = cap.read()
    if success: cv2.imwrite(output_path, frame)
    cap.release()
    return success

def video_mode_step1():
    print("--- Extracting Frames from Videos ---")
    for filename in os.listdir(WORKING_DIR):
        if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            video_path = os.path.join(WORKING_DIR, filename)
            image_path = os.path.join(WORKING_DIR, os.path.splitext(filename)[0] + ".jpg")
            if os.path.exists(image_path):
                print(f"Skipping: Frame already exists for {filename}")
                continue
            if extract_video_frame(video_path, image_path):
                print(f"Frame extracted: {image_path}")

def get_target_folder(person_name, cache):
    if person_name in cache:
        folder_name = cache[person_name]
        print(f"Cache hit: Using '{folder_name}' for '{person_name}'")
        return folder_name

    existing_dirs = [d for d in os.listdir(WORKING_DIR) if os.path.isdir(os.path.join(WORKING_DIR, d))]
    
    if person_name in existing_dirs:
        cache[person_name] = person_name
        return person_name

    for folder in existing_dirs:
        if person_name.lower() in folder.lower():
            # تم تغيير السؤال والمنطق هنا
            confirm = input(f"Found folder '{folder}' for name '{person_name}'. Use it? (Y/n): ").lower().strip()
            if confirm != 'n': # أي شيء ليس 'n' يعتبر موافقة
                cache[person_name] = folder
                return folder

    print(f"No matching folder for '{person_name}'.")
    choice = input(f"Options: [1] Create folder '{person_name}' | [2] Type custom folder name: ")
    
    final_folder_name = ""
    if choice == "1":
        final_folder_name = person_name
    else:
        final_folder_name = input("Enter custom folder name: ")
    
    new_dir = os.path.join(WORKING_DIR, final_folder_name)
    os.makedirs(new_dir, exist_ok=True)
    cache[person_name] = final_folder_name
    return final_folder_name

def video_mode_step2():
    print("--- Organizing Videos by Tagged Frames (with Memory) ---")
    name_cache = load_cache()
    
    try: # <--- بداية البلوك المضمون
        files_to_process = [f for f in os.listdir(WORKING_DIR) if f.lower().endswith(('.jpg', '.jpeg'))]
        for filename in files_to_process:
            img_path = os.path.join(WORKING_DIR, filename)
            if not os.path.exists(img_path): continue # للتأكد أن الملف لم يُحذف في جولة سابقة

            person_name = get_metadata_name(img_path)
            
            if person_name:
                base_name = os.path.splitext(filename)[0]
                video_filename = None
                for ext in ['.mp4', '.mov', '.avi', '.mkv']:
                    v_file = base_name + ext
                    if os.path.exists(os.path.join(WORKING_DIR, v_file)):
                        video_filename = v_file
                        break
                
                if video_filename:
                    target_folder_name = get_target_folder(person_name, name_cache)
                    target_dir = os.path.join(WORKING_DIR, target_folder_name)
                    
                    shutil.move(os.path.join(WORKING_DIR, video_filename), os.path.join(target_dir, video_filename))
                    os.remove(img_path)
                    print(f"Moved {video_filename} to {target_folder_name} and cleaned up.")

    finally: # <--- هذا الجزء سيعمل دائماً
        print("\n--- Saving decisions to cache file... ---")
        save_cache(name_cache)
        print("--- Cache saved. Your choices will be remembered. ---")


def main():
    print("1. Photos Mode (Update JSON)")
    print("2. Videos Mode - Step 1: Extract Frames")
    print("3. Videos Mode - Step 2: Organize Videos (with Cache)")
    choice = input("Enter your choice (1/2/3): ")

    if choice == "1":
        process_photos()
    elif choice == "2":
        video_mode_step1()
    elif choice == "3":
        video_mode_step2()
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()