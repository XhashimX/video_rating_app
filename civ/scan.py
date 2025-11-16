# --- START OF FILE scan.py (MODIFIED) ---

import os
import subprocess
import json
import shutil
import time
import re
from pathlib import Path

# --- إعدادات ---
# START: MODIFIED SECTION
# تحديد المجلد الأساسي للمستخدم. كل المسارات ستكون نسبية لهذا المجلد.
# هذا يجعل الكود أكثر قابلية للنقل وأقل عرضة للخطأ.
BASE_DIR = Path("C:/Users/Stark").resolve()

# تعريف المسارات باستخدام المجلد الأساسي
DOWNLOAD_FOLDER = BASE_DIR / "Downloads"
DIB_FOLDER = BASE_DIR / "Download/myhome/video_rating_app/NS/TikTok/Elo tik/Dib"
CACHE_FILE = Path(__file__).parent / "image_cache.json"  # وضع الكاش بجانب السكربت
# END: MODIFIED SECTION

def extract_model_name(exif_data):
    """
    يستخرج اسم الموديل من بيانات Civitai الموجودة في EXIF.
    """
    text = exif_data.get('UserComment', '') or exif_data.get('Parameters', '')
    if not text:
        return "غير معروف"

    match = re.search(r'Civitai resources: (\[.*?\])', text, re.DOTALL)
    if not match:
        return "غير معروف"

    json_string = match.group(1)
    try:
        resources = json.loads(json_string)
        for resource in resources:
            if 'modelName' in resource:
                return resource['modelName']
    except json.JSONDecodeError:
        return "غير معروف"
    
    return "غير معروف"


def find_ai_images_with_exiftool(folder_path):
    """
    يستخدم exiftool للبحث بكفاءة عن الصور التي تحتوي على 'Artist: ai' أو 'User Comment'.
    """
    print(f"🔎 البحث عن صور AI في المجلد: {folder_path}")
    
    command = [
        'exiftool', '-json',
        '-if', '($Artist and $Artist =~ /ai/i) or ($UserComment) or ($Parameters)',
        '-ext', 'jpg', '-ext', 'jpeg', '-ext', 'png',
        str(folder_path) # تحويل كائن Path إلى نص
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8')
        
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
        print("يرجى تثبيتها والتأكد من أنها في مسار النظام (System PATH).")
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
        print("يرجى تثبيته أولاً.")
        return

    all_images_data = []

    if DOWNLOAD_FOLDER.is_dir():
        download_images = find_ai_images_with_exiftool(DOWNLOAD_FOLDER)
        if download_images is None: return
        all_images_data.extend(download_images)
    else:
        print(f"❌ خطأ: مجلد التحميل '{DOWNLOAD_FOLDER}' غير موجود.")

    if DIB_FOLDER.is_dir():
        dib_images = find_ai_images_with_exiftool(DIB_FOLDER)
        if dib_images:
            all_images_data.extend(dib_images)
    else:
        print(f"❕ ملاحظة: مجلد '{DIB_FOLDER}' غير موجود، سيتم تجاهله.")
    
    if not all_images_data:
        print("✅ لم يتم العثور على صور AI جديدة في المجلدات المحددة.")
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("--- انتهت العملية ---")
        return

    print(f"👍 تم العثور على ما مجموعه {len(all_images_data)} صورة AI.")

    images_to_process = []
    for item in all_images_data:
        file_path = Path(item['SourceFile'])
        model_name = extract_model_name(item)
        
        # START: MODIFIED SECTION
        # حساب المسار النسبي بشكل صحيح وآمن نسبةً إلى المجلد الأساسي
        try:
            relative_path = file_path.relative_to(BASE_DIR)
            images_to_process.append({
                'name': file_path.name,
                'relative_path': str(relative_path).replace('\\', '/'), # توحيد الفواصل
                'mod_time': file_path.stat().st_mtime,
                'model_name': model_name
            })
        except ValueError:
            print(f"⚠️ تحذير: لا يمكن حساب المسار النسبي للملف: {file_path}. سيتم تجاهله.")
            continue
        # END: MODIFIED SECTION

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
# --- END OF FILE scan.py (MODIFIED) ---