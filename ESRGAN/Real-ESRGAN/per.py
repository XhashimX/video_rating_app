# esrgan_automation.py
"""
سكريبت شامل لأتمتة عمليات Real-ESRGAN مع واجهة تفاعلية
يدعم رفع جودة الصور والفيديوهات ومعالجتها بعد ذلك
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# ========== START: MODIFIED SECTION - المسارات الثابتة ==========
BASE_DIR = Path(r"C:\Users\Stark\Download\myhome\video_rating_app\ESRGAN\Real-ESRGAN")
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUT_DIR = BASE_DIR / "output"

# مسارات قواعد البيانات
DB_PATHS = [
    Path(r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"),
    Path(r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo pic.json"),
    Path(r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_Dib.json")
]

# المجلدات الأصلية للملفات
ORIGINAL_DIRS = [
    Path(r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo pic"),
    Path(r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"),
    Path(r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\Dib")
]

# امتدادات الملفات
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.flv'}

# نماذج Real-ESRGAN المتاحة
AVAILABLE_MODELS = [
    "RealESRGAN_x2plus",
    "RealESRGAN_x4plus",
    "realesr-general-x4v3",
    "RealESRGAN_x4plus_anime_6B",
    "realesr-animevideov3"
]
# ========== END: MODIFIED SECTION ==========


class ESRGANAutomation:
    """الكلاس الرئيسي لأتمتة عمليات Real-ESRGAN"""
    
    def __init__(self):
        """تهيئة الكلاس"""
        self.base_dir = BASE_DIR
        self.inputs_dir = INPUTS_DIR
        self.output_dir = OUTPUT_DIR
        
    def clear_screen(self):
        """مسح الشاشة"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """طباعة عنوان مع تنسيق"""
        print("\n" + "="*60)
        print(f"  {title}")
        print("="*60 + "\n")
    
    def get_user_choice(self, prompt: str, valid_choices: List[str]) -> str:
        """الحصول على اختيار المستخدم"""
        while True:
            choice = input(f"{prompt}: ").strip()
            if choice in valid_choices:
                return choice
            print(f"❌ اختيار غير صحيح. الخيارات المتاحة: {', '.join(valid_choices)}")
    
    def get_files_by_extension(self, directory: Path, extensions: set) -> List[Path]:
        """الحصول على قائمة الملفات حسب الامتداد"""
        files = []
        for file in directory.iterdir():
            if file.is_file() and file.suffix.lower() in extensions:
                files.append(file)
        return sorted(files)
    
    # ========== START: MODIFIED SECTION - رفع جودة الصور ==========
    def upscale_images(self):
        """رفع جودة الصور باستخدام Real-ESRGAN"""
        self.print_header("رفع جودة الصور")
        
        # التحقق من وجود صور
        images = self.get_files_by_extension(self.inputs_dir, IMAGE_EXTENSIONS)
        if not images:
            print("❌ لا توجد صور في مجلد المدخلات!")
            return
        
        print(f"✅ تم العثور على {len(images)} صورة")
        
        # الحصول على الإعدادات من المستخدم
        print("\n--- إعدادات المعالجة ---")
        
        # tile
        tile_input = input("أدخل قيمة tile (افتراضي: 128): ").strip()
        tile = tile_input if tile_input else "128"
        
        # outscale
        outscale_input = input("أدخل قيمة outscale (افتراضي: 1.2): ").strip()
        outscale = outscale_input if outscale_input else "1.2"
        
        # suffix
        suffix_input = input("أدخل قيمة suffix (اتركه فارغاً إذا لم ترد استخدامه): ").strip()
        
        # output name
        output_name = input("أدخل اسم مجلد الإخراج (افتراضي: output): ").strip()
        if not output_name:
            output_name = "output"
        output_path = self.output_dir / output_name
        
        # اختيار النموذج
        print("\n--- اختر النموذج ---")
        for i, model in enumerate(AVAILABLE_MODELS, 1):
            default_mark = " (افتراضي)" if model == "RealESRGAN_x2plus" else ""
            print(f"{i}. {model}{default_mark}")
        
        model_choice = input("\nاختر رقم النموذج (افتراضي: 1): ").strip()
        if not model_choice or model_choice == "1":
            model = AVAILABLE_MODELS[0]
        else:
            try:
                model = AVAILABLE_MODELS[int(model_choice) - 1]
            except (ValueError, IndexError):
                print("⚠️ اختيار غير صحيح، سيتم استخدام النموذج الافتراضي")
                model = AVAILABLE_MODELS[0]
        
        # بناء الأمر
        cmd = [
            sys.executable,  # python
            "inference_realesrgan.py",
            "-n", model,
            "-i", str(self.inputs_dir),
            "-o", str(output_path),
            "--fp32",
            "--tile", tile,
            "--outscale", outscale
        ]
        
        # إضافة suffix إذا كان موجوداً
        if suffix_input:
            cmd.extend(["--suffix", suffix_input])
        
        # عرض الأمر
        print("\n--- الأمر الذي سيتم تنفيذه ---")
        print(" ".join(cmd))
        
        # تأكيد التنفيذ
        confirm = input("\n⚠️ هل تريد تنفيذ الأمر؟ (نعم/لا): ").strip().lower()
        if confirm not in ['نعم', 'yes', 'y']:
            print("❌ تم إلغاء العملية")
            return
        
        # تنفيذ الأمر
        print("\n🔄 جاري معالجة الصور...\n")
        try:
            result = subprocess.run(cmd, cwd=self.base_dir, check=True)
            print("\n✅ تمت معالجة الصور بنجاح!")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ حدث خطأ أثناء المعالجة: {e}")
    # ========== END: MODIFIED SECTION ==========
    
    # ========== START: MODIFIED SECTION - معالجة الصور بعد رفع الجودة ==========
    def process_upscaled_images(self):
        """معالجة الصور بعد رفع الجودة"""
        self.print_header("معالجة الصور بعد رفع الجودة")
        
        print("اختر العملية:")
        print("1. إعادة تسمية الملفات (حذف _out)")
        print("2. تحديث قاعدة البيانات")
        print("3. نقل الصور إلى مجلداتها الأصلية")
        print("0. رجوع")
        
        choice = self.get_user_choice("اختر رقم العملية", ["1", "2", "3", "0"])
        
        if choice == "1":
            self.rename_output_files()
        elif choice == "2":
            self.update_database()
        elif choice == "3":
            self.move_images_to_original()
    
    def rename_output_files(self):
        """إعادة تسمية الملفات بحذف _out"""
        self.print_header("إعادة تسمية الملفات")
        
        # البحث عن الملفات التي تنتهي بـ _out
        files_to_rename = []
        for file in self.output_dir.rglob("*_out.*"):
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS:
                files_to_rename.append(file)
        
        if not files_to_rename:
            print("❌ لم يتم العثور على ملفات تنتهي بـ _out")
            return
        
        print(f"✅ تم العثور على {len(files_to_rename)} ملف")
        print("\nأمثلة على الملفات التي سيتم إعادة تسميتها:")
        for i, file in enumerate(files_to_rename[:5], 1):
            new_name = file.stem.replace("_out", "") + file.suffix
            print(f"{i}. {file.name} → {new_name}")
        
        if len(files_to_rename) > 5:
            print(f"... و {len(files_to_rename) - 5} ملف آخر")
        
        confirm = input("\n⚠️ هل تريد المتابعة؟ (نعم/لا): ").strip().lower()
        if confirm not in ['نعم', 'yes', 'y']:
            print("❌ تم إلغاء العملية")
            return
        
        # إعادة التسمية
        success_count = 0
        for file in files_to_rename:
            try:
                new_name = file.stem.replace("_out", "") + file.suffix
                new_path = file.parent / new_name
                file.rename(new_path)
                success_count += 1
            except Exception as e:
                print(f"❌ خطأ في إعادة تسمية {file.name}: {e}")
        
        print(f"\n✅ تمت إعادة تسمية {success_count} من {len(files_to_rename)} ملف")
    
    def update_database(self):
        """تحديث أحجام الملفات في قاعدة البيانات"""
        self.print_header("تحديث قاعدة البيانات")
        
        # الحصول على الملفات من مجلد الإخراج
        output_files = {}
        for file in self.output_dir.rglob("*"):
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS:
                output_files[file.name] = file.stat().st_size
        
        if not output_files:
            print("❌ لا توجد ملفات في مجلد الإخراج")
            return
        
        print(f"✅ تم العثور على {len(output_files)} ملف في مجلد الإخراج")
        
        # البحث عن التطابقات في قواعد البيانات
        matches_found = []
        
        for db_path in DB_PATHS:
            if not db_path.exists():
                print(f"⚠️ قاعدة البيانات غير موجودة: {db_path}")
                continue
            
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    db_data = json.load(f)
                
                for filename, new_size in output_files.items():
                    if filename in db_data:
                        old_size = db_data[filename].get('file_size', 0)
                        matches_found.append({
                            'db_path': db_path,
                            'filename': filename,
                            'old_size': old_size,
                            'new_size': new_size
                        })
            except Exception as e:
                print(f"❌ خطأ في قراءة قاعدة البيانات {db_path}: {e}")
        
        if not matches_found:
            print("❌ لم يتم العثور على تطابقات في قواعد البيانات")
            return
        
        # عرض التطابقات
        print(f"\n✅ تم العثور على {len(matches_found)} تطابق:")
        print("\n{:<50} {:<15} {:<15}".format("اسم الملف", "الحجم القديم", "الحجم الجديد"))
        print("-" * 80)
        for match in matches_found[:10]:
            print("{:<50} {:<15} {:<15}".format(
                match['filename'][:47] + "..." if len(match['filename']) > 50 else match['filename'],
                match['old_size'],
                match['new_size']
            ))
        
        if len(matches_found) > 10:
            print(f"... و {len(matches_found) - 10} تطابق آخر")
        
        confirm = input("\n⚠️ هل تريد تحديث الأحجام؟ (نعم/لا): ").strip().lower()
        if confirm not in ['نعم', 'yes', 'y']:
            print("❌ تم إلغاء العملية")
            return
        
        # تحديث قواعد البيانات
        updated_dbs = {}
        for match in matches_found:
            db_path = match['db_path']
            if db_path not in updated_dbs:
                with open(db_path, 'r', encoding='utf-8') as f:
                    updated_dbs[db_path] = json.load(f)
            
            updated_dbs[db_path][match['filename']]['file_size'] = match['new_size']
        
        # حفظ التغييرات
        success_count = 0
        for db_path, db_data in updated_dbs.items():
            try:
                with open(db_path, 'w', encoding='utf-8') as f:
                    json.dump(db_data, f, ensure_ascii=False, indent=4)
                success_count += 1
            except Exception as e:
                print(f"❌ خطأ في حفظ قاعدة البيانات {db_path}: {e}")
        
        print(f"\n✅ تم تحديث {success_count} من {len(updated_dbs)} قاعدة بيانات")
    
    def move_images_to_original(self):
        """نقل الصور إلى مجلداتها الأصلية"""
        self.print_header("نقل الصور إلى مجلداتها الأصلية")
        
        # الحصول على الملفات من مجلد الإخراج
        output_files = {}
        for file in self.output_dir.rglob("*"):
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS:
                output_files[file.name] = file
        
        if not output_files:
            print("❌ لا توجد ملفات في مجلد الإخراج")
            return
        
        print(f"✅ تم العثور على {len(output_files)} ملف في مجلد الإخراج")
        
        # البحث عن التطابقات في المجلدات الأصلية
        matches = []
        for output_name, output_file in output_files.items():
            for original_dir in ORIGINAL_DIRS:
                if not original_dir.exists():
                    continue
                
                for original_file in original_dir.iterdir():
                    if original_file.is_file() and original_file.name == output_name:
                        old_size = original_file.stat().st_size
                        new_size = output_file.stat().st_size
                        if old_size != new_size:
                            matches.append({
                                'output_file': output_file,
                                'original_file': original_file,
                                'old_size': old_size,
                                'new_size': new_size
                            })
                        break
        
        if not matches:
            print("❌ لم يتم العثور على ملفات مطابقة للاستبدال")
            return
        
        # عرض التطابقات
        print(f"\n✅ تم العثور على {len(matches)} ملف للاستبدال:")
        print("\n{:<50} {:<15} {:<15}".format("اسم الملف", "الحجم القديم", "الحجم الجديد"))
        print("-" * 80)
        for match in matches[:10]:
            print("{:<50} {:<15} {:<15}".format(
                match['output_file'].name[:47] + "..." if len(match['output_file'].name) > 50 else match['output_file'].name,
                match['old_size'],
                match['new_size']
            ))
        
        if len(matches) > 10:
            print(f"... و {len(matches) - 10} ملف آخر")
        
        confirm = input("\n⚠️ هل تريد استبدال الملفات؟ (نعم/لا): ").strip().lower()
        if confirm not in ['نعم', 'yes', 'y']:
            print("❌ تم إلغاء العملية")
            return
        
        # استبدال الملفات
        success_count = 0
        for match in matches:
            try:
                shutil.copy2(match['output_file'], match['original_file'])
                success_count += 1
            except Exception as e:
                print(f"❌ خطأ في نقل {match['output_file'].name}: {e}")
        
        print(f"\n✅ تم استبدال {success_count} من {len(matches)} ملف")
    # ========== END: MODIFIED SECTION ==========
    
    # ========== START: MODIFIED SECTION - رفع جودة الفيديوهات ==========
    def upscale_videos(self):
        """رفع جودة الفيديوهات"""
        self.print_header("رفع جودة الفيديوهات")
        
        # التحقق من وجود ffmpeg
        if not self.check_ffmpeg():
            print("❌ ffmpeg غير مثبت أو غير موجود في PATH")
            return
        
        # الحصول على الفيديوهات
        videos = self.get_files_by_extension(self.inputs_dir, VIDEO_EXTENSIONS)
        if not videos:
            print("❌ لا توجد فيديوهات في مجلد المدخلات!")
            return
        
        print(f"✅ تم العثور على {len(videos)} فيديو")
        for i, video in enumerate(videos, 1):
            size = video.stat().st_size
            print(f"{i}. {video.name} (الحجم: {size} بايت)")
        
        # الحصول على إعدادات المعالجة
        print("\n--- إعدادات المعالجة ---")
        
        # tile
        tile_input = input("أدخل قيمة tile (افتراضي: 128): ").strip()
        tile = tile_input if tile_input else "128"
        
        # outscale
        outscale_input = input("أدخل قيمة outscale (افتراضي: 1.2): ").strip()
        outscale = outscale_input if outscale_input else "1.2"
        
        # suffix
        suffix_input = input("أدخل قيمة suffix (اتركه فارغاً إذا لم ترد استخدامه): ").strip()
        
        # اختيار النموذج
        print("\n--- اختر النموذج ---")
        for i, model in enumerate(AVAILABLE_MODELS, 1):
            default_mark = " (افتراضي)" if model == "RealESRGAN_x2plus" else ""
            print(f"{i}. {model}{default_mark}")
        
        model_choice = input("\nاختر رقم النموذج (افتراضي: 1): ").strip()
        if not model_choice or model_choice == "1":
            model = AVAILABLE_MODELS[0]
        else:
            try:
                model = AVAILABLE_MODELS[int(model_choice) - 1]
            except (ValueError, IndexError):
                print("⚠️ اختيار غير صحيح، سيتم استخدام النموذج الافتراضي")
                model = AVAILABLE_MODELS[0]
        
        # معالجة كل فيديو
        for video in videos:
            print(f"\n{'='*60}")
            print(f"معالجة الفيديو: {video.name}")
            print(f"{'='*60}")
            
            video_size = video.stat().st_size
            frames_dir_name = str(video_size)
            
            # المسارات
            input_frames_dir = self.inputs_dir / frames_dir_name
            output_frames_dir = self.output_dir / frames_dir_name
            
            # إنشاء المجلدات
            input_frames_dir.mkdir(exist_ok=True)
            output_frames_dir.mkdir(exist_ok=True)
            
            # 1. استخراج الإطارات
            print("\n🔄 استخراج الإطارات...")
            extract_cmd = [
                "ffmpeg",
                "-i", str(video),
                str(input_frames_dir / "frame_%05d.png")
            ]
            
            try:
                subprocess.run(extract_cmd, check=True, capture_output=True)
                print("✅ تم استخراج الإطارات")
            except subprocess.CalledProcessError as e:
                print(f"❌ خطأ في استخراج الإطارات: {e}")
                continue
            
            # 2. معالجة الإطارات بـ Real-ESRGAN
            print("\n🔄 معالجة الإطارات...")
            upscale_cmd = [
                sys.executable,
                "inference_realesrgan.py",
                "-n", model,
                "-i", str(input_frames_dir),
                "-o", str(output_frames_dir),
                "--fp32",
                "--tile", tile,
                "--outscale", outscale
            ]
            
            if suffix_input:
                upscale_cmd.extend(["--suffix", suffix_input])
            
            try:
                subprocess.run(upscale_cmd, cwd=self.base_dir, check=True)
                print("✅ تمت معالجة الإطارات")
            except subprocess.CalledProcessError as e:
                print(f"❌ خطأ في معالجة الإطارات: {e}")
                continue
            
            # 3. إعادة تجميع الفيديو بدون صوت
            print("\n🔄 إعادة تجميع الفيديو...")
            video_without_audio = self.output_dir / f"{video.stem}_without_voice.mp4"
            
            # تحديد نمط الإطارات (مع أو بدون _out)
            frame_pattern = "frame_%05d_out.png" if suffix_input or os.path.exists(output_frames_dir / "frame_00001_out.png") else "frame_%05d.png"
            
            reassemble_cmd = [
                "ffmpeg",
                "-framerate", "24",
                "-i", str(output_frames_dir / frame_pattern),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                str(video_without_audio),
                "-y"
            ]
            
            try:
                subprocess.run(reassemble_cmd, check=True, capture_output=True)
                print("✅ تم إعادة تجميع الفيديو")
            except subprocess.CalledProcessError as e:
                print(f"❌ خطأ في إعادة تجميع الفيديو: {e}")
                continue
            
            # 4. إضافة الصوت
            print("\n🔄 إضافة الصوت...")
            final_video = self.output_dir / f"{video.stem}.mp4"
            
            add_audio_cmd = [
                "ffmpeg",
                "-i", str(video_without_audio),
                "-i", str(video),
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-y",
                str(final_video)
            ]
            
            try:
                subprocess.run(add_audio_cmd, check=True, capture_output=True)
                print("✅ تمت إضافة الصوت")
                
                # حذف الفيديو المؤقت
                video_without_audio.unlink()
                
                print(f"\n✅ تمت معالجة الفيديو بنجاح: {final_video}")
            except subprocess.CalledProcessError as e:
                print(f"❌ خطأ في إضافة الصوت: {e}")
                continue
        
        print("\n" + "="*60)
        print("✅ انتهت معالجة جميع الفيديوهات")
        print("="*60)
    
    def check_ffmpeg(self) -> bool:
        """التحقق من وجود ffmpeg"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    # ========== END: MODIFIED SECTION ==========
    
    # ========== START: MODIFIED SECTION - معالجة الفيديوهات بعد رفع الجودة ==========
    def process_upscaled_videos(self):
        """معالجة الفيديوهات بعد رفع الجودة"""
        self.print_header("معالجة الفيديوهات بعد رفع الجودة")
        
        print("اختر العملية:")
        print("1. تحديث قاعدة البيانات")
        print("2. نقل الفيديوهات إلى مجلداتها الأصلية")
        print("0. رجوع")
        
        choice = self.get_user_choice("اختر رقم العملية", ["1", "2", "0"])
        
        if choice == "1":
            self.update_database_videos()
        elif choice == "2":
            self.move_videos_to_original()
    
    def update_database_videos(self):
        """تحديث أحجام الفيديوهات في قاعدة البيانات"""
        self.print_header("تحديث قاعدة البيانات - فيديوهات")
        
        # الحصول على الفيديوهات من مجلد الإخراج
        output_files = {}
        for file in self.output_dir.rglob("*"):
            if file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS:
                output_files[file.name] = file.stat().st_size
        
        if not output_files:
            print("❌ لا توجد فيديوهات في مجلد الإخراج")
            return
        
        print(f"✅ تم العثور على {len(output_files)} فيديو في مجلد الإخراج")
        
        # البحث عن التطابقات في قواعد البيانات
        matches_found = []
        
        for db_path in DB_PATHS:
            if not db_path.exists():
                continue
            
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    db_data = json.load(f)
                
                for filename, new_size in output_files.items():
                    if filename in db_data:
                        old_size = db_data[filename].get('file_size', 0)
                        matches_found.append({
                            'db_path': db_path,
                            'filename': filename,
                            'old_size': old_size,
                            'new_size': new_size
                        })
            except Exception as e:
                print(f"❌ خطأ في قراءة قاعدة البيانات {db_path}: {e}")
        
        if not matches_found:
            print("❌ لم يتم العثور على تطابقات في قواعد البيانات")
            return
        
        # عرض التطابقات
        print(f"\n✅ تم العثور على {len(matches_found)} تطابق:")
        print("\n{:<50} {:<15} {:<15}".format("اسم الملف", "الحجم القديم", "الحجم الجديد"))
        print("-" * 80)
        for match in matches_found[:10]:
            print("{:<50} {:<15} {:<15}".format(
                match['filename'][:47] + "..." if len(match['filename']) > 50 else match['filename'],
                match['old_size'],
                match['new_size']
            ))
        
        if len(matches_found) > 10:
            print(f"... و {len(matches_found) - 10} تطابق آخر")
        
        confirm = input("\n⚠️ هل تريد تحديث الأحجام؟ (نعم/لا): ").strip().lower()
        if confirm not in ['نعم', 'yes', 'y']:
            print("❌ تم إلغاء العملية")
            return
        
        # تحديث قواعد البيانات
        updated_dbs = {}
        for match in matches_found:
            db_path = match['db_path']
            if db_path not in updated_dbs:
                with open(db_path, 'r', encoding='utf-8') as f:
                    updated_dbs[db_path] = json.load(f)
            
            updated_dbs[db_path][match['filename']]['file_size'] = match['new_size']
        
        # حفظ التغييرات
        success_count = 0
        for db_path, db_data in updated_dbs.items():
            try:
                with open(db_path, 'w', encoding='utf-8') as f:
                    json.dump(db_data, f, ensure_ascii=False, indent=4)
                success_count += 1
            except Exception as e:
                print(f"❌ خطأ في حفظ قاعدة البيانات {db_path}: {e}")
        
        print(f"\n✅ تم تحديث {success_count} من {len(updated_dbs)} قاعدة بيانات")
    
    def move_videos_to_original(self):
        """نقل الفيديوهات إلى مجلداتها الأصلية"""
        self.print_header("نقل الفيديوهات إلى مجلداتها الأصلية")
        
        # الحصول على الفيديوهات من مجلد الإخراج
        output_files = {}
        for file in self.output_dir.rglob("*"):
            if file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS:
                output_files[file.name] = file
        
        if not output_files:
            print("❌ لا توجد فيديوهات في مجلد الإخراج")
            return
        
        print(f"✅ تم العثور على {len(output_files)} فيديو في مجلد الإخراج")
        
        # البحث عن التطابقات في المجلدات الأصلية
        matches = []
        for output_name, output_file in output_files.items():
            for original_dir in ORIGINAL_DIRS:
                if not original_dir.exists():
                    continue
                
                for original_file in original_dir.iterdir():
                    if original_file.is_file() and original_file.name == output_name:
                        old_size = original_file.stat().st_size
                        new_size = output_file.stat().st_size
                        if old_size != new_size:
                            matches.append({
                                'output_file': output_file,
                                'original_file': original_file,
                                'old_size': old_size,
                                'new_size': new_size
                            })
                        break
        
        if not matches:
            print("❌ لم يتم العثور على ملفات مطابقة للاستبدال")
            return
        
        # عرض التطابقات
        print(f"\n✅ تم العثور على {len(matches)} فيديو للاستبدال:")
        print("\n{:<50} {:<15} {:<15}".format("اسم الملف", "الحجم القديم", "الحجم الجديد"))
        print("-" * 80)
        for match in matches[:10]:
            print("{:<50} {:<15} {:<15}".format(
                match['output_file'].name[:47] + "..." if len(match['output_file'].name) > 50 else match['output_file'].name,
                match['old_size'],
                match['new_size']
            ))
        
        if len(matches) > 10:
            print(f"... و {len(matches) - 10} فيديو آخر")
        
        confirm = input("\n⚠️ هل تريد استبدال الفيديوهات؟ (نعم/لا): ").strip().lower()
        if confirm not in ['نعم', 'yes', 'y']:
            print("❌ تم إلغاء العملية")
            return
        
        # استبدال الفيديوهات
        success_count = 0
        for match in matches:
            try:
                shutil.copy2(match['output_file'], match['original_file'])
                success_count += 1
            except Exception as e:
                print(f"❌ خطأ في نقل {match['output_file'].name}: {e}")
        
        print(f"\n✅ تم استبدال {success_count} من {len(matches)} فيديو")
    # ========== END: MODIFIED SECTION ==========
    
    # ========== START: MODIFIED SECTION - القائمة الرئيسية ==========
    def run(self):
        """تشغيل السكريبت"""
        while True:
            self.clear_screen()
            self.print_header("Real-ESRGAN - أداة رفع جودة الصور والفيديوهات")
            
            print("القائمة الرئيسية:")
            print("1. رفع جودة الصور")
            print("2. معالجة الصور بعد رفع الجودة")
            print("3. رفع جودة الفيديوهات")
            print("4. معالجة الفيديوهات بعد رفع الجودة")
            print("0. خروج")
            
            choice = self.get_user_choice("\nاختر رقم العملية", ["1", "2", "3", "4", "0"])
            
            if choice == "1":
                self.upscale_images()
            elif choice == "2":
                self.process_upscaled_images()
            elif choice == "3":
                self.upscale_videos()
            elif choice == "4":
                self.process_upscaled_videos()
            elif choice == "0":
                print("\n👋 شكراً لاستخدامك البرنامج!")
                break
            
            if choice != "0":
                input("\n⏎ اضغط Enter للمتابعة...")
    # ========== END: MODIFIED SECTION ==========


def main():
    """الدالة الرئيسية"""
    try:
        automation = ESRGANAutomation()
        automation.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ تم إيقاف البرنامج بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ حدث خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
