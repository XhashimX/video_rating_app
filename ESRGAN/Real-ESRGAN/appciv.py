import os
import requests
from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import hashlib
import re
import glob
import time
from io import BytesIO  # للتحميل في الذاكرة


# --- 1. الإعدادات ---
DOWNLOAD_FOLDER = r"C:\Users\Stark\Downloads\Civitai_Images"
PROCESSED_LINKS_DB = "processed_links.txt"
MIN_FILE_SIZE = 50 * 1024  # 50 كيلوبايت بالبايت


ORCHESTRATOR_TRACKING_FILES = [
    os.path.join(DOWNLOAD_FOLDER, "processed_anime4k.txt"),
    os.path.join(DOWNLOAD_FOLDER, "processed_esrgan.txt")
]

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
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query_params.pop('sig', None)
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
    التحقق مما إذا كان اسم الملف موجودًا في ملفات التتبع
    """
    for tracker_file in ORCHESTRATOR_TRACKING_FILES:
        try:
            if not os.path.exists(tracker_file):
                continue
            
            with open(tracker_file, 'r', encoding='utf-8') as f:
                processed_files = f.read().splitlines()
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
    """
    try:
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
    توليد اسم الملف من الرابط
    """
    try:
        parsed_url = urlparse(url)
        base_name_part = parsed_url.path.split('/')[-1]
        name, ext = os.path.splitext(base_name_part)
        safe_name = sanitize_filename(name)
        return safe_name, ext
    except Exception:
        url_without_sig = remove_signature_from_url(url)
        hash_name = hashlib.md5(url_without_sig.encode()).hexdigest()
        return hash_name, ".jpg"


# --- الطبقة الرابعة الجديدة: التحقق من حجم الملف ---
def check_file_size_via_head(url, headers):
    """
    التحقق من حجم الملف باستخدام HEAD request فقط
    يرجع: (is_valid, file_size_bytes)
    """
    try:
        print(f"[ 📏 ] الطبقة 4: التحقق من حجم الملف عبر HEAD request...")
        head_response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        
        content_length = head_response.headers.get('Content-Length')
        
        if content_length:
            file_size = int(content_length)
            file_size_kb = file_size / 1024
            print(f"   📊 حجم الملف: {file_size_kb:.2f} KB")
            
            if file_size < MIN_FILE_SIZE:
                print(f"   🚫 الملف صغير جداً (< 50 KB). سيتم تخطيه دون حفظ الرابط.")
                return False, file_size
            else:
                print(f"   ✅ حجم الملف مقبول (>= 50 KB).")
                return True, file_size
        else:
            print(f"   ⚠️ لم يتوفر Content-Length في HEAD response.")
            return None, None  # سنحتاج للتحميل في الذاكرة
            
    except Exception as e:
        print(f"   ⚠️ فشل HEAD request: {e}.")
        return None, None


def download_to_memory_and_check(url, headers):
    """
    تحميل الملف إلى الذاكرة (BytesIO) والتحقق من حجمه قبل الكتابة
    يرجع: (is_valid, bytes_data, file_size)
    """
    try:
        print(f"[ 💾 ] تحميل الملف إلى الذاكرة للتحقق من الحجم...")
        
        # التحميل باستخدام stream للكفاءة
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # إنشاء BytesIO في الذاكرة
        memory_file = BytesIO()
        
        # تحميل البيانات على شكل chunks
        for chunk in response.iter_content(chunk_size=8192):
            memory_file.write(chunk)
        
        # الحصول على حجم البيانات
        file_size = memory_file.tell()
        file_size_kb = file_size / 1024
        print(f"   📊 حجم الملف المحمل في الذاكرة: {file_size_kb:.2f} KB")
        
        # التحقق من الحجم
        if file_size < MIN_FILE_SIZE:
            print(f"   🚫 الملف صغير جداً (< 50 KB). سيتم تجاهله دون حفظ.")
            memory_file.close()
            return False, None, file_size
        else:
            print(f"   ✅ حجم الملف مقبول. جاهز للحفظ في المجلد.")
            # إعادة المؤشر إلى البداية لقراءة البيانات لاحقاً
            memory_file.seek(0)
            return True, memory_file.getvalue(), file_size
            
    except Exception as e:
        print(f"   ❌ خطأ أثناء التحميل في الذاكرة: {e}")
        raise


# --- 3. نقطة النهاية (API Endpoint) ---

@app.route('/process-image', methods=['POST'])
def process_image_link():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"status": "error", "message": "الرجاء إرسال 'url' في الطلب."}), 400

        image_url = data['url']
        print(f"\n[ 📥 ] تم استقبال رابط جديد: {image_url[:80]}...")

        # --- طبقة الدفاع الأولى: التحقق من الرابط ---
        if is_link_processed(image_url):
            print("[ 🟡 ] الطبقة 1: الرابط مكرر. تم التجاهل.")
            return jsonify({"status": "skipped", "message": "الرابط تمت معالجته مسبقًا."}), 200

        # --- توليد اسم الملف ---
        base_filename, extension = None, None
        parsed_url = urlparse(image_url)

        if 'view' in parsed_url.path and 'filename=' in parsed_url.query:
            print("[ ℹ️ ] تم اكتشاف رابط من نوع ComfyUI/Pinggy.")
            query_params = parse_qs(parsed_url.query)
            filename_from_query = query_params.get('filename', [None])[0]
            if filename_from_query:
                base_filename, extension = os.path.splitext(filename_from_query)
        
        if base_filename is None:
            print("[ ℹ️ ] استخدام المنطق الأصلي (Civitai).")
            base_filename, extension = generate_filename(image_url)
        
        print(f"[ ℹ️ ] الاسم الأساسي للملف: {base_filename}")

        # --- طبقة الدفاع الثانية: التحقق من وجود ملف بنفس الاسم ---
        exists, existing_file = file_exists_with_base_name(base_filename, DOWNLOAD_FOLDER)
        if exists:
            print(f"[ 🟡 ] الطبقة 2: وجدنا ملف مطابق. تم التجاهل.")
            add_link_to_db(image_url)
            return jsonify({"status": "skipped", "message": f"الملف موجود: {os.path.basename(existing_file)}"}), 200

        # --- طبقة الدفاع الثالثة: التحقق من سجلات المعالجة ---
        if is_already_processed_by_orchestrator(base_filename):
            print(f"[ 🟡 ] الطبقة 3: الملف معالج مسبقاً. تم التجاهل.")
            add_link_to_db(image_url)
            return jsonify({"status": "skipped", "message": f"الملف '{base_filename}' معالج مسبقاً."}), 200

        # --- طبقة الدفاع الرابعة: التحقق من حجم الملف ---
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # المحاولة 1: HEAD request أولاً
        is_size_valid, file_size = check_file_size_via_head(image_url, headers)
        
        if is_size_valid is False:
            # الملف صغير جداً - نتخطاه دون حفظ الرابط
            return jsonify({
                "status": "skipped_size", 
                "message": f"الملف صغير جداً ({file_size/1024:.2f} KB < 50 KB). تم التخطي دون حفظ الرابط."
            }), 200
        
        # المحاولة 2: إذا لم نستطع التحقق عبر HEAD، نحمل في الذاكرة
        image_bytes = None
        if is_size_valid is None:
            print(f"[ 🔄 ] HEAD request لم يوفر معلومات كافية. سيتم التحميل في الذاكرة...")
            is_size_valid, image_bytes, file_size = download_to_memory_and_check(image_url, headers)
            
            if not is_size_valid:
                # الملف صغير جداً - تم رفضه دون حفظ الرابط
                return jsonify({
                    "status": "skipped_size", 
                    "message": f"الملف صغير جداً ({file_size/1024:.2f} KB < 50 KB). تم التخطي دون حفظ الرابط."
                }), 200

        # --- الآن نحن واثقون أن الملف مقبول: احفظه في المجلد ---
        timestamp_suffix = str(int(time.time() * 1000))[-6:]
        final_filename = f"{base_filename}_{timestamp_suffix}{extension}"
        filepath = os.path.join(DOWNLOAD_FOLDER, final_filename)
        
        # التحقق الأخير من عدم وجود الملف
        if os.path.exists(filepath):
            print(f"[ 🟡 ] الملف '{final_filename}' موجود. تم التجاهل.")
            add_link_to_db(image_url)
            return jsonify({"status": "skipped", "message": f"الملف '{final_filename}' موجود."}), 200

        print(f"[ 💾 ] جارٍ حفظ الملف في: {filepath}")
        
        # إذا كان لدينا البيانات في الذاكرة، احفظها مباشرة
        if image_bytes:
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            print(f"[ ✅ ] تم حفظ الملف من الذاكرة: {final_filename}")
        else:
            # إذا تحققنا عبر HEAD، حمّل الملف الآن
            print(f"[ ⏳ ] جارٍ تحميل الصورة...")
            response = requests.get(image_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[ ✅ ] تم تحميل وحفظ الصورة: {final_filename}")
        
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
