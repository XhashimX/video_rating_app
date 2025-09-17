# --- START OF FILE app.py (FINAL VERSION WITH NEW MODIFICATION) ---

from flask import Flask, render_template, jsonify, request, send_file
import os
import subprocess
import json
from pathlib import Path

app = Flask(__name__)

# --- إضافات جديدة ---
# اسم ملف لحفظ الصور المميزة بنجمة
FAVORITES_FILE = "favorites.json"
# اسم ملف لحفظ الملاحظات
NOTES_FILE = "notes.txt"

# اسم ملف الكاش الذي سيحتوي على قائمة صور AI
CACHE_FILE = "image_cache.json" 

# إعدادات المجلدات
DOWNLOAD_FOLDER = "C:/Users/Stark/Download/myhome/video_rating_app/"
TIKTOK_FOLDERS = "C:/Users/Stark/Download/myhome/video_rating_app/NS/TikTok/Elo tik/"

def load_favorites():
    """تحميل قائمة مسارات الصور المميزة من الملف"""
    if not os.path.exists(FAVORITES_FILE):
        return set()
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            # نحن نخزن الآن القاموس الكامل، لذا سنستخرج المسارات
            favorites_data = json.load(f)
            return {fav['relative_path'] for fav in favorites_data}
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

def get_images_from_download():
    """(نسخة سريعة) الحصول على الصور من ملف الكاش مع إضافة حالة التمييز بنجمة"""
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            images = json.load(f)
        
        # إضافة حالة التمييز
        favorite_paths = load_favorites()
        for img in images:
            img['is_favorite'] = img['relative_path'] in favorite_paths
        return images
            
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def get_tiktok_folders():
    """الحصول على قائمة المجلدات، بما في ذلك TikTok ومجلد التحميل"""
    folders = []

    if os.path.exists(DOWNLOAD_FOLDER):
        folders.append({
            'name': 'Download',
            'path': DOWNLOAD_FOLDER
        })

    if os.path.exists(TIKTOK_FOLDERS):
        for item in os.listdir(TIKTOK_FOLDERS):
            item_path = os.path.join(TIKTOK_FOLDERS, item)
            if os.path.isdir(item_path):
                folders.append({
                    'name': item,
                    'path': item_path
                })
    
    return sorted(folders, key=lambda x: x['name'])

### --- التعديل الأول: تعديل الدالة لتقبل اسم المجلد --- ###
def get_png_images_from_folder(folder_path, folder_name=None):
    """
    الحصول على جميع صور PNG من مجلد معين مع إضافة حالة التمييز بنجمة.
    ### <-- إذا كان اسم المجلد هو 'Dib'، فسيتم تضمين صور JPG/JPEG أيضًا.
    """
    images = []
    if not os.path.exists(folder_path):
        return images
    
    favorite_paths = load_favorites()
    
    for file in os.listdir(folder_path):
        is_valid_image = False
        file_lower = file.lower()
        
        ### --- التعديل الثاني: التحقق من اسم المجلد وتحديد الامتدادات المسموح بها --- ###
        if folder_name == 'Dib':
            # إذا كان المجلد هو 'Dib'، اسمح بـ png و jpg و jpeg
            if file_lower.endswith(('.png', '.jpg', '.jpeg')):
                is_valid_image = True
        else:
            # لجميع المجلدات الأخرى، اسمح بـ png فقط
            if file_lower.endswith('.png'):
                is_valid_image = True

        if is_valid_image:
            image_path = os.path.join(folder_path, file)
            try:
                relative_path = str(Path(image_path).relative_to('/storage/emulated/0/'))
                images.append({
                    'name': file,
                    'path': image_path,
                    'relative_path': relative_path,
                    'is_favorite': relative_path in favorite_paths
                })
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
    """عرض محتويات مجلد معين (TikTok أو Download)"""
    if folder_name == 'Download':
        folder_path = DOWNLOAD_FOLDER
    else:
        folder_path = os.path.join(TIKTOK_FOLDERS, folder_name)

    ### --- التعديل الثالث: تمرير اسم المجلد إلى الدالة --- ###
    images = get_png_images_from_folder(folder_path, folder_name=folder_name)
    
    return render_template('folder.html', 
                         folder_name=folder_name,
                         images=images)

# --- المسارات الجديدة ---

@app.route('/favorites')
def view_favorites():
    """صفحة عرض الصور المميزة بنجمة فقط"""
    if not os.path.exists(FAVORITES_FILE):
        images = []
    else:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            # كل الصور هنا مميزة بالفعل، لذا نعطيها القيمة true
            images = json.load(f)
            for img in images:
                img['is_favorite'] = True
    return render_template('favorites.html', favorite_images=images)

@app.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    """API لتمييز أو إلغاء تمييز صورة"""
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

    # تحقق مما إذا كانت الصورة موجودة بالفعل
    found_index = -1
    for i, fav in enumerate(favorites):
        if fav['relative_path'] == image_to_toggle['relative_path']:
            found_index = i
            break

    if found_index != -1:
        # إذا وجدت، قم بإزالتها (إلغاء التمييز)
        favorites.pop(found_index)
        new_status = 'unfavorited'
    else:
        # إذا لم تجد، قم بإضافتها (تمييز)
        favorites.append(image_to_toggle)
        new_status = 'favorited'
    
    # حفظ القائمة المحدثة
    with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(favorites, f, ensure_ascii=False, indent=4)
        
    return jsonify({"status": new_status})

@app.route('/notes', methods=['GET'])
def get_notes():
    """API للحصول على الملاحظات المحفوظة"""
    if not os.path.exists(NOTES_FILE):
        return ""
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError:
        return ""

@app.route('/notes', methods=['POST'])
def save_notes():
    """API لحفظ الملاحظات"""
    try:
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            f.write(request.data.decode('utf-8'))
        return jsonify({"status": "success"})
    except IOError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- نهاية المسارات الجديدة ---

def run_exiftool(image_path):
    """تشغيل أداة exiftool وإرجاع النتائج."""
    try:
        result = subprocess.run(
            ['exiftool', '-json', image_path],
            capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)[0] if result.stdout else {}
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return {}

@app.route('/exif/<path:image_path>')
def get_exif_data(image_path):
    """الحصول على بيانات EXIF لصورة معينة (عند الطلب فقط)"""
    full_path = f"/storage/emulated/0/{image_path}"
    exif_data = run_exiftool(full_path)
    return jsonify(exif_data)

@app.route('/image/<path:image_path>')
def serve_image(image_path):
    """تقديم الصور"""
    full_path = f"/storage/emulated/0/{image_path}"
    if os.path.exists(full_path):
        return send_file(full_path)
    return "Image not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)