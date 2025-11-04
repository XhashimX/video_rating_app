# START: FULL SCRIPT
import os
import re
import shutil
import time
import subprocess
import questionary

try:
    import pyanime4k
    import cv2
    PYANIME4K_AVAILABLE = True
except ImportError:
    PYANIME4K_AVAILABLE = False

# --- 1. الإعدادات والمسارات الأساسية ---
BASE_UPSCALE_DIR = "C:/Users/Stark/Download/myhome/video_rating_app/upscaled_media"
TO_UPSCALE_DIR = os.path.join(BASE_UPSCALE_DIR, "to_upscale")
UPSCALED_DIR = BASE_UPSCALE_DIR

SOURCE_SYNC_DIR = "C:/Users/Stark/Download/myhome/video_rating_app/NS/TikTok/ELO TIK"

# --- 2. دوال مساعدة ---

def get_base_name(filename):
    """يزيل البادئة الرقمية (مثل 123_ أو 1234_) من اسم الملف لإرجاع الاسم الأساسي."""
    return re.sub(r'^\d{3,4}_', '', filename)

def run_command(command):
    """لتشغيل الأوامر في الطرفية وعرض المخرجات مباشرة."""
    print("\n" + "="*20 + f"\n🚀 Executing Command:\n{' '.join(command)}\n" + "="*20 + "\n")
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace'
        )
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()
        if rc != 0:
            print(f"\n❌ Command finished with an error (exit code: {rc}).")
        else:
            print(f"\n✅ Command finished successfully.")
        return rc
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return -1

# --- 3. دوال المنطق الأساسي ---

# START: MODIFIED SECTION - تم تبسيط هذه الدالة
def get_anime4k_options():
    """للحصول على خيارات Anime4K من المستخدم (إعدادات المعالج)."""
    model_choices = ['acnet-gan', 'acnet-hdn0', 'acnet-hdn1', 'acnet-hdn2', 'acnet-hdn3', 'arnet-hdn']
    options = {}
    options['model_name'] = questionary.select("Select the Anime4K model to use:", choices=model_choices, default='acnet-gan').ask()
    options['processor_name'] = questionary.select("Select the processor to use:", choices=['cuda', 'opencl', 'cpu'], default='cuda').ask()
    options['device_id'] = int(questionary.text("Enter device ID (default 0):", default="0").ask())
    return options
# END: MODIFIED SECTION

def upscale_images():
    """واجهة رفع جودة الصور."""
    print("\n--- Upscaling Images with Anime4K ---")
    options = get_anime4k_options()

    try:
        options['scale_factor'] = float(questionary.text("Enter scale factor for images (e.g., 2.0, 4.0):", default="2.0").ask())
    except (ValueError, TypeError):
        print("Invalid scale factor. Using default 2.0.")
        options['scale_factor'] = 2.0

    try:
        processor = pyanime4k.Processor(processor_name=options['processor_name'], device_id=options['device_id'], model_name=options['model_name'])
        print("\n✅ Processor initialized successfully!")
    except Exception as e:
        print(f"\n❌ Fatal error during processor initialization: {e}")
        return

    existing_files_basenames = {get_base_name(f) for f in os.listdir(UPSCALED_DIR)}
    files_to_process = [f for f in os.listdir(TO_UPSCALE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not files_to_process:
        print("\nNo images found in 'to_upscale' directory.")
        return

    print(f"\nFound {len(files_to_process)} images to process...")
    processed_count = 0
    skipped_count = 0

    for filename in files_to_process:
        base_name = get_base_name(filename)
        if base_name in existing_files_basenames:
            print(f"⏭️ Skipping '{filename}' (already exists in output).")
            skipped_count += 1
            continue

        input_path = os.path.join(TO_UPSCALE_DIR, filename)
        output_path = os.path.join(UPSCALED_DIR, filename)
        image_bgr = cv2.imread(input_path)

        if image_bgr is not None:
            print(f"⏳ Processing: '{filename}' with scale factor {options['scale_factor']}x...")
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            result_rgb = processor(image_rgb, factor=options['scale_factor'])
            result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite(output_path, result_bgr)
            processed_count += 1
        else:
            print(f"⚠️ Warning: Could not read file: {filename}")
    
    print("\n--- Processing Complete ---")
    print(f"✅ Successfully processed: {processed_count} images.")
    print(f"⏭️ Skipped: {skipped_count} images (duplicates).")

# START: MODIFIED SECTION - تم تعديل هذه الدالة بالكامل
def upscale_videos():
    """واجهة رفع جودة الفيديوهات."""
    print("\n--- Upscaling Videos with Anime4K ---")
    options = get_anime4k_options()

    # إضافة سؤال عن معامل التكبير هنا
    try:
        options['scale_factor'] = float(questionary.text("Enter scale factor for video (e.g., 2.0):", default="2.0").ask())
    except (ValueError, TypeError):
        print("Invalid scale factor. Using default 2.0.")
        options['scale_factor'] = 2.0
    
    try:
        processor = pyanime4k.Processor(processor_name=options['processor_name'], device_id=options['device_id'], model_name=options['model_name'])
        print("\n✅ Processor initialized successfully!")
    except Exception as e:
        print(f"\n❌ Fatal error during processor initialization: {e}")
        return

    existing_files_basenames = {get_base_name(f) for f in os.listdir(UPSCALED_DIR)}
    videos_to_process = [f for f in os.listdir(TO_UPSCALE_DIR) if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
    
    if not videos_to_process:
        print("\nNo videos found in 'to_upscale' directory.")
        return

    print(f"\nFound {len(videos_to_process)} videos to process...")
    processed_count = 0
    skipped_count = 0

    for video_name in videos_to_process:
        base_name = get_base_name(video_name)
        if base_name in existing_files_basenames:
            print(f"⏭️ Skipping '{video_name}' (already exists in output).")
            skipped_count += 1
            continue
        
        print(f"\n--- Processing Video: {video_name} ---")
        video_path = os.path.join(TO_UPSCALE_DIR, video_name)
        temp_folder_name = f"temp_{os.path.splitext(video_name)[0]}"
        frames_input_dir = os.path.join(BASE_UPSCALE_DIR, temp_folder_name, "input_frames")
        frames_output_dir = os.path.join(BASE_UPSCALE_DIR, temp_folder_name, "output_frames")
        os.makedirs(frames_input_dir, exist_ok=True)
        os.makedirs(frames_output_dir, exist_ok=True)

        print("Step 1: Extracting frames...")
        extract_command = ['ffmpeg', '-i', video_path, os.path.join(frames_input_dir, 'frame_%06d.png')]
        if run_command(extract_command) != 0:
            print(f"❌ Failed to extract frames for {video_name}. Skipping.")
            continue
            
        print(f"Step 2: Upscaling frames with factor {options['scale_factor']}x...")
        frame_files = sorted(os.listdir(frames_input_dir))
        total_frames = len(frame_files)
        for i, frame_file in enumerate(frame_files, 1):
            print(f"  Upscaling frame {i}/{total_frames}", end='\r')
            img_bgr = cv2.imread(os.path.join(frames_input_dir, frame_file))
            if img_bgr is not None:
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                # تطبيق معامل التكبير المحدد هنا
                res_rgb = processor(img_rgb, factor=options['scale_factor'])
                res_bgr = cv2.cvtColor(res_rgb, cv2.COLOR_RGB2BGR)
                cv2.imwrite(os.path.join(frames_output_dir, frame_file), res_bgr)
        print("\n  Frame upscaling complete.")
            
        print("Step 3: Assembling video with audio...")
        final_video_path = os.path.join(UPSCALED_DIR, video_name)
        assemble_command = [
            'ffmpeg', '-y', '-i', video_path, '-framerate', '30',
            '-i', os.path.join(frames_output_dir, 'frame_%06d.png'),
            '-map', '1:v:0', '-map', '0:a:0?',
            '-vf', "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
            '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-c:a', 'copy', '-shortest', final_video_path
        ]
        
        if run_command(assemble_command) == 0:
            processed_count += 1
        else:
            print(f"❌ Failed to assemble video for {video_name}. Skipping.")

        print("Step 4: Cleaning up temporary files...")
        shutil.rmtree(os.path.join(BASE_UPSCALE_DIR, temp_folder_name))

    print("\n--- Processing Complete ---")
    print(f"✅ Successfully processed: {processed_count} videos.")
    print(f"⏭️ Skipped: {skipped_count} videos (duplicates).")
# END: MODIFIED SECTION

def sync_names():
    """يقارن الأسماء بين المجلد المصدر والمجلد المُحسَّن ويقترح إعادة التسمية."""
    print("\n--- Syncing Names ---")
    print(f"Source Directory: {SOURCE_SYNC_DIR}")
    print(f"Target Directory: {UPSCALED_DIR}")

    source_files = []
    for root, _, files in os.walk(SOURCE_SYNC_DIR):
        for f in files:
            source_files.append(f)
    
    source_map = {get_base_name(f): f for f in source_files}
    upscaled_files = [f for f in os.listdir(UPSCALED_DIR)]
    upscaled_map = {get_base_name(f): f for f in upscaled_files}

    rename_candidates = []
    for base_name, old_full_name in upscaled_map.items():
        if base_name in source_map:
            new_full_name = source_map[base_name]
            if old_full_name != new_full_name:
                rename_candidates.append((old_full_name, new_full_name))

    if not rename_candidates:
        print("\n✅ All names are already in sync. Nothing to do.")
        return

    print("\nFound the following files to rename:")
    for old, new in rename_candidates:
        print(f"  '{old}'  ->  '{new}'")
        
    if questionary.confirm("\nProceed with renaming these files?").ask():
        renamed_count = 0
        for old, new in rename_candidates:
            old_path = os.path.join(UPSCALED_DIR, old)
            new_path = os.path.join(UPSCALED_DIR, new)
            try:
                os.rename(old_path, new_path)
                print(f"✅ Renamed '{old}' to '{new}'")
                renamed_count += 1
            except Exception as e:
                print(f"❌ Error renaming '{old}': {e}")
        print(f"\n--- Sync Complete. Renamed {renamed_count} files. ---")
    else:
        print("\nSync operation cancelled by user.")

# --- 4. الدالة الرئيسية ---

def main():
    """الدالة الرئيسية لتشغيل البرنامج."""
    if not PYANIME4K_AVAILABLE:
        print("❌ Critical Error: 'pyanime4k' or 'opencv-python' is not installed.")
        print("Please install them by running: pip install pyanime4k opencv-python")
        return

    os.makedirs(TO_UPSCALE_DIR, exist_ok=True)
    
    print("--- Upscaler & Sync Manager ---")
    while True:
        choice = questionary.select(
            "\nWhat would you like to do?",
            choices=[
                "1. Upscale Images", "2. Upscale Videos",
                "3. Sync Names", "Exit"
            ]
        ).ask()

        if choice == "1. Upscale Images":
            upscale_images()
        elif choice == "2. Upscale Videos":
            upscale_videos()
        elif choice == "3. Sync Names":
            sync_names()
        elif choice == "Exit" or choice is None:
            print("Exiting. Goodbye!")
            break
        
        questionary.press_any_key_to_continue().ask()

if __name__ == "__main__":
    main()

# END: FULL SCRIPT