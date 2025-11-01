# START: MODIFIED SECTION
import os
import requests
from flask import Flask, request, jsonify
from urllib.parse import urlparse
import hashlib
import re
import glob


# --- 1. الإعدادات ---
DOWNLOAD_FOLDER = r"C:\Users\Stark\Downloads\Civitai_Images"
PROCESSED_LINKS_DB = "processed_links.txt"


# --- الجزء الجديد: إضافة مسارات ملفات التتبع الخاصة بسكريبت المعالجة ---
ORCHESTRATOR_TRACKING_FILES = [
    os.path.join(DOWNLOAD_FOLDER, "processed_anime4k.txt"),
    os.path.join(DOWNLOAD_FOLDER, "processed_esrgan.txt")
]
# ------------------------------------------------------------------


app = Flask(__name__)


# --- 2. وظائف مساعدة ---


def setup():
    try:
        if not os.path.exists(DOWNLOAD_FOLDER):
            os.makedirs(DOWNLOAD_FOLDER)
            print(f"تم إنشاء مجلد التحميلات: {DOWNLOAD_FOLDER}")
        if not os.path.exists(PROCESSED_LINKS_DB):
            with open(PROCESSED_LINKS_DB, "w") as f: pass
            print(f"تم إنشاء ملف قاعدة البيانات: {PROCESSED_LINKS_DB}")
    except Exception as e:
        print(f"❌ خطأ فادح أثناء الإعداد: {e}")
        exit()


def is_link_processed(url):
    """
    التحقق من الرابط الأصلي (بدون sig parameter)
    """
    # إزالة sig parameter قبل المقارنة
    url_without_sig = remove_signature_from_url(url)
    
    with open(PROCESSED_LINKS_DB, "r", encoding='utf-8') as f:
        for line in f:
            stored_url = line.strip()
            stored_url_without_sig = remove_signature_from_url(stored_url)
            if url_without_sig == stored_url_without_sig:
                return True
    return False


def add_link_to_db(url):
    with open(PROCESSED_LINKS_DB, "a", encoding='utf-8') as f:
        f.write(url + "\n")


def remove_signature_from_url(url):
    """
    إزالة sig parameter من URL للمقارنة الصحيحة
    """
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # إزالة sig parameter
        query_params.pop('sig', None)
        
        # إعادة بناء URL بدون sig
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        return new_url
    except:
        return url


def is_already_processed_by_orchestrator(base_filename):
    """
    التحقق مما إذا كان اسم الملف (أو أي ملف بنفس الاسم الأساسي) موجودًا في ملفات التتبع
    """
    for tracker_file in ORCHESTRATOR_TRACKING_FILES:
        try:
            if not os.path.exists(tracker_file):
                continue
            
            with open(tracker_file, 'r', encoding='utf-8') as f:
                processed_files = f.read().splitlines()
                # البحث عن أي ملف يبدأ بنفس الاسم الأساسي
                for processed_file in processed_files:
                    if processed_file.startswith(base_filename):
                        return True
        except Exception as e:
            print(f"⚠️ تحذير: لم يتمكن من قراءة ملف التتبع '{tracker_file}'. الخطأ: {e}")
            continue
            
    return False


def file_exists_with_base_name(base_filename, folder):
    """
    التحقق من وجود ملف بنفس الاسم الأساسي (مع أي لاحقة)
    مثال: إذا كان base_filename = "4ZBSV21CQG0JHX8BP4JN46G9Q0"
    سيجد: 4ZBSV21CQG0JHX8BP4JN46G9Q0_*.jpeg
    """
    try:
        # البحث عن أي ملف يبدأ بنفس الاسم الأساسي
        pattern = os.path.join(folder, f"{base_filename}_*")
        matching_files = glob.glob(pattern)
        
        if matching_files:
            print(f"   🔍 وجدنا ملف مطابق: {os.path.basename(matching_files[0])}")
            return True, matching_files[0]
        return False, None
    except Exception as e:
        print(f"⚠️ خطأ في البحث عن الملفات: {e}")
        return False, None


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def generate_filename(url):
    """
    توليد اسم ملف بدون استخدام sig parameter
    فقط استخدام الاسم الأساسي من URL
    """
    try:
        parsed_url = urlparse(url)
        base_name_part = parsed_url.path.split('/')[-1]
        
        # إزالة الامتداد مؤقتاً
        name, ext = os.path.splitext(base_name_part)
        safe_name = sanitize_filename(name)
        
        # إرجاع الاسم الأساسي فقط (بدون hash من sig)
        return safe_name, ext
        
    except Exception:
        # في حالة الفشل، استخدام hash للـ URL بالكامل (بدون sig)
        url_without_sig = remove_signature_from_url(url)
        hash_name = hashlib.md5(url_without_sig.encode()).hexdigest()
        return hash_name, ".jpg"


# --- 3. نقطة النهاية (API Endpoint) مع الحماية المحسّنة ---


@app.route('/process-image', methods=['POST'])
def process_image_link():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"status": "error", "message": "الرجاء إرسال 'url' في الطلب."}), 400


        image_url = data['url']
        print(f"\n[ 📥 ] تم استقبال رابط جديد: {image_url[:80]}...")


        # --- طبقة الدفاع الأولى: التحقق من الرابط (بدون sig) ---
        if is_link_processed(image_url):
            print("[ 🟡 ] الطبقة 1: الرابط مكرر (بدون النظر للـ sig). تم التجاهل.")
            return jsonify({"status": "skipped", "message": "الرابط تمت معالجته مسبقًا."}), 200


        # توليد اسم الملف الأساسي (بدون hash من sig)
        base_filename, extension = generate_filename(image_url)
        print(f"[ ℹ️ ] الاسم الأساسي للملف: {base_filename}")
        
        
        # --- طبقة الدفاع الثانية: التحقق من وجود ملف بنفس الاسم الأساسي ---
        exists, existing_file = file_exists_with_base_name(base_filename, DOWNLOAD_FOLDER)
        if exists:
            print(f"[ 🟡 ] الطبقة 2: وجدنا ملف بنفس الاسم الأساسي '{os.path.basename(existing_file)}'. تم التجاهل.")
            add_link_to_db(image_url)
            return jsonify({"status": "skipped", "message": f"الملف موجود بالفعل: {os.path.basename(existing_file)}"}), 200


        # --- طبقة الدفاع الثالثة: التحقق من سجلات المعالجة ---
        if is_already_processed_by_orchestrator(base_filename):
            print(f"[ 🟡 ] الطبقة 3: الملف '{base_filename}*' تم تسجيله كـ'معالج' مسبقًا. تم التجاهل.")
            add_link_to_db(image_url)
            return jsonify({"status": "skipped", "message": f"الملف '{base_filename}' تمت معالجته مسبقًا."}), 200


        # إنشاء اسم ملف فريد (نضيف timestamp صغير للحالات النادرة)
        import time
        timestamp_suffix = str(int(time.time() * 1000))[-6:]  # آخر 6 أرقام من timestamp
        final_filename = f"{base_filename}_{timestamp_suffix}{extension}"
        filepath = os.path.join(DOWNLOAD_FOLDER, final_filename)
        
        # التحقق النهائي من عدم وجود الملف
        if os.path.exists(filepath):
            print(f"[ 🟡 ] الملف '{final_filename}' موجود بالفعل. تم التجاهل.")
            add_link_to_db(image_url)
            return jsonify({"status": "skipped", "message": f"الملف '{final_filename}' موجود بالفعل."}), 200


        # إذا تجاوزنا كل الدفاعات، نبدأ التحميل
        print(f"[ ⏳ ] جارٍ تحميل الصورة...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status() 
        
        print(f"[ 💾 ] جارٍ حفظ الملف في: {filepath}")
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"[ ✅ ] تم تحميل وحفظ الصورة بنجاح: {final_filename}")
        add_link_to_db(image_url)
        
        return jsonify({"status": "success", "message": "تم تحميل الصورة بنجاح.", "filename": final_filename}), 201


    except Exception as e:
        print(f"💥💥💥 حدث خطأ فادح داخل الخادم! 💥💥💥")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"حدث خطأ في الخادم: {str(e)}"}), 500


# --- 4. تشغيل الخادم ---
if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=5003, debug=False)
# END: MODIFIED SECTION
