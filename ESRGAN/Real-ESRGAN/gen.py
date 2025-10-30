#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import glob

# المسارات الأساسية
BASE_DIR = Path(r"C:\Users\Stark\Download\myhome\video_rating_app\ESRGAN\Real-ESRGAN")
INPUT_DIR = BASE_DIR / "inputs"
OUTPUT_DIR = BASE_DIR / "output"

# مسارات قواعد البيانات
DB_PATHS = [
    r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json",
    r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo pic.json",
    r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_Dib.json"
]

# المجلدات الأساسية للصور والفيديوهات
SOURCE_DIRS = [
    r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo pic",
    r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik",
    r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\Dib"
]

# نماذج Real-ESRGAN المتاحة
MODELS = {
    "1": "RealESRGAN_x2plus",
    "2": "RealESRGAN_x4plus",
    "3": "realesr-general-x4v3",
    "4": "RealESRGAN_x4plus_anime_6B",
    "5": "realesr-animevideov3"
}

# امتدادات الملفات
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff']
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']

def clear_screen():
    """مسح الشاشة"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """طباعة عنوان مزخرف"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def get_user_choice(prompt, options):
    """الحصول على اختيار المستخدم من قائمة"""
    print(prompt)
    for key, value in options.items():
        print(f"  [{key}] {value}")
    
    while True:
        choice = input("\nأدخل رقم الخيار: ").strip()
        if choice in options:
            return choice
        print("❌ اختيار غير صحيح، حاول مرة أخرى.")

def get_files_by_extension(directory, extensions):
    """الحصول على قائمة الملفات حسب الامتداد"""
    files = []
    for ext in extensions:
        files.extend(glob.glob(str(directory / f"*{ext}")))
    return files

def run_command(cmd, show_output=True):
    """تنفيذ أمر في سطر الأوامر"""
    print(f"\n🔄 تنفيذ الأمر:\n{cmd}\n")
    
    if show_output:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 universal_newlines=True, encoding='utf-8', errors='replace')
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.rstrip())
        process.wait()
        return process.returncode == 0
    else:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0

def enhance_images():
    """رفع جودة الصور"""
    print_header("رفع جودة الصور")
    
    # البحث عن الصور في مجلد الإدخال
    image_files = get_files_by_extension(INPUT_DIR, IMAGE_EXTENSIONS)
    
    if not image_files:
        print("❌ لا توجد صور في مجلد الإدخال!")
        return
    
    print(f"✅ تم العثور على {len(image_files)} صورة")
    
    # الحصول على إعدادات المستخدم
    print("\n📋 الإعدادات:")
    
    # Tile size
    tile = input("أدخل قيمة tile (الافتراضي 128): ").strip()
    tile = tile if tile else "128"
    
    # Outscale
    outscale = input("أدخل قيمة outscale (الافتراضي 1.2): ").strip()
    outscale = outscale if outscale else "1.2"
    
    # Suffix
    suffix = input("أدخل suffix (اتركه فارغاً إذا لم تريد): ").strip()
    
    # Output folder
    output_folder = input("أدخل مجلد الإخراج (الافتراضي output): ").strip()
    output_folder = output_folder if output_folder else "output"
    
    # اختيار الموديل
    print("\n🎨 اختر الموديل:")
    model_choice = get_user_choice("", MODELS)
    model_name = MODELS[model_choice]
    
    # بناء الأمر
    cmd = f"python inference_realesrgan.py"
    cmd += f" -n {model_name}"
    cmd += f" -i inputs"
    cmd += f" -o {output_folder}"
    cmd += f" --fp32"
    cmd += f" --tile {tile}"
    cmd += f" --outscale {outscale}"
    
    if suffix:
        cmd += f" --suffix {suffix}"
    
    # تنفيذ الأمر
    os.chdir(BASE_DIR)
    success = run_command(cmd)
    
    if success:
        print("\n✅ تم رفع جودة الصور بنجاح!")
    else:
        print("\n❌ حدث خطأ أثناء رفع جودة الصور!")

def process_enhanced_images():
    """معالجة الصور بعد رفع جودتها"""
    print_header("معالجة الصور بعد رفع الجودة")
    
    options = {
        "1": "إعادة تسمية الملفات (حذف _out)",
        "2": "تحديث قواعد البيانات",
        "3": "نقل الصور إلى مجلداتها الأصلية",
        "4": "العودة للقائمة الرئيسية"
    }
    
    choice = get_user_choice("اختر العملية المطلوبة:", options)
    
    if choice == "1":
        rename_files()
    elif choice == "2":
        update_databases()
    elif choice == "3":
        move_files_to_source()
    elif choice == "4":
        return

def rename_files():
    """إعادة تسمية الملفات وحذف _out"""
    print("\n🔄 إعادة تسمية الملفات...")
    
    renamed_count = 0
    for file_path in OUTPUT_DIR.glob("*"):
        if file_path.is_file() and "_out" in file_path.stem:
            new_name = file_path.name.replace("_out", "")
            new_path = file_path.parent / new_name
            
            try:
                file_path.rename(new_path)
                print(f"✅ {file_path.name} -> {new_name}")
                renamed_count += 1
            except Exception as e:
                print(f"❌ فشل في إعادة تسمية {file_path.name}: {e}")
    
    print(f"\n✅ تم إعادة تسمية {renamed_count} ملف")

def update_databases():
    """تحديث أحجام الملفات في قواعد البيانات"""
    print("\n🔄 تحديث قواعد البيانات...")
    
    # جمع معلومات الملفات من مجلد الإخراج
    output_files = {}
    for file_path in OUTPUT_DIR.glob("*"):
        if file_path.is_file():
            file_size = file_path.stat().st_size
            output_files[file_path.name] = file_size
    
    if not output_files:
        print("❌ لا توجد ملفات في مجلد الإخراج!")
        return
    
    updates_to_make = []
    
    # البحث في قواعد البيانات
    for db_path in DB_PATHS:
        if not os.path.exists(db_path):
            print(f"⚠️ قاعدة البيانات غير موجودة: {db_path}")
            continue
        
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            
            for filename, new_size in output_files.items():
                if filename in db_data:
                    old_size = db_data[filename].get('file_size', 0)
                    updates_to_make.append({
                        'db_path': db_path,
                        'filename': filename,
                        'old_size': old_size,
                        'new_size': new_size
                    })
        except Exception as e:
            print(f"❌ خطأ في قراءة {db_path}: {e}")
    
    if not updates_to_make:
        print("❌ لم يتم العثور على ملفات مطابقة في قواعد البيانات!")
        return
    
    # عرض التحديثات المقترحة
    print(f"\n📊 تم العثور على {len(updates_to_make)} تحديث مطلوب:")
    for update in updates_to_make:
        print(f"  📁 {update['filename']}")
        print(f"     قاعدة البيانات: {os.path.basename(update['db_path'])}")
        print(f"     الحجم القديم: {update['old_size']:,} بايت")
        print(f"     الحجم الجديد: {update['new_size']:,} بايت")
    
    confirm = input("\n❓ هل أنت متأكد من تحديث الأحجام؟ (نعم/لا): ").strip().lower()
    
    if confirm in ['نعم', 'yes', 'y']:
        # تطبيق التحديثات
        for db_path in DB_PATHS:
            if not os.path.exists(db_path):
                continue
            
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    db_data = json.load(f)
                
                updated = False
                for update in updates_to_make:
                    if update['db_path'] == db_path and update['filename'] in db_data:
                        db_data[update['filename']]['file_size'] = update['new_size']
                        updated = True
                
                if updated:
                    with open(db_path, 'w', encoding='utf-8') as f:
                        json.dump(db_data, f, ensure_ascii=False, indent=4)
                    print(f"✅ تم تحديث: {os.path.basename(db_path)}")
                    
            except Exception as e:
                print(f"❌ خطأ في تحديث {db_path}: {e}")
        
        print("\n✅ تم تحديث قواعد البيانات بنجاح!")
    else:
        print("❌ تم إلغاء التحديث")

def move_files_to_source():
    """نقل الملفات إلى مجلداتها الأصلية"""
    print("\n🔄 نقل الملفات إلى مجلداتها الأصلية...")
    
    files_to_move = []
    
    # البحث عن الملفات المطابقة
    for file_path in OUTPUT_DIR.glob("*"):
        if not file_path.is_file():
            continue
        
        for source_dir in SOURCE_DIRS:
            source_file = Path(source_dir) / file_path.name
            if source_file.exists():
                files_to_move.append({
                    'source': file_path,
                    'destination': source_file,
                    'dir_name': os.path.basename(source_dir)
                })
                break
    
    if not files_to_move:
        print("❌ لم يتم العثور على ملفات مطابقة في المجلدات الأصلية!")
        return
    
    # عرض الملفات التي سيتم نقلها
    print(f"\n📊 تم العثور على {len(files_to_move)} ملف للنقل:")
    for file_info in files_to_move:
        print(f"  📁 {file_info['source'].name} -> {file_info['dir_name']}")
    
    confirm = input("\n❓ هل أنت متأكد من استبدال الملفات؟ (نعم/لا): ").strip().lower()
    
    if confirm in ['نعم', 'yes', 'y']:
        moved_count = 0
        for file_info in files_to_move:
            try:
                shutil.move(str(file_info['source']), str(file_info['destination']))
                print(f"✅ تم نقل: {file_info['source'].name}")
                moved_count += 1
            except Exception as e:
                print(f"❌ فشل في نقل {file_info['source'].name}: {e}")
        
        print(f"\n✅ تم نقل {moved_count} ملف بنجاح!")
    else:
        print("❌ تم إلغاء النقل")

def enhance_videos():
    """رفع جودة الفيديوهات"""
    print_header("رفع جودة الفيديوهات")
    
    # البحث عن الفيديوهات في مجلد الإدخال
    video_files = get_files_by_extension(INPUT_DIR, VIDEO_EXTENSIONS)
    
    if not video_files:
        print("❌ لا توجد فيديوهات في مجلد الإدخال!")
        return
    
    print(f"✅ تم العثور على {len(video_files)} فيديو")
    
    # الحصول على إعدادات المستخدم
    print("\n📋 الإعدادات:")
    
    # Tile size
    tile = input("أدخل قيمة tile (الافتراضي 128): ").strip()
    tile = tile if tile else "128"
    
    # Outscale  
    outscale = input("أدخل قيمة outscale (الافتراضي 1.2): ").strip()
    outscale = outscale if outscale else "1.2"
    
    # اختيار الموديل
    print("\n🎨 اختر الموديل:")
    model_choice = get_user_choice("", MODELS)
    model_name = MODELS[model_choice]
    
    # معالجة كل فيديو
    for video_path in video_files:
        video_path = Path(video_path)
        print(f"\n📹 معالجة: {video_path.name}")
        
        # الحصول على حجم الفيديو
        video_size = video_path.stat().st_size
        
        # إنشاء مجلدات الإطارات
        frames_input_dir = INPUT_DIR / str(video_size)
        frames_output_dir = OUTPUT_DIR / str(video_size)
        
        frames_input_dir.mkdir(exist_ok=True)
        frames_output_dir.mkdir(exist_ok=True)
        
        # استخراج الإطارات
        print("  1️⃣ استخراج الإطارات...")
        extract_cmd = f'ffmpeg -i "{video_path}" "{frames_input_dir}/frame_%05d.png"'
        
        if not run_command(extract_cmd, show_output=False):
            print(f"  ❌ فشل في استخراج إطارات {video_path.name}")
            continue
        
        # رفع جودة الإطارات
        print("  2️⃣ رفع جودة الإطارات...")
        enhance_cmd = f"python inference_realesrgan.py"
        enhance_cmd += f" -n {model_name}"
        enhance_cmd += f' -i "inputs/{video_size}"'
        enhance_cmd += f' -o "output/{video_size}"'
        enhance_cmd += f" --fp32"
        enhance_cmd += f" --tile {tile}"
        enhance_cmd += f" --outscale {outscale}"
        
        os.chdir(BASE_DIR)
        if not run_command(enhance_cmd):
            print(f"  ❌ فشل في رفع جودة إطارات {video_path.name}")
            continue
        
        # تجميع الإطارات
        print("  3️⃣ تجميع الإطارات...")
        output_video_name = f"{video_path.stem}_without_voice.mp4"
        output_video_path = OUTPUT_DIR / output_video_name
        
        merge_cmd = f'ffmpeg -framerate 24 -i "{frames_output_dir}/frame_%05d_out.png" '
        merge_cmd += f'-c:v libx264 -pix_fmt yuv420p "{output_video_path}"'
        
        if not run_command(merge_cmd, show_output=False):
            print(f"  ❌ فشل في تجميع إطارات {video_path.name}")
            continue
        
        # دمج الصوت
        print("  4️⃣ دمج الصوت...")
        final_video_path = OUTPUT_DIR / f"{video_path.stem}.mp4"
        
        audio_cmd = f'ffmpeg -i "{output_video_path}" -i "{video_path}" '
        audio_cmd += f'-c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -y "{final_video_path}"'
        
        if run_command(audio_cmd, show_output=False):
            print(f"  ✅ تم إنشاء: {final_video_path.name}")
            # حذف الفيديو المؤقت
            output_video_path.unlink(missing_ok=True)
        else:
            print(f"  ❌ فشل في دمج الصوت لـ {video_path.name}")
        
        # تنظيف مجلدات الإطارات (اختياري)
        cleanup = input("\n  ❓ هل تريد حذف الإطارات المؤقتة؟ (نعم/لا): ").strip().lower()
        if cleanup in ['نعم', 'yes', 'y']:
            shutil.rmtree(frames_input_dir, ignore_errors=True)
            shutil.rmtree(frames_output_dir, ignore_errors=True)
            print("  ✅ تم حذف الإطارات المؤقتة")
    
    print("\n✅ انتهت معالجة جميع الفيديوهات!")

def process_enhanced_videos():
    """معالجة الفيديوهات بعد رفع جودتها"""
    print_header("معالجة الفيديوهات بعد رفع الجودة")
    
    options = {
        "1": "تحديث قواعد البيانات",
        "2": "نقل الفيديوهات إلى مجلداتها الأصلية",
        "3": "العودة للقائمة الرئيسية"
    }
    
    choice = get_user_choice("اختر العملية المطلوبة:", options)
    
    if choice == "1":
        update_databases()  # نفس الدالة تعمل للصور والفيديوهات
    elif choice == "2":
        move_files_to_source()  # نفس الدالة تعمل للصور والفيديوهات
    elif choice == "3":
        return

def main():
    """القائمة الرئيسية"""
    while True:
        clear_screen()
        print_header("🚀 Real-ESRGAN واجهة تفاعلية")
        
        options = {
            "1": "رفع جودة الصور",
            "2": "رفع جودة الفيديوهات",
            "3": "معالجة الصور بعد رفع الجودة",
            "4": "معالجة الفيديوهات بعد رفع الجودة",
            "5": "خروج"
        }
        
        choice = get_user_choice("اختر العملية المطلوبة:", options)
        
        if choice == "1":
            enhance_images()
        elif choice == "2":
            enhance_videos()
        elif choice == "3":
            process_enhanced_images()
        elif choice == "4":
            process_enhanced_videos()
        elif choice == "5":
            print("\n👋 مع السلامة!")
            sys.exit(0)
        
        input("\n\nاضغط Enter للمتابعة...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ تم إلغاء البرنامج")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ حدث خطأ غير متوقع: {e}")
        input("اضغط Enter للخروج...")
        sys.exit(1)
