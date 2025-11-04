# START: MODIFIED SECTION

from flask import Flask, render_template, jsonify, request, send_file
import os
import subprocess
import json
from pathlib import Path

app = Flask(__name__)

# --- إعدادات الملفات والمجلدات ---
FAVORITES_FILE = "favorites.json"
NOTES_FILE = "notes.txt"
CACHE_FILE = "image_cache.json" 
DOWNLOAD_FOLDER = "C:/Users/Stark/Download/myhome/video_rating_app/"
TIKTOK_FOLDERS_BASE = "C:/Users/Stark/Download/myhome/video_rating_app/NS/TikTok/Elo tik/"

# --- إضافة جديدة: قائمة بالمجلدات التي تحتوي على صور AI وتحتاج ميزة التصنيف ---
AI_IMAGE_FOLDERS = {'Download', 'Dib'}

def load_favorites():
    """تحميل قائمة مسارات الصور المميزة من الملف"""
    if not os.path.exists(FAVORITES_FILE):
        return set()
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            favorites_data = json.load(f)
            return {fav['relative_path'] for fav in favorites_data}
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

def load_image_cache_as_dict():
    """تحميل الكاش وتحويله إلى قاموس للوصول السريع"""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            images = json.load(f)
            # استخدام مسار الصورة ك مفتاح لسهولة البحث
            return {img['relative_path']: img for img in images}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def get_images_from_download():
    """الحصول على الصور من ملف الكاش مع إضافة حالة التمييز بنجمة"""
    # هذه الدالة تستخدم الكاش مباشرة وهو يحتوي بالفعل على كل صور AI
    cache_dict = load_image_cache_as_dict()
    images = list(cache_dict.values())
    
    favorite_paths = load_favorites()
    for img in images:
        img['is_favorite'] = img['relative_path'] in favorite_paths
    
    # فرز حسب تاريخ التعديل (الذي تم حسابه أثناء المسح)
    images.sort(key=lambda x: x.get('mod_time', 0), reverse=True)
    return images

def get_tiktok_folders():
    """الحصول على قائمة المجلدات في TIKTOK_FOLDERS_BASE"""
    folders = []
    if os.path.exists(TIKTOK_FOLDERS_BASE):
        for item in os.listdir(TIKTOK_FOLDERS_BASE):
            item_path = os.path.join(TIKTOK_FOLDERS_BASE, item)
            if os.path.isdir(item_path):
                folders.append({'name': item})
    return sorted(folders, key=lambda x: x['name'])


def get_images_from_folder(folder_path, folder_name=None):
    """
    الحصول على جميع الصور من مجلد معين وإثرائها ببيانات من الكاش إذا لزم الأمر.
    """
    images = []
    if not os.path.exists(folder_path):
        return images
    
    favorite_paths = load_favorites()
    # تحميل الكاش مرة واحدة لاستخدامه في إثراء البيانات
    cache_dict = load_image_cache_as_dict()
    
    allowed_extensions = ('.png',)
    if folder_name in AI_IMAGE_FOLDERS:
        allowed_extensions = ('.png', '.jpg', '.jpeg')

    for file in os.listdir(folder_path):
        if file.lower().endswith(allowed_extensions):
            image_path = os.path.join(folder_path, file)
            try:
                # استخدام المسار النسبي الصحيح
                relative_path = str(Path(image_path).relative_to(Path(DOWNLOAD_FOLDER).parent.parent)) # تعديل للحصول على مسار نسبي صحيح من الجذر
                
                image_info = {
                    'name': file,
                    'path': image_path,
                    'relative_path': relative_path.replace('\\', '/'),
                    'is_favorite': relative_path.replace('\\', '/') in favorite_paths,
                    'model_name': 'غير معروف' # قيمة افتراضية
                }

                # إذا كان المجلد من مجلدات AI، ابحث عن بيانات الموديل في الكاش
                if folder_name in AI_IMAGE_FOLDERS:
                    cached_data = cache_dict.get(image_info['relative_path'])
                    if cached_data and 'model_name' in cached_data:
                        image_info['model_name'] = cached_data['model_name']

                images.append(image_info)
            except ValueError:
                continue

    images.sort(key=lambda x: os.path.getmtime(x['path']), reverse=True)
    return images


@app.route('/')
def index():
    """الصفحة الرئيسية"""
    download_images = get_images_from_download()
    tiktok_folders = get_tiktok_folders()
    return render_template('index.html', 
                         download_images=download_images,
                         tiktok_folders=tiktok_folders)

@app.route('/folder/<path:folder_name>')
def view_folder(folder_name):
    """عرض محتويات مجلد معين"""
    # تحديد المسار بناءً على اسم المجلد
    if folder_name == 'Download':
        folder_path = DOWNLOAD_FOLDER
    else:
        folder_path = os.path.join(TIKTOK_FOLDERS_BASE, folder_name)

    images = get_images_from_folder(folder_path, folder_name=folder_name)
    
    # تحديد ما إذا كان يجب عرض ميزة التصنيف
    show_classification = folder_name in AI_IMAGE_FOLDERS
    
    return render_template('folder.html', 
                         folder_name=folder_name,
                         images=images,
                         show_classification=show_classification)

@app.route('/favorites')
def view_favorites():
    """صفحة عرض الصور المميزة بنجمة فقط"""
    if not os.path.exists(FAVORITES_FILE):
        images = []
    else:
        try:
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                images = json.load(f)
                for img in images:
                    img['is_favorite'] = True
        except json.JSONDecodeError:
            images = []
            
    images.sort(key=lambda x: x.get('name', '')) # فرز أبجدي بسيط
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
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                favorites = json.load(f)
        except json.JSONDecodeError:
            favorites = []
    found_index = -1
    for i, fav in enumerate(favorites):
        if fav['relative_path'] == image_to_toggle['relative_path']:
            found_index = i
            break
    if found_index != -1:
        favorites.pop(found_index)
        new_status = 'unfavorited'
    else:
        favorites.append(image_to_toggle)
        new_status = 'favorited'
    with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(favorites, f, ensure_ascii=False, indent=4)
    return jsonify({"status": new_status})

@app.route('/notes', methods=['GET'])
def get_notes():
    if not os.path.exists(NOTES_FILE):
        return ""
    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/notes', methods=['POST'])
def save_notes():
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        f.write(request.data.decode('utf-8'))
    return jsonify({"status": "success"})

def run_exiftool(image_path):
    try:
        result = subprocess.run(['exiftool', '-json', image_path], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)[0] if result.stdout else {}
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return {}

@app.route('/exif/<path:image_path>')
def get_exif_data(image_path):
    full_path = Path(DOWNLOAD_FOLDER).parent.parent / image_path # استخدام المسار الصحيح
    exif_data = run_exiftool(str(full_path))
    return jsonify(exif_data)

@app.route('/image/<path:image_path>')
def serve_image(image_path):
    full_path = Path(DOWNLOAD_FOLDER).parent.parent / image_path
    if os.path.exists(full_path):
        return send_file(str(full_path))
    return "Image not found", 404

if __name__ == '__main__':
    # تحديد مسار الجذر للمجلدات بشكل أكثر دقة
    app.config['ROOT_PATH'] = str(Path(DOWNLOAD_FOLDER).parent.parent)
    app.run(host='0.0.0.0', port=5002, debug=True)

# END: MODIFIED SECTION