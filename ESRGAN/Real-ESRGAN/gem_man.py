# START: FULL SCRIPT
import os
import sys
import subprocess
import json
import shutil
import questionary

# --- الإعدادات والمسارات الأساسية ---
# تأكد من أن هذه المسارات صحيحة
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INFERENCE_SCRIPT = os.path.join(BASE_DIR, "inference_realesrgan.py")

DB_FILES = [
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\utilities\\elo_videos_A1000 elo tik.json",
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\utilities\\elo_videos_A1000 elo pic.json",
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\utilities\\elo_videos_Dib.json"
]

SOURCE_MEDIA_FOLDERS = [
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\NS\\TikTok\\ELO TIK\\A1000 elo pic",
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\NS\\TikTok\\ELO TIK\\A1000 elo tik",
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\NS\\TikTok\\ELO TIK\\Dib"
]

# --- دوال مساعدة ---

def run_command(command):
    """لتشغيل الأوامر في الطرفية وعرض المخرجات مباشرة."""
    print("\n" + "="*20)
    print(f"🚀 Executing Command:\n{' '.join(command)}")
    print("="*20 + "\n")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=BASE_DIR
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
    except FileNotFoundError:
        print(f"❌ Error: Command '{command[0]}' not found. Make sure it's installed and in your PATH.")
        return -1
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return -1

def get_upscale_options():
    """للحصول على خيارات رفع الجودة من المستخدم."""
    model_choices = [
        'RealESRGAN_x2plus',
        'RealESRGAN_x4plus',
        'realesr-general-x4v3',
        'RealESRGAN_x4plus_anime_6B',
        'realesr-animevideov3'
    ]
    
    options = {}
    options['model_name'] = questionary.select(
        "Select the model to use:",
        choices=model_choices,
        default='RealESRGAN_x2plus'
    ).ask()
    
    options['tile'] = questionary.text("Enter tile size (enter 0 to disable, default 128):", default="128").ask()
    options['outscale'] = questionary.text("Enter outscale factor (default 1.2):", default="1.2").ask()
    options['suffix'] = questionary.text("Enter suffix (leave blank for none):", default="").ask()

    return options

def upscale_images_ui():
    """واجهة رفع جودة الصور."""
    print("\n--- Upscaling Images ---")
    options = get_upscale_options()
    
    command = [
        sys.executable, INFERENCE_SCRIPT,
        '-n', options['model_name'],
        '-i', INPUT_DIR,
        '-o', OUTPUT_DIR,
        '--outscale', options['outscale'],
        '--fp32'
    ]
    
    tile_value = options['tile'].strip()
    if tile_value and tile_value != '0':
        command.extend(['--tile', tile_value])
    
    if options['suffix'].strip():
        command.extend(['--suffix', options['suffix'].strip()])
        
    run_command(command)

def upscale_videos_ui():
    """واجهة رفع جودة الفيديوهات."""
    print("\n--- Upscaling Videos ---")
    video_extensions = ('.mp4', '.mkv', '.mov', '.avi', '.webm')
    videos = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(video_extensions)]

    if not videos:
        print("No videos found in the input directory.")
        return

    print(f"Found {len(videos)} video(s) to process.")
    options = get_upscale_options()
    tile_value = options['tile'].strip()

    for video_name in videos:
        print(f"\n--- Processing Video: {video_name} ---")
        video_path = os.path.join(INPUT_DIR, video_name)
        video_size_str = str(os.path.getsize(video_path))
        
        frames_input_dir = os.path.join(INPUT_DIR, video_size_str)
        frames_output_dir = os.path.join(OUTPUT_DIR, video_size_str)
        os.makedirs(frames_input_dir, exist_ok=True)
        os.makedirs(frames_output_dir, exist_ok=True)

        print("Step 1: Extracting frames...")
        extract_command = [ 'ffmpeg', '-i', video_path, os.path.join(frames_input_dir, 'frame_%05d.png') ]
        if run_command(extract_command) != 0:
            print(f"Failed to extract frames for {video_name}. Skipping.")
            continue
            
        print("Step 2: Upscaling frames...")
        upscale_command = [
            sys.executable, INFERENCE_SCRIPT,
            '-n', options['model_name'],
            '-i', frames_input_dir,
            '-o', frames_output_dir,
            '--outscale', options['outscale'],
            '--fp32'
        ]
        if tile_value and tile_value != '0':
            upscale_command.extend(['--tile', tile_value])
        
        suffix = options['suffix'].strip() if options['suffix'].strip() else 'out'
        upscale_command.extend(['--suffix', suffix])
        
        if run_command(upscale_command) != 0:
            print(f"Failed to upscale frames for {video_name}. Skipping.")
            continue
            
        print("Step 3: Assembling video (no audio)...")
        video_base_name = os.path.splitext(video_name)[0]
        temp_video_name = f"{video_base_name}_without_voice.mp4"
        temp_video_path = os.path.join(OUTPUT_DIR, temp_video_name)
        
        assemble_command = [ 'ffmpeg', '-framerate', '24', '-i', os.path.join(frames_output_dir, f'frame_%05d_{suffix}.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', temp_video_path ]
        if run_command(assemble_command) != 0:
            print(f"Failed to assemble video for {video_name}. Skipping.")
            continue
            
        print("Step 4: Adding audio...")
        final_video_name = f"{video_base_name}_upscaled.mp4"
        final_video_path = os.path.join(OUTPUT_DIR, final_video_name)
        
        audio_command = [ 'ffmpeg', '-i', temp_video_path, '-i', video_path, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-y', final_video_path ]
        if run_command(audio_command) != 0:
            print(f"Failed to add audio for {video_name}. Skipping.")
            continue
        
        print("Step 5: Cleaning up temporary files...")
        try:
            shutil.rmtree(frames_input_dir)
            shutil.rmtree(frames_output_dir)
            os.remove(temp_video_path)
            print("Cleanup successful.")
        except Exception as e:
            print(f"Warning: Could not clean up all temporary files. {e}")

# START: MODIFIED SECTION
# تمت إضافة دالة جديدة هنا لنسخ البيانات الوصفية
def post_process_copy_metadata_ui():
    """واجهة نسخ البيانات الوصفية للصور من المجلد الأصلي."""
    print("\n--- Copying metadata from original images ---")
    
    if shutil.which("exiftool") is None:
        print("❌ Error: 'exiftool' is not installed or not in your system's PATH.")
        print("This feature requires ExifTool. Please install it first.")
        return
        
    print("This will copy all metadata from images in the 'inputs' folder")
    print("to the corresponding upscaled images in the 'output' folder.")
    
    if questionary.confirm("Proceed with copying metadata?").ask():
        # الأمر يستخدم متغيرات ExifTool الخاصة (%f, %e) لإيجاد الملفات المطابقة
        # يتم تشغيله من مجلد المخرجات مباشرة ليعمل بشكل صحيح
        command = [
            'exiftool',
            '-tagsFromFile',
            os.path.join(INPUT_DIR, '%f.%e'),
            '-all:all',
            '-overwrite_original',
            '-ext', 'jpg',
            '-ext', 'png',
            '-ext', 'jpeg',
            OUTPUT_DIR
        ]
        run_command(command)
# END: MODIFIED SECTION

def post_process_rename_files_ui(media_type):
    """واجهة إعادة تسمية الملفات."""
    print(f"\n--- Renaming {media_type} files (removing '_out' suffix) ---")
    files_to_rename = [f for f in os.listdir(OUTPUT_DIR) if os.path.splitext(f)[0].endswith('_out')]

    if not files_to_rename:
        print("No files with '_out' suffix found to rename.")
        return

    print("The following files will be renamed:")
    for f in files_to_rename: print(f)

    if questionary.confirm("Proceed with renaming?").ask():
        renamed_count = 0
        for filename in files_to_rename:
            name, ext = os.path.splitext(filename)
            new_name = name[:-4] + ext
            try:
                os.rename(os.path.join(OUTPUT_DIR, filename), os.path.join(OUTPUT_DIR, new_name))
                renamed_count += 1
            except Exception as e:
                print(f"Error renaming {filename}: {e}")
        print(f"\n✅ Renamed {renamed_count} file(s).")

def post_process_update_db_ui(media_type):
    """واجهة تحديث أحجام الملفات في قاعدة البيانات."""
    print(f"\n--- Updating file sizes in JSON databases for {media_type} ---")
    
    output_files = {f: os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in os.listdir(OUTPUT_DIR)}
    
    found_matches = {}
    for db_path in DB_FILES:
        try:
            with open(db_path, 'r', encoding='utf-8') as f: data = json.load(f)
            for key in data.keys():
                if key in output_files and data[key].get('file_size') != output_files[key]:
                    found_matches[key] = {'old': data[key].get('file_size', 'N/A'), 'new': output_files[key]}
        except Exception as e:
            print(f"Warning: Could not process database {db_path}. {e}")

    if not found_matches:
        print("No matching files found in databases that need updating.")
        return

    print("\nFound the following files to update in the databases:")
    for name, sizes in found_matches.items(): print(f"- {name}: Old Size: {sizes['old']}, New Size: {sizes['new']}")

    if questionary.confirm("Are you sure you want to update these file sizes?").ask():
        for db_path in DB_FILES:
            try:
                with open(db_path, 'r', encoding='utf-8') as f: data = json.load(f)
                if any(key in found_matches for key in data):
                    for key, value in data.items():
                        if key in found_matches: value['file_size'] = found_matches[key]['new']
                    with open(db_path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
            except Exception as e:
                print(f"Error updating database {db_path}: {e}")
        print(f"\n✅ Updated records in databases.")


def post_process_move_files_ui(media_type):
    """واجهة نقل الملفات واستبدال القديمة."""
    print(f"\n--- Moving {media_type} and replacing originals ---")
    
    files_to_move = []
    for output_file in os.listdir(OUTPUT_DIR):
        for source_folder in SOURCE_MEDIA_FOLDERS:
            dest_path = os.path.join(source_folder, output_file)
            if os.path.exists(dest_path):
                files_to_move.append((os.path.join(OUTPUT_DIR, output_file), dest_path))
                break 

    if not files_to_move:
        print("No original files found to replace.")
        return
    
    print("\nThe following files will be moved, replacing the originals:")
    for src, dest in files_to_move: print(f"- From: {src}\n  To:   {dest}")
    
    if questionary.confirm("Are you sure you want to replace these files? This cannot be undone.").ask():
        moved_count = 0
        for src, dest in files_to_move:
            try:
                shutil.move(src, dest)
                moved_count += 1
            except Exception as e:
                print(f"Error moving {os.path.basename(src)}: {e}")
        print(f"\n✅ Moved and replaced {moved_count} file(s).")

def post_process_ui(media_type):
    """القائمة الرئيسية للمعالجة اللاحقة."""
    while True:
        # START: MODIFIED SECTION
        # تم تعديل قائمة الخيارات هنا
        choices = [
            "Rename files (remove '_out')",
            "Update file sizes in database",
            "Move files to original location (replace)",
        ]
        if media_type == "Images":
            choices.insert(1, "Copy metadata from originals") # إضافة الخيار الجديد للصور فقط
        
        choices.append("Back to main menu")
        # END: MODIFIED SECTION

        choice = questionary.select(
            f"Select a post-processing action for {media_type}:",
            choices=choices
        ).ask()
        
        if choice == "Rename files (remove '_out')":
            post_process_rename_files_ui(media_type)
        # START: MODIFIED SECTION
        # تم ربط الخيار الجديد بالدالة الجديدة
        elif choice == "Copy metadata from originals":
            post_process_copy_metadata_ui()
        # END: MODIFIED SECTION
        elif choice == "Update file sizes in database":
            post_process_update_db_ui(media_type)
        elif choice == "Move files to original location (replace)":
            post_process_move_files_ui(media_type)
        elif choice == "Back to main menu" or choice is None:
            break
        
        questionary.press_any_key_to_continue().ask()

def main():
    """الدالة الرئيسية للبرنامج."""
    print("--- Real-ESRGAN Workflow Manager ---")
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    while True:
        main_choice = questionary.select(
            "What would you like to do?",
            choices=[
                "1. Upscale Images",
                "2. Upscale Videos",
                "3. Post-process Upscaled Images",
                "4. Post-process Upscaled Videos",
                "Exit"
            ]
        ).ask()

        if main_choice == "1. Upscale Images":
            upscale_images_ui()
        elif main_choice == "2. Upscale Videos":
            upscale_videos_ui()
        elif main_choice == "3. Post-process Upscaled Images":
            post_process_ui("Images")
        elif main_choice == "4. Post-process Upscaled Videos":
            post_process_ui("Videos")
        elif main_choice == "Exit" or main_choice is None:
            print("Exiting. Goodbye!")
            break
            
        questionary.press_any_key_to_continue().ask()


if __name__ == "__main__":
    # START: MODIFIED SECTION
    # تم إضافة فحص لوجود exiftool هنا
    # التحقق من الأدوات المطلوبة
    print("Checking for required tools...")
    if shutil.which("ffmpeg") is None:
        print("⚠️ WARNING: 'ffmpeg' is not found. Video processing will not be available.")
    if shutil.which("exiftool") is None:
        print("⚠️ WARNING: 'exiftool' is not found. Metadata copying will not be available.")
    print("-" * 20)
    # END: MODIFIED SECTION

    main()
# END: FULL SCRIPT