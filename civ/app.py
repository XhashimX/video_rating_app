# --- START OF FILE app.py (MODIFIED) ---

from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for, flash
import os
import subprocess
import json
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'a_very_secret_key_change_this' 

# --- إعدادات الملفات والمجلدات ---
BASE_DIR = Path("C:/Users/Stark").resolve()
DOWNLOAD_FOLDER = BASE_DIR / "Downloads"
TIKTOK_FOLDERS_BASE = BASE_DIR / "Download/myhome/video_rating_app/NS/TikTok/Elo tik"

FAVORITES_FILE = Path(__file__).parent / "favorites.json"
NOTES_FILE = Path(__file__).parent / "notes.txt"
CACHE_FILE = Path(__file__).parent / "image_cache.json" 

# START: MODIFIED SECTION - إصلاح منطق التحقق من المجلدات
# 1. توحيد كل الأسماء لتكون بحالة أحرف صغيرة (lowercase) لمنع الأخطاء
AI_IMAGE_FOLDERS = {'downloads', 'dib'}
# END: MODIFIED SECTION

def load_favorites():
    if not FAVORITES_FILE.exists(): return set()
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            return {fav['relative_path'] for fav in json.load(f)}
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

def load_image_cache_as_dict():
    if not CACHE_FILE.exists(): return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            images = json.load(f)
            return {img['relative_path']: img for img in images}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def get_images_from_download_cache():
    cache_dict = load_image_cache_as_dict()
    images = list(cache_dict.values())
    favorite_paths = load_favorites()
    for img in images:
        img['is_favorite'] = img['relative_path'] in favorite_paths
    return images

def get_tiktok_folders():
    folders = []
    if TIKTOK_FOLDERS_BASE.is_dir():
        for item in os.listdir(TIKTOK_FOLDERS_BASE):
            if (TIKTOK_FOLDERS_BASE / item).is_dir():
                folders.append({'name': item})
    return sorted(folders, key=lambda x: x['name'])

# START: MODIFIED SECTION - إصلاح دالة جلب الصور وإضافة طباعة للمساعدة في التشخيص
def get_images_from_folder(folder_path: Path, folder_name=None):
    """
    الحصول على جميع الصور من مجلد معين وإثرائها ببيانات من الكاش إذا لزم الأمر.
    """
    # إضافة طباعة لتتبع المسار الذي يتم فحصه
    print(f"🔍 DEBUG: يتم الآن فحص المجلد: {folder_path}")

    images = []
    if not folder_path.is_dir(): 
        print(f"❌ DEBUG: المجلد غير موجود أو ليس مجلداً: {folder_path}")
        return images
    
    favorite_paths = load_favorites()
    cache_dict = load_image_cache_as_dict()
    
    # 2. توسيع قائمة الامتدادات لتشمل صيغاً شائعة أخرى مثل jfif
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.jfif'}

    for file in os.listdir(folder_path):
        file_path = folder_path / file
        # التأكد من أنه ملف وليس مجلداً فرعياً
        if file_path.is_file() and file_path.suffix.lower() in allowed_extensions:
            try:
                relative_path = file_path.relative_to(BASE_DIR).as_posix()
                
                image_info = {
                    'name': file,
                    'relative_path': relative_path,
                    'is_favorite': relative_path in favorite_paths,
                    'model_name': 'غير معروف'
                }
                
                # 3. التأكد من أن التحقق من اسم المجلد يستخدم حالة الأحرف الصغيرة
                current_folder_name = folder_name.lower() if folder_name else ''
                if current_folder_name in AI_IMAGE_FOLDERS:
                    cached_data = cache_dict.get(image_info['relative_path'])
                    if cached_data and 'model_name' in cached_data:
                        image_info['model_name'] = cached_data['model_name']

                images.append(image_info)
            except ValueError:
                # هذا يحدث إذا كان الملف خارج BASE_DIR، تجاهله بأمان
                continue

    # 4. التأكد من أن الفرز يتم بشكل صحيح حتى لو لم يتمكن من الوصول لوقت التعديل
    try:
        images.sort(key=lambda x: (BASE_DIR / x['relative_path']).stat().st_mtime, reverse=True)
    except FileNotFoundError:
        print("⚠️ DEBUG: حدث خطأ أثناء محاولة فرز الصور حسب التاريخ.")

    print(f"👍 DEBUG: تم العثور على {len(images)} صورة في المجلد.")
    return images
# END: MODIFIED SECTION


@app.route('/')
def index():
    download_images = get_images_from_download_cache()
    tiktok_folders = get_tiktok_folders()
    return render_template('index.html', 
                         download_images=download_images,
                         tiktok_folders=tiktok_folders)

@app.route('/browse', methods=['POST'])
def browse_folder():
    custom_path_str = request.form.get('custom_path')
    if not custom_path_str:
        flash("الرجاء إدخال مسار للمجلد.", "error")
        return redirect(url_for('index'))
    
    custom_path = Path(custom_path_str).resolve()
    
    if not custom_path.is_dir() or not custom_path.is_relative_to(BASE_DIR):
        flash(f"خطأ: المسار '{custom_path_str}' غير صالح أو خارج النطاق المسموح به.", "error")
        return redirect(url_for('index'))
        
    folder_name = custom_path.name
    images = get_images_from_folder(custom_path, folder_name)
    
    show_classification = folder_name.lower() in AI_IMAGE_FOLDERS
    
    return render_template('folder.html', 
                         folder_name=f"مسار مخصص: {folder_name}",
                         images=images,
                         show_classification=show_classification)


@app.route('/folder/<path:folder_name>')
def view_folder(folder_name):
    folder_name_lower = folder_name.lower()
    
    # START: MODIFIED SECTION - تبسيط وتصحيح المنطق
    if folder_name_lower == 'downloads':
        folder_path = DOWNLOAD_FOLDER
        # هنا نعرض الصور من الكاش لأنها مفلترة كصور AI
        images = get_images_from_download_cache()
    else:
        folder_path = (TIKTOK_FOLDERS_BASE / folder_name).resolve()
        images = get_images_from_folder(folder_path, folder_name)
    
    show_classification = folder_name_lower in AI_IMAGE_FOLDERS
    # END: MODIFIED SECTION
    
    return render_template('folder.html', 
                         folder_name=folder_name,
                         images=images,
                         show_classification=show_classification)

# ... (باقي المسارات مثل favorites, toggle_favorite, exif, image تبقى كما هي دون تغيير) ...

@app.route('/favorites')
def view_favorites():
    if not FAVORITES_FILE.exists():
        images = []
    else:
        try:
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                images = json.load(f)
                for img in images: img['is_favorite'] = True
        except json.JSONDecodeError:
            images = []
            
    images.sort(key=lambda x: x.get('name', ''))
    return render_template('favorites.html', favorite_images=images)


@app.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    data = request.json
    image_to_toggle = {
        "relative_path": data.get("relative_path"),
        "name": data.get("name"),
        "model_name": data.get("model_name", "غير معروف")
    }
    if not image_to_toggle["relative_path"]:
        return jsonify({"status": "error", "message": "Missing image path"}), 400
    favorites = []
    if FAVORITES_FILE.exists():
        try:
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                favorites = json.load(f)
        except json.JSONDecodeError: pass
    
    found_index = next((i for i, fav in enumerate(favorites) if fav['relative_path'] == image_to_toggle['relative_path']), -1)

    if found_index != -1:
        favorites.pop(found_index)
        new_status = 'unfavorited'
    else:
        favorites.append(image_to_toggle)
        new_status = 'favorited'
    with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(favorites, f, ensure_ascii=False, indent=4)
    return jsonify({"status": new_status})


def run_exiftool(image_path):
    try:
        result = subprocess.run(['exiftool', '-json', str(image_path)], capture_output=True, text=True, check=True, encoding='utf-8')
        return json.loads(result.stdout)[0] if result.stdout else {}
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return {}

@app.route('/exif/<path:relative_path>')
def get_exif_data(relative_path):
    full_path = (BASE_DIR / relative_path).resolve()
    if not full_path.is_relative_to(BASE_DIR):
        return "Access Denied", 403
    exif_data = run_exiftool(full_path)
    return jsonify(exif_data)

@app.route('/image/<path:relative_path>')
def serve_image(relative_path):
    full_path = (BASE_DIR / relative_path).resolve()
    if full_path.exists() and full_path.is_relative_to(BASE_DIR):
        return send_file(str(full_path))
    return "Image not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)

# --- END OF FILE app.py (MODIFIED) ---