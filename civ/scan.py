# --- START OF FILE scan.py (MODIFIED) ---

import os
import subprocess
import json
import shutil
import time
import re
from pathlib import Path

# --- إعدادات ---
DOWNLOAD_FOLDER = "/storage/emulated/0/Download/"
# --- الإضافة الجديدة هنا ---
# تعريف المجلد الإضافي الذي سيتم دمجه
DIB_FOLDER = "/storage/emulated/0/Download/NS/TikTok/Elo tik/Dib/"
CACHE_FILE = "image_cache.json"

def extract_model_name(exif_data):
    """
    يستخرج اسم الموديل من بيانات Civitai الموجودة في EXIF.
    """
    # يمكن أن تكون البيانات في 'UserComment' أو 'Parameters'
    text = exif_data.get('UserComment', '') or exif_data.get('Parameters', '')
    if not text:
        return "غير معروف"

    # البحث عن كتلة "Civitai resources"
    match = re.search(r'Civitai resources: (\[.*?\])', text, re.DOTALL)
    if not match:
        return "غير معروف"

    json_string = match.group(1)
    try:
        resources = json.loads(json_string)
        # البحث عن أول مورد يحتوي على modelName
        for resource in resources:
            if 'modelName' in resource:
                return resource['modelName']
    except json.JSONDecodeError:
        # إذا كان JSON غير صالح، لا يمكننا تحليله
        return "غير معروف"
    
    return "غير معروف"


def find_ai_images_with_exiftool(folder_path):
    """
    يستخدم exiftool للبحث بكفاءة عن الصور التي تحتوي على 'Artist: ai'
    أو 'User Comment'.
    """
    print(f"🔎 البحث عن صور AI في المجلد: {folder_path}")
    
    command = [
        'exiftool',
        '-json',
        # البحث عن صور AI التي تحتوي على معلومات التوليد
        '-if', '($Artist and $Artist =~ /ai/i) or ($UserComment) or ($Parameters)',
        '-ext', 'jpg',
        '-ext', 'jpeg',
        '-ext', 'png',
        folder_path
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stderr:
            print(f"⚠️ رسالة من exiftool: {result.stderr.strip()}")

        if not result.stdout:
            return []
            
        found_images_data = json.loads(result.stdout)
        
        if not isinstance(found_images_data, list):
            found_images_data = [found_images_data]

        return found_images_data

    except FileNotFoundError:
        print("\n❌ خطأ فادح: لم يتم العثور على أداة 'exiftool'.")
        print("يرجى تثبيتها باستخدام الأمر: pkg install exiftool")
        return None
    except json.JSONDecodeError:
        print("❌ خطأ: فشل في تحليل إخراج JSON من exiftool.")
        return []
    except Exception as e:
        print(f"❌ حدث خطأ غير متوقع: {e}")
        return []


def scan_and_cache_images():
    """
    الوظيفة الرئيسية: تفحص الصور، تستخرج البيانات، ترتبها، وتخزن النتائج في ملف كاش.
    """
    start_time = time.time()
    print("--- بدء عملية فحص وتخزين الصور ---")

    if not shutil.which("exiftool"):
        print("\n❌ خطأ فادح: أمر 'exiftool' غير موجود في النظام.")
        print("يرجى تثبيته أولاً. إذا كنت تستخدم Termux، قم بتشغيل: pkg install exiftool")
        return

    # --- بداية التعديل ---
    all_images_data = []

    # 1. فحص مجلد التحميل الرئيسي
    if os.path.isdir(DOWNLOAD_FOLDER):
        download_images = find_ai_images_with_exiftool(DOWNLOAD_FOLDER)
        if download_images is None:
            return # إيقاف التنفيذ إذا لم يتم العثور على exiftool
        all_images_data.extend(download_images)
    else:
        print(f"❌ خطأ: مجلد التحميل '{DOWNLOAD_FOLDER}' غير موجود.")

    # 2. فحص مجلد Dib ودمج النتائج
    if os.path.isdir(DIB_FOLDER):
        dib_images = find_ai_images_with_exiftool(DIB_FOLDER)
        if dib_images:
            all_images_data.extend(dib_images)
    else:
        print(f"❕ ملاحظة: مجلد '{DIB_FOLDER}' غير موجود، سيتم تجاهله.")
    
    image_data_list = all_images_data
    # --- نهاية التعديل ---

    if not image_data_list:
        print("✅ لم يتم العثور على صور AI جديدة في المجلدات المحددة.")
        # تأكد من إنشاء ملف كاش فارغ إذا لم يتم العثور على صور
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("--- انتهت العملية ---")
        return

    print(f"👍 تم العثور على ما مجموعه {len(image_data_list)} صورة AI.")

    images_to_process = []
    for item in image_data_list:
        file_path = item['SourceFile']
        model_name = extract_model_name(item)
        
        relative_path = Path(file_path).relative_to('/storage/emulated/0/')
        images_to_process.append({
            'name': os.path.basename(file_path),
            'relative_path': str(relative_path),
            'mod_time': os.path.getmtime(file_path),
            'model_name': model_name
        })

    images_to_process.sort(key=lambda x: x['mod_time'], reverse=True)
    
    final_image_list = [{k: v for k, v in img.items() if k != 'mod_time'} for img in images_to_process]
    
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_image_list, f, ensure_ascii=False, indent=4)
        print(f"\n💾 تم حفظ القائمة المدمجة للصور بنجاح في '{CACHE_FILE}'.")
    except IOError as e:
        print(f"❌ خطأ: لم يتمكن من كتابة ملف الكاش: {e}")

    end_time = time.time()
    print(f"--- ✅ اكتملت العملية في {end_time - start_time:.2f} ثانية ---")


if __name__ == '__main__':
    scan_and_cache_images()