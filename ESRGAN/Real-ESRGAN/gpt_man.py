# START: FULL SCRIPT
import os
import sys
import subprocess
import json
import shutil
import questionary
import time

try:
    import pyanime4k
    import cv2
    PYANIME4K_AVAILABLE = True
except ImportError:
    PYANIME4K_AVAILABLE = False


# --- الإعدادات والمسارات الأساسية ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INFERENCE_SCRIPT = os.path.join(BASE_DIR, "inference_realesrgan.py")

# # START: MODIFIED SECTION
# --- إضافة مسار المحرك الجديد ---
VULKAN_EXECUTABLE = "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\ESRGAN\\Real-ESRGAN\\realesrgan-ncnn-vulkan.exe"
# # END: MODIFIED SECTION

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

# # START: MODIFIED SECTION
# --- دالة مساعدة جديدة لاختيار وبناء أمر تجميع الفيديو (تم تحديثها قليلاً) ---
def get_video_assembly_command(original_video_path, upscaled_frames_path_pattern, output_video_path):
    """
    تسأل المستخدم عن طريقة التجميع وتبني أمر ffmpeg المناسب.
    """
    assembly_choice = questionary.select(
        "Select video assembly method:",
        choices=[
            "Method 1: Professional (High Quality, Auto Framerate)",
            "Method 2: Manual (You specify the framerate)",
            "Cancel Assembly"
        ],
        default="Method 1: Professional (High Quality, Auto Framerate)"
    ).ask()

    if assembly_choice == "Method 1: Professional (High Quality, Auto Framerate)":
        print("Building command with Professional settings...")
        return [
            'ffmpeg', '-y', '-i', original_video_path, '-framerate', '30',
            '-i', upscaled_frames_path_pattern,
            '-map', '1:v:0', '-map', '0:a:0?',
            '-vf', "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
            '-c:v', 'libx264', '-crf', '18', '-preset', 'medium',
            '-c:a', 'copy', '-shortest', output_video_path
        ]
    elif assembly_choice == "Method 2: Manual (You specify the framerate)":
        print("Building command with Manual settings...")
        framerate = questionary.text("Enter desired framerate (e.g., 23.98, 30, 60):", default="23.98").ask()
        # بناء الأمر مع تبديل المدخلات ليتوافق مع -map 0:v و -map 1:a
        return [
            'ffmpeg', '-y', '-framerate', framerate,
            '-i', upscaled_frames_path_pattern,
            '-i', original_video_path,
            '-map', '0:v:0', '-map', '1:a:0?',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            '-c:a', 'copy', '-shortest', output_video_path
        ]
    else:
        return None
# # END: MODIFIED SECTION

# --- دوال Real-ESRGAN (الخاصة بـ PyTorch - لم يتم لمسها) ---

def get_upscale_options():
    """للحصول على خيارات رفع الجودة من المستخدم (PyTorch)."""
    model_choices = [
        'RealESRGAN_x2plus', 'RealESRGAN_x4plus', 'realesr-general-x4v3',
        'RealESRGAN_x4plus_anime_6B', 'realesr-animevideov3'
    ]
    options = {}
    options['model_name'] = questionary.select("Select the PyTorch model to use:", choices=model_choices, default='RealESRGAN_x2plus').ask()
    options['tile'] = questionary.text("Enter tile size (enter 0 to disable, default 128):", default="128").ask()
    options['outscale'] = questionary.text("Enter outscale factor (default 1.2):", default="1.2").ask()
    options['suffix'] = questionary.text("Enter suffix for images (default 'out'):", default="out").ask()
    return options

def upscale_images_ui():
    """واجهة رفع جودة الصور (PyTorch)."""
    print("\n--- Upscaling Images with Real-ESRGAN (PyTorch) ---")
    options = get_upscale_options()
    command = [
        sys.executable, INFERENCE_SCRIPT, '-n', options['model_name'],
        '-i', INPUT_DIR, '-o', OUTPUT_DIR, '--outscale', options['outscale'], '--fp32'
    ]
    tile_value = options['tile'].strip()
    if tile_value and tile_value != '0':
        command.extend(['--tile', tile_value])
    if options['suffix'].strip():
        command.extend(['--suffix', options['suffix'].strip()])
    run_command(command)

def upscale_videos_ui():
    """واجهة رفع جودة الفيديوهات (PyTorch)."""
    print("\n--- Upscaling Videos with Real-ESRGAN (PyTorch) ---")
    video_extensions = ('.mp4', '.mkv', '.mov', '.avi', '.webm')
    videos = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(video_extensions)]

    if not videos:
        print("No videos found in the input directory.")
        return

    print(f"Found {len(videos)} video(s) to process.")
    options = get_upscale_options()
    tile_value = options['tile'].strip()
    suffix = options['suffix'].strip() if options['suffix'].strip() else 'out'

    for video_name in videos:
        print(f"\n--- Processing Video: {video_name} ---")
        video_path = os.path.join(INPUT_DIR, video_name)
        temp_folder_name = f"temp_{os.path.splitext(video_name)[0]}"
        frames_input_dir = os.path.join(BASE_DIR, temp_folder_name, "input_frames")
        frames_output_dir = os.path.join(BASE_DIR, temp_folder_name, "output_frames")
        os.makedirs(frames_input_dir, exist_ok=True)
        os.makedirs(frames_output_dir, exist_ok=True)

        print("Step 1: Extracting frames...")
        extract_command = ['ffmpeg', '-i', video_path, '-qscale:v', '1', '-qmin', '1', '-qmax', '1', os.path.join(frames_input_dir, 'frame_%06d.png')]
        if run_command(extract_command) != 0:
            print(f"Failed to extract frames for {video_name}. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
            
        print("Step 2: Upscaling frames...")
        upscale_command = [
            sys.executable, INFERENCE_SCRIPT, '-n', options['model_name'], '-i', frames_input_dir,
            '-o', frames_output_dir, '--outscale', options['outscale'], '--fp32', '--suffix', suffix
        ]
        if tile_value and tile_value != '0':
            upscale_command.extend(['--tile', tile_value])
        
        if run_command(upscale_command) != 0:
            print(f"Failed to upscale frames for {video_name}. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
            
        print("Step 3: Assembling video with audio...")
        final_video_name = video_name
        final_video_path = os.path.join(OUTPUT_DIR, final_video_name)
        
        assemble_command = get_video_assembly_command(
            original_video_path=video_path,
            upscaled_frames_path_pattern=os.path.join(frames_output_dir, f'frame_%06d_{suffix}.png'),
            output_video_path=final_video_path
        )
        
        if not assemble_command:
            print("Video assembly cancelled by user. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
        
        if run_command(assemble_command) != 0:
            print(f"Failed to assemble video for {video_name}. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
        
        print("Step 4: Cleaning up temporary files...")
        try:
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            print("Cleanup successful.")
        except Exception as e:
            print(f"Warning: Could not clean up all temporary files. {e}")

# # START: MODIFIED SECTION
# --- دوال جديدة خاصة بـ Real-ESRGAN (محرك Vulkan) ---

def get_vulkan_options():
    """للحصول على خيارات رفع الجودة من المستخدم (Vulkan)."""
    model_choices = ['realesr-animevideov3', 'realesrgan-x4plus', 'realesrgan-x4plus-anime']
    options = {}
    options['model_name'] = questionary.select("Select the Vulkan model to use:", choices=model_choices, default='realesr-animevideov3').ask()
    options['scale'] = questionary.text("Enter scale factor (-s) (e.g., 2, 4):", default="2").ask()
    options['format'] = questionary.select("Select output format (-f):", choices=['png', 'jpg', 'webp'], default='png').ask()
    return options

def upscale_images_vulkan_ui():
    """واجهة رفع جودة الصور (Vulkan)."""
    print("\n--- Upscaling Images with Real-ESRGAN (NCNN Vulkan) ---")
    options = get_vulkan_options()
    command = [
        VULKAN_EXECUTABLE, '-i', INPUT_DIR, '-o', OUTPUT_DIR,
        '-n', options['model_name'], '-s', options['scale'], '-f', options['format']
    ]
    run_command(command)

def upscale_videos_vulkan_ui():
    """واجهة رفع جودة الفيديوهات (Vulkan)."""
    print("\n--- Upscaling Videos with Real-ESRGAN (NCNN Vulkan) ---")
    video_extensions = ('.mp4', '.mkv', '.mov', '.avi', '.webm')
    videos = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(video_extensions)]

    if not videos:
        print("No videos found in the input directory.")
        return

    print(f"Found {len(videos)} video(s) to process.")
    options = get_vulkan_options()
    
    for video_name in videos:
        print(f"\n--- Processing Video: {video_name} ---")
        video_path = os.path.join(INPUT_DIR, video_name)
        temp_folder_name = f"temp_{os.path.splitext(video_name)[0]}"
        frames_input_dir = os.path.join(BASE_DIR, temp_folder_name, "input_frames")
        frames_output_dir = os.path.join(BASE_DIR, temp_folder_name, "output_frames")
        os.makedirs(frames_input_dir, exist_ok=True)
        os.makedirs(frames_output_dir, exist_ok=True)

        print("Step 1: Extracting frames...")
        # استخراج الإطارات بصيغة jpg كما هو موصى به في كتيب Vulkan
        extract_command = ['ffmpeg', '-i', video_path, '-qscale:v', '1', '-qmin', '1', '-qmax', '1', os.path.join(frames_input_dir, 'frame_%08d.jpg')]
        if run_command(extract_command) != 0:
            print(f"Failed to extract frames for {video_name}. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
            
        print("Step 2: Upscaling frames...")
        # بناء أمر Vulkan. لاحظ أنه لا يحتاج لـ --suffix
        upscale_command = [
            VULKAN_EXECUTABLE, '-i', frames_input_dir, '-o', frames_output_dir,
            '-n', options['model_name'], '-s', options['scale'], '-f', options['format']
        ]
        
        if run_command(upscale_command) != 0:
            print(f"Failed to upscale frames for {video_name}. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
            
        print("Step 3: Assembling video with audio...")
        final_video_name = video_name
        final_video_path = os.path.join(OUTPUT_DIR, final_video_name)
        
        # تحديد نمط الإطارات الناتجة بناءً على الصيغة المختارة
        upscaled_frames_path_pattern = os.path.join(frames_output_dir, f'frame_%08d.{options["format"]}')

        assemble_command = get_video_assembly_command(
            original_video_path=video_path,
            upscaled_frames_path_pattern=upscaled_frames_path_pattern,
            output_video_path=final_video_path
        )
        
        if not assemble_command:
            print("Video assembly cancelled by user. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue

        if run_command(assemble_command) != 0:
            print(f"Failed to assemble video for {video_name}. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
        
        print("Step 4: Cleaning up temporary files...")
        try:
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            print("Cleanup successful.")
        except Exception as e:
            print(f"Warning: Could not clean up all temporary files. {e}")

# # END: MODIFIED SECTION

# --- دوال Anime4K (بدون تغيير) ---
def get_anime4k_options():
    """للحصول على خيارات Anime4K من المستخدم."""
    model_choices = ['acnet-gan', 'acnet-hdn0', 'acnet-hdn1', 'acnet-hdn2', 'acnet-hdn3', 'arnet-hdn']
    options = {}
    options['model_name'] = questionary.select("Select the Anime4K model to use:", choices=model_choices, default='acnet-gan').ask()
    options['processor_name'] = questionary.select("Select the processor to use:", choices=['cuda', 'opencl', 'cpu'], default='cuda').ask()
    options['device_id'] = int(questionary.text("Enter device ID (default 0):", default="0").ask())
    return options

def upscale_images_anime4k_ui():
    """واجهة رفع جودة الصور باستخدام Anime4K."""
    print("\n--- Upscaling Images with Anime4K ---")
    options = get_anime4k_options()
    
    try:
        options['scale_factor'] = float(questionary.text("Enter scale factor (e.g., 2.0, 3.5):", default="2.0").ask())
    except (ValueError, TypeError):
        print("Invalid scale factor. Using default 2.0.")
        options['scale_factor'] = 2.0

    try:
        processor = pyanime4k.Processor(processor_name=options['processor_name'], device_id=options['device_id'], model_name=options['model_name'])
        print("... Processor initialized successfully! ...")
    except Exception as e:
        print(f"!!! Fatal error during processor initialization: {e}")
        return

    print("\n... Starting image processing ...")
    start_time = time.time()
    files_to_process = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))]
    total_files = len(files_to_process)
    if total_files == 0:
        print("No images found in the input directory.")
        return

    for i, filename in enumerate(files_to_process, 1):
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        image_bgr = cv2.imread(input_path)
        if image_bgr is not None:
            print(f"[{i}/{total_files}] Processing: {filename} with scale factor {options['scale_factor']}x")
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            result_rgb = processor(image_rgb, factor=options['scale_factor'])
            result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite(output_path, result_bgr)
        else:
            print(f"Warning: Could not read file (it may not be an image): {filename}")

    end_time = time.time()
    print("\n... All images processed successfully! ...")
    print(f"Total images processed: {total_files}")
    print(f"Time taken: {end_time - start_time:.2f} seconds")

def upscale_videos_anime4k_ui():
    """واجهة رفع جودة الفيديو باستخدام Anime4K."""
    print("\n--- Upscaling Videos with Anime4K ---")
    video_extensions = ('.mp4', '.mkv', '.mov', '.avi', '.webm')
    videos = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(video_extensions)]

    if not videos:
        print("No videos found in the input directory.")
        return

    print(f"Found {len(videos)} video(s) to process.")
    options = get_anime4k_options()

    try:
        options['scale_factor'] = float(questionary.text("Enter scale factor (e.g., 2.0, 4.0):", default="2.0").ask())
    except (ValueError, TypeError):
        print("Invalid scale factor. Using default 2.0.")
        options['scale_factor'] = 2.0

    try:
        processor = pyanime4k.Processor(processor_name=options['processor_name'], device_id=options['device_id'], model_name=options['model_name'])
        print("... Processor initialized successfully! ...")
    except Exception as e:
        print(f"!!! Fatal error during processor initialization: {e}")
        return

    for video_name in videos:
        print(f"\n--- Processing Video: {video_name} (at {options['scale_factor']}x scale) ---")
        video_path = os.path.join(INPUT_DIR, video_name)
        temp_folder_name = f"temp_{os.path.splitext(video_name)[0]}"
        frames_input_dir = os.path.join(BASE_DIR, temp_folder_name, "input_frames")
        frames_output_dir = os.path.join(BASE_DIR, temp_folder_name, "output_frames")
        os.makedirs(frames_input_dir, exist_ok=True)
        os.makedirs(frames_output_dir, exist_ok=True)

        print("Step 1: Extracting frames...")
        extract_command = ['ffmpeg', '-i', video_path, '-qscale:v', '1', '-qmin', '1', '-qmax', '1', os.path.join(frames_input_dir, 'frame_%06d.png')]
        if run_command(extract_command) != 0:
            print(f"Failed to extract frames for {video_name}. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
            
        print("Step 2: Upscaling frames with Anime4K...")
        frame_files = sorted(os.listdir(frames_input_dir))
        total_frames = len(frame_files)
        for i, frame_file in enumerate(frame_files, 1):
            print(f"  Upscaling frame {i}/{total_frames}", end='\r')
            input_frame_path = os.path.join(frames_input_dir, frame_file)
            output_frame_path = os.path.join(frames_output_dir, frame_file)
            image_bgr = cv2.imread(input_frame_path)
            if image_bgr is None: continue
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            result_rgb = processor(image_rgb, factor=options['scale_factor'])
            result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite(output_frame_path, result_bgr)
        print("\n  Frame upscaling complete.")
            
        print("Step 3: Assembling video with audio...")
        final_video_name = video_name
        final_video_path = os.path.join(OUTPUT_DIR, final_video_name)
        
        assemble_command = get_video_assembly_command(
            original_video_path=video_path,
            upscaled_frames_path_pattern=os.path.join(frames_output_dir, 'frame_%06d.png'),
            output_video_path=final_video_path
        )
        
        if not assemble_command:
            print("Video assembly cancelled by user. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
        
        if run_command(assemble_command) != 0:
            print(f"Failed to assemble video for {video_name}. Skipping.")
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            continue
        
        print("Step 4: Cleaning up temporary files...")
        try:
            shutil.rmtree(os.path.join(BASE_DIR, temp_folder_name))
            print("Cleanup successful.")
        except Exception as e:
            print(f"Warning: Could not clean up all temporary files. {e}")

def anime4k_ui():
    """القائمة الرئيسية الخاصة بـ Anime4K."""
    if not PYANIME4K_AVAILABLE:
        print("\n❌ Error: 'pyanime4k' or 'opencv-python' is not installed.")
        print("Please install them by running: pip install pyanime4k opencv-python")
        return

    choice = questionary.select("Select an action for Anime4K:", choices=["Upscale Images", "Upscale Videos", "Back to main menu"]).ask()

    if choice == "Upscale Images":
        upscale_images_anime4k_ui()
    elif choice == "Upscale Videos":
        upscale_videos_anime4k_ui()
    elif choice == "Back to main menu" or choice is None:
        return

# --- دوال المعالجة اللاحقة (بدون تغيير) ---
def post_process_copy_metadata_ui():
    print("\n--- Copying metadata from original images ---")
    
    exiftool_path = shutil.which("exiftool")
    if not exiftool_path:
        print("❌ Error: 'exiftool.exe' is not installed or not in your system's PATH.")
        return

    # --- تعديل ذكي: البحث عن ملف التكوين بجانب ملف exiftool.exe نفسه ---
    exiftool_dir = os.path.dirname(exiftool_path)
    config_file_path = os.path.join(exiftool_dir, 'ComfyUI.config')
    
    if not os.path.exists(config_file_path):
        print(f"❌ Error: Config file 'ComfyUI.config' not found in the same directory as exiftool.exe.")
        print(f"   (Searched in: {exiftool_dir})")
        print("   Please create the config file and place it next to exiftool.exe.")
        return

    try:
        output_files = [f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    except FileNotFoundError:
        print(f"❌ Error: Output directory not found at {OUTPUT_DIR}")
        return

    if not output_files:
        print("No image files found in the output directory to process.")
        return

    if questionary.confirm(f"Found {len(output_files)} files. Proceed with copying ComfyUI metadata?").ask():
        success_count = 0
        fail_count = 0
        
        for filename in output_files:
            source_path = os.path.join(INPUT_DIR, filename)
            target_path = os.path.join(OUTPUT_DIR, filename)

            if os.path.exists(source_path):
                command = [
                    'exiftool',
                    '-config', config_file_path,
                    '-TagsFromFile', source_path,
                    '-workflow', '-prompt',
                    '-overwrite_original',
                    target_path
                ]
                
                print(f"\nProcessing: {filename}")
                # استخدمنا دالة run_command الموجودة بالفعل
                if run_command(command) == 0:
                    success_count += 1
                else:
                    fail_count += 1
            else:
                print(f"⚠️ Warning: Source file not found for '{filename}'. Skipping.")
        
        print(f"\n✅ Metadata copying complete.")
        print(f"Successfully updated: {success_count} files.")
        if fail_count > 0:
            print(f"Failed to update: {fail_count} files.")


def post_process_rename_files_ui(media_type):
    print(f"\n--- Renaming {media_type} files (removing suffixes) ---")
    suffixes_to_remove = ['_out'] 
    files_to_rename = [f for f in os.listdir(OUTPUT_DIR) if any(os.path.splitext(f)[0].endswith(s) for s in suffixes_to_remove)]
    if not files_to_rename:
        print("No files with known suffixes found to rename.")
        return
    print("The following files will be renamed:")
    for f in files_to_rename: print(f)
    if questionary.confirm("Proceed with renaming?").ask():
        for filename in files_to_rename:
            name, ext = os.path.splitext(filename)
            new_name = name
            for s in suffixes_to_remove:
                if new_name.endswith(s):
                    new_name = new_name[:-len(s)]
            new_filename = new_name + ext
            try:
                os.rename(os.path.join(OUTPUT_DIR, filename), os.path.join(OUTPUT_DIR, new_filename))
            except Exception as e:
                print(f"Error renaming {filename}: {e}")
        print(f"\n✅ Renaming complete.")

def post_process_update_db_ui(media_type):
    print(f"\n--- Updating file sizes in JSON databases for {media_type} ---")
    output_files = {f: os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in os.listdir(OUTPUT_DIR)}
    found_matches = {}
    for db_path in DB_FILES:
        try:
            with open(db_path, 'r', encoding='utf-8') as f: data = json.load(f)
            for key in data:
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
        for src, dest in files_to_move:
            try:
                shutil.move(src, dest)
            except Exception as e:
                print(f"Error moving {os.path.basename(src)}: {e}")
        print(f"\n✅ Moving and replacing complete.")

def post_process_ui(media_type):
    """القائمة الرئيسية للمعالجة اللاحقة."""
    while True:
        choices = ["Rename files (remove suffixes)", "Update file sizes in database", "Move files to original location (replace)"]
        if media_type == "Images":
            choices.insert(1, "Copy metadata from originals")
        choices.append("Back to main menu")
        choice = questionary.select(f"Select a post-processing action for {media_type}:", choices=choices).ask()
        
        if choice == "Rename files (remove suffixes)":
            post_process_rename_files_ui(media_type)
        elif choice == "Copy metadata from originals":
            post_process_copy_metadata_ui()
        elif choice == "Update file sizes in database":
            post_process_update_db_ui(media_type)
        elif choice == "Move files to original location (replace)":
            post_process_move_files_ui(media_type)
        elif choice == "Back to main menu" or choice is None:
            break
        questionary.press_any_key_to_continue().ask()

def main():
    """الدالة الرئيسية للبرنامج."""
    print("--- Workflow Manager ---")
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    while True:
        # # START: MODIFIED SECTION
        # --- تعديل القائمة الرئيسية لتشمل المحرك الجديد ---
        main_choice = questionary.select(
            "What would you like to do?",
            choices=[
                "1. Upscale with Real-ESRGAN (PyTorch)", 
                "2. Upscale with Real-ESRGAN (NCNN Vulkan)",
                "3. Upscale with Anime4K", 
                "4. Post-process Upscaled Images",
                "5. Post-process Upscaled Videos", 
                "Exit"
            ]
        ).ask()

        if main_choice == "1. Upscale with Real-ESRGAN (PyTorch)":
            media_type_choice = questionary.select("Select media type:", choices=["Images", "Videos"]).ask()
            if media_type_choice == "Images":
                upscale_images_ui()
            elif media_type_choice == "Videos":
                upscale_videos_ui()
        
        elif main_choice == "2. Upscale with Real-ESRGAN (NCNN Vulkan)":
            media_type_choice = questionary.select("Select media type:", choices=["Images", "Videos"]).ask()
            if media_type_choice == "Images":
                upscale_images_vulkan_ui()
            elif media_type_choice == "Videos":
                upscale_videos_vulkan_ui()
        # # END: MODIFIED SECTION

        elif main_choice == "3. Upscale with Anime4K":
            anime4k_ui()
        elif main_choice == "4. Post-process Upscaled Images":
            post_process_ui("Images")
        elif main_choice == "5. Post-process Upscaled Videos":
            post_process_ui("Videos")
        elif main_choice == "Exit" or main_choice is None:
            print("Exiting. Goodbye!")
            break
        questionary.press_any_key_to_continue().ask()

if __name__ == "__main__":
    print("Checking for required tools...")
    if shutil.which("ffmpeg") is None:
        print("⚠️ WARNING: 'ffmpeg' is not found. Video processing will not be available.")
    if shutil.which("exiftool") is None:
        print("⚠️ WARNING: 'exiftool' is not found. Metadata copying will not be available.")
    if not PYANIME4K_AVAILABLE:
        print("⚠️ WARNING: 'pyanime4k' or 'opencv-python' not found. Anime4K features will be disabled.")
    # # START: MODIFIED SECTION
    if not os.path.exists(VULKAN_EXECUTABLE):
        print(f"⚠️ WARNING: Real-ESRGAN Vulkan executable not found at '{VULKAN_EXECUTABLE}'. This option will be disabled.")
    # # END: MODIFIED SECTION
    print("-" * 20)
    main()
# END: FULL SCRIPT