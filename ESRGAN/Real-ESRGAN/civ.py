# START: MODIFIED SECTION
import os
import sys
import time
import subprocess
import shutil
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import re


try:
    import pyanime4k
    import cv2
    PYANIME4K_AVAILABLE = True
except ImportError:
    PYANIME4K_AVAILABLE = False
    print("⚠️ WARNING: pyanime4k or opencv-python is not installed. Fast upscaling feature will be disabled.")
    print("Please install them by running: pip install pyanime4k opencv-python")


# --- 1. Main Settings ---
WATCHED_DIR = r"C:\Users\Stark\Downloads\Civitai_Images"
SHARING_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\ESRGAN\Real-ESRGAN\results"
ESRGAN_BASE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\ESRGAN\Real-ESRGAN"
ESRGAN_INFERENCE_SCRIPT = os.path.join(ESRGAN_BASE_DIR, "inference_realesrgan.py")
ANIME4K_TRACKING_FILE = os.path.join(WATCHED_DIR, "processed_anime4k.txt")
ESRGAN_TRACKING_FILE = os.path.join(WATCHED_DIR, "processed_esrgan.txt")
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')
SCAN_INTERVAL = 10  # فحص المجلد كل 10 ثواني
EXIFTOOL_TIMEOUT = 30  # timeout لعملية exiftool بالثواني


# --- 2. State Variables for Thread Communication ---
stop_flag = threading.Event()
ESRGAN_ENABLED = True  # Default mode is to run both stages
processing_lock = threading.Lock()  # قفل لمنع معالجة نفس الصورة مرتين


# --- 3. Initialize Anime4K Processor ---
if PYANIME4K_AVAILABLE:
    try:
        anime4k_processor = pyanime4k.Processor(processor_name='cuda', device_id=0)
        print("✅ Anime4K processor (CUDA) initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize Anime4K processor: {e}. Disabling fast upscaling feature.")
        PYANIME4K_AVAILABLE = False


# --- 4. Helper Functions and Command Functions ---


def setup_environment():
    os.makedirs(WATCHED_DIR, exist_ok=True)
    os.makedirs(SHARING_DIR, exist_ok=True)
    for tracker in [ANIME4K_TRACKING_FILE, ESRGAN_TRACKING_FILE]:
        if not os.path.exists(tracker): open(tracker, 'w').close()
    print("✅ Working environment set up successfully.")


def extract_base_filename(filename):
    """
    استخراج الاسم الأساسي بدون اللاحقة (بدون آخر suffix)
    مثال: 4ZBSV21CQG0JHX8BP4JN46G9Q0_3fc3a8c1.jpeg → 4ZBSV21CQG0JHX8BP4JN46G9Q0
    """
    # إزالة الامتداد أولاً
    name_without_ext, ext = os.path.splitext(filename)
    
    # البحث عن آخر underscore متبوعة بـ 8 أحرف hex (اللاحقة)
    # Pattern: كلام_XXXXXXXX حيث XXXXXXXX هي 8 أحرف hex
    match = re.search(r'^(.+)_([0-9a-f]{8})$', name_without_ext, re.IGNORECASE)
    
    if match:
        # وجدنا اللاحقة، إرجاع الجزء الأساسي
        return match.group(1)
    
    # لم نجد اللاحقة، إرجاع الاسم كما هو
    return name_without_ext


def get_processed_set(tracking_file):
    """قراءة الملفات المعالجة وإرجاعها كـ set للمقارنة السريعة
    لكن بدون اللاحقة - فقط الاسم الأساسي"""
    try:
        with open(tracking_file, 'r', encoding='utf-8') as f:
            # استخراج الاسم الأساسي لكل ملف معالج
            return {extract_base_filename(line.strip()) for line in f if line.strip()}
    except Exception as e:
        print(f"⚠️ Warning reading tracking file: {e}")
        return set()


def is_processed(filename, tracking_file):
    """التحقق مما إذا كان الملف (أو أي نسخة منه بلاحقة مختلفة) معالج"""
    base_filename = extract_base_filename(filename)
    processed_set = get_processed_set(tracking_file)
    return base_filename in processed_set


def mark_as_processed(filename, tracking_file):
    """تسجيل الملف كمعالج - باستخدام الاسم الأساسي فقط"""
    base_filename = extract_base_filename(filename)
    
    # التحقق من عدم تسجيله مسبقاً
    try:
        with open(tracking_file, 'r', encoding='utf-8') as f:
            if base_filename in f.read().splitlines():
                return  # مسجل بالفعل
    except:
        pass
    
    # تسجيل الملف
    with open(tracking_file, 'a', encoding='utf-8') as f:
        f.write(base_filename + "\n")


def run_command(command, working_dir=None, timeout=None):
    """
    تنفيذ أمر مع timeout اختياري
    استخدام subprocess.run بدلاً من Popen لتجنب مشاكل التعليق
    """
    print(f"\n🚀 Executing: {' '.join(command)}")
    try:
        # استخدام subprocess.run بدون shell=True
        result = subprocess.run(
            command,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,  # إغلاق stdin لمنع exiftool من الانتظار
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            shell=False  # CRITICAL: لا تستخدم shell=True مع exiftool
        )
        
        if result.stdout:
            print(result.stdout.strip())
        
        if result.returncode != 0:
            print(f"❌ Command failed (exit code: {result.returncode}).")
            return False
        
        print(f"✅ Command finished successfully.")
        return True
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ Command timed out after {timeout} seconds.")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred while running the command: {e}")
        return False


def clear_existing_images():
    """Function for the 'clear' command: archives all current images."""
    print("\n[Command Received] 🧹 Starting to archive and ignore existing images...")
    try:
        image_files_to_add = {fn for fn in os.listdir(WATCHED_DIR) if fn.lower().endswith(IMAGE_EXTENSIONS)}
    except FileNotFoundError:
        print(f"❌ Error: Directory '{WATCHED_DIR}' not found.")
        return
    
    if not image_files_to_add:
        print("🟡 No existing images to archive.")
        return


    print(f"   - Found {len(image_files_to_add)} images.")
    for tracker_path in [ANIME4K_TRACKING_FILE, ESRGAN_TRACKING_FILE]:
        try:
            with open(tracker_path, 'r+', encoding='utf-8') as f:
                existing_entries = {extract_base_filename(line.strip()) for line in f}
                new_entries = {extract_base_filename(fn) for fn in image_files_to_add} - existing_entries
                if new_entries:
                    f.seek(0, 2)
                    for entry in sorted(list(new_entries)):
                        f.write(entry + "\n")
                    print(f"   - Added {len(new_entries)} new entries to {os.path.basename(tracker_path)}")
        except Exception as e:
            print(f"   - ❌ Failed to write to file '{tracker_path}'. Error: {e}")
    print("   ✅ Archiving complete. These images will now be ignored.")



# --- 5. Core Processing Functions (with Metadata fix) ---


def process_with_anime4k(filepath):
    if not PYANIME4K_AVAILABLE: return False
    filename = os.path.basename(filepath)
    output_path = os.path.join(SHARING_DIR, filename)
    print(f"\n[1A] ⚡️ Starting fast processing with Anime4K for {filename}...")
    try:
        image_bgr = cv2.imread(filepath)
        if image_bgr is None: return False
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        result_rgb = anime4k_processor(image_rgb, factor=4.0)
        result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, result_bgr)
        print(f"   [✔] Temporarily saved to sharing directory: {output_path}")
        return True
    except Exception as e:
        print(f"   [❌] Anime4K processing failed: {e}")
        return False


def copy_metadata(source_path, dest_path):
    """
    نسخ EXIF metadata بطريقة آمنة
    """
    print(f"   [📝] Copying EXIF data from original to upscaled image...")
    
    # استخدام قائمة بدلاً من string، بدون shell=True
    command = [
        'exiftool',
        '-tagsFromFile', source_path,
        '-all:all',
        '-overwrite_original',
        dest_path
    ]
    
    # استخدام timeout للحماية من التعليق
    success = run_command(command, timeout=EXIFTOOL_TIMEOUT)
    
    if not success:
        print("   [⚠️] Metadata copy failed or timed out. Continuing without metadata...")


def process_with_esrgan_and_replace(filepath):
    filename = os.path.basename(filepath)
    print(f"\n[2A] 🐌 Starting slow, high-quality processing with Real-ESRGAN for {filename}...")
    base_name, ext = os.path.splitext(filename)
    temp_suffixed_filename = f"{base_name}_out{ext}"
    temp_output_path = os.path.join(SHARING_DIR, temp_suffixed_filename)
    command = [
        sys.executable, ESRGAN_INFERENCE_SCRIPT,
        '-n', 'realesr-general-x4v3', '-i', filepath, '-o', SHARING_DIR,
        '--outscale', '4', '--suffix', 'out', '--fp32'
    ]
    if not run_command(command, working_dir=ESRGAN_BASE_DIR):
        print(f"   [❌] Real-ESRGAN processing failed.")
        return False
    
    final_destination_path = os.path.join(SHARING_DIR, filename)
    if os.path.exists(temp_output_path):
        print(f"[2B] 🔄 Replacing fast version with high-quality version...")
        try:
            shutil.move(temp_output_path, final_destination_path)
            copy_metadata(filepath, final_destination_path)
            print(f"   [✔] File replaced and metadata copied successfully!")
            return True
        except Exception as e:
            print(f"   [❌] Failed to move the final file: {e}")
            return False
    else:
        print(f"   [❌] Real-ESRGAN output file not found.")
        return False


def process_single_image(filepath, filename):
    """معالجة صورة واحدة - دالة مشتركة لـ watchdog والفحص الدوري"""
    with processing_lock:  # منع معالجة نفس الصورة مرتين في نفس الوقت
        # Stage 1: Anime4K
        if not is_processed(filename, ANIME4K_TRACKING_FILE):
            if process_with_anime4k(filepath):
                dest_path = os.path.join(SHARING_DIR, filename)
                copy_metadata(filepath, dest_path)
                mark_as_processed(filename, ANIME4K_TRACKING_FILE)
        else:
            base_filename = extract_base_filename(filename)
            print(f"[1] ⏩ Skipping Anime4K stage ('{base_filename}' already processed).")
        
        # Stage 2: ESRGAN
        if ESRGAN_ENABLED:
            if not is_processed(filename, ESRGAN_TRACKING_FILE):
                if process_with_esrgan_and_replace(filepath):
                    mark_as_processed(filename, ESRGAN_TRACKING_FILE)
            else:
                base_filename = extract_base_filename(filename)
                print(f"[2] ⏩ Skipping ESRGAN stage ('{base_filename}' already processed).")
        else:
            print("[2] ⏩ Skipping ESRGAN stage (fast mode 'off' is active).")
            if not is_processed(filename, ESRGAN_TRACKING_FILE):
                mark_as_processed(filename, ESRGAN_TRACKING_FILE)
        
        print(f"\n✅ Workflow completed for: {filename}.")


# --- 6. NEW: Periodic Directory Scanner ---
def periodic_directory_scan():
    """
    فحص دوري للمجلد بالكامل للبحث عن الصور التي فاتت watchdog
    يعمل كل SCAN_INTERVAL ثانية
    """
    print(f"🔍 Periodic scanner started (interval: {SCAN_INTERVAL} seconds)")
    
    while not stop_flag.is_set():
        try:
            # الانتظار قبل الفحص التالي
            time.sleep(SCAN_INTERVAL)
            
            if stop_flag.is_set():
                break
            
            # الحصول على قائمة سريعة بكل الصور في المجلد
            try:
                all_files = os.listdir(WATCHED_DIR)
            except Exception as e:
                print(f"⚠️ Scanner: Error reading directory: {e}")
                continue
            
            # فلترة الصور فقط (باستخدام set comprehension - سريع جداً)
            image_files = {f for f in all_files if f.lower().endswith(IMAGE_EXTENSIONS)}
            
            if not image_files:
                continue
            
            # الحصول على الملفات المعالجة (باستخدام الاسم الأساسي - O(1) lookup)
            processed_anime4k = get_processed_set(ANIME4K_TRACKING_FILE)
            
            # إيجاد الصور التي لم تعالج بعد
            # يجب استخراج الاسم الأساسي لكل صورة أيضاً
            unprocessed = {f for f in image_files if extract_base_filename(f) not in processed_anime4k}
            
            if unprocessed:
                print(f"\n🔍 [Periodic Scan] Found {len(unprocessed)} unprocessed images!")
                
                # معالجة كل صورة لم تعالج
                for filename in sorted(unprocessed):
                    if stop_flag.is_set():
                        break
                    
                    filepath = os.path.join(WATCHED_DIR, filename)
                    
                    # التأكد من أن الملف موجود وليس قيد النسخ
                    if not os.path.exists(filepath):
                        continue
                    
                    # التأكد من اكتمال النسخ (مقارنة الحجم مرتين)
                    try:
                        size1 = os.path.getsize(filepath)
                        time.sleep(0.5)
                        size2 = os.path.getsize(filepath)
                        if size1 != size2:
                            print(f"   ⏳ File still copying: {filename}, will retry next scan")
                            continue
                    except:
                        continue
                    
                    print(f"\n{'='*40}\n🖼️ [Periodic Scan] Processing missed image: {filename}\n{'='*40}")
                    process_single_image(filepath, filename)
        
        except Exception as e:
            print(f"⚠️ Periodic scanner error: {e}")
    
    print("🔍 Periodic scanner stopped.")


# --- 7. Watchdog Handler (updated to use shared processing function) ---
class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or stop_flag.is_set(): return
        filepath = event.src_path
        filename = os.path.basename(filepath)
        if filename.lower().endswith(IMAGE_EXTENSIONS):
            print(f"\n{'='*40}\n🖼️ New image detected: {filename}\n{'='*40}")
            time.sleep(2)
            process_single_image(filepath, filename)


# --- 8. Background Command Listener ---
def keyboard_listener():
    global ESRGAN_ENABLED
    print("\n✅ Command listener is ready. Available commands: 'clear', 'on', 'off', 'exit'")
    while not stop_flag.is_set():
        try:
            command = input()
            if command.lower() == 'clear':
                clear_existing_images()
            elif command.lower() == 'off':
                ESRGAN_ENABLED = False
                print("\n[Command Received] ⏸️ Fast mode activated. Real-ESRGAN will be skipped.")
            elif command.lower() == 'on':
                ESRGAN_ENABLED = True
                print("\n[Command Received] ▶️ Full mode activated. Real-ESRGAN will be executed.")
            elif command.lower() == 'exit':
                print("\n[Command Received] 🛑 Received 'exit' command. Shutting down gracefully...")
                stop_flag.set()
                break
            else:
                print(f"\n[?] Unknown command: '{command}'. Available commands: clear, on, off, exit")
        except (EOFError, KeyboardInterrupt):
            stop_flag.set()
            break
    print("🛑 Command listener stopped.")


# --- 9. Main Program Execution ---
if __name__ == "__main__":
    setup_environment()
    if shutil.which("exiftool") is None:
        print("🛑 IMPORTANT: 'exiftool' not found. Image metadata will not be copied.")


    # إطلاق Command Listener Thread
    listener_thread = threading.Thread(target=keyboard_listener, daemon=True)
    listener_thread.start()


    # إطلاق Periodic Scanner Thread
    scanner_thread = threading.Thread(target=periodic_directory_scan, daemon=True)
    scanner_thread.start()


    # إطلاق Watchdog Observer
    event_handler = ImageHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=False)
    observer.start()
    
    print(f"\n🚀 Orchestrator script is running...")
    print(f"👁️ Watching directory: {WATCHED_DIR}")
    print(f"🎯 Results will be saved to: {SHARING_DIR}")
    print(f"🔍 Periodic scan interval: {SCAN_INTERVAL} seconds")
    print(f"⏱️ ExifTool timeout: {EXIFTOOL_TIMEOUT} seconds")
    print("Mode: ON (Anime4K + ESRGAN)")
    
    try:
        while not stop_flag.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Ctrl+C received. Initiating shutdown...")
        stop_flag.set()
    
    observer.stop()
    observer.join()
    scanner_thread.join(timeout=2)
    print("👋 Program finished.")
# END: MODIFIED SECTION
