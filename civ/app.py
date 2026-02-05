
from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for
import os
import subprocess
import json
from pathlib import Path
import math
import random  # --- جديد: مطلوب للفرز العشوائي
from collections import defaultdict

app = Flask(__name__)

# --- إعدادات المسارات (PC Version) ---
# المجلد الأساسي الذي سننطلق منه لقراءة الملفات
BASE_DIR = Path("C:/Users/Stark").resolve()

# مسار مجلد Dib (للتحقق من وجوده فقط)
DIB_FOLDER_PATH = Path(r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\Dib")

# تحديد مكان ملفات الكاش (بجانب ملف app.py)
SCRIPT_DIR = Path(__file__).parent
MAIN_CACHE_FILE = SCRIPT_DIR / "image_cache.json"
SUBFOLDER_CACHE_FILE = SCRIPT_DIR / "subfolder_cache.json"
FAVORITES_FILE = SCRIPT_DIR / "favorites.json"
NOTES_FILE = SCRIPT_DIR / "notes.txt"

# --- دوال مساعدة (Helpers) ---

def load_favorites_paths():
    """تحميل قائمة مسارات الصور المميزة (relative paths)"""
    if not os.path.exists(FAVORITES_FILE):
        return set()
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            favorites_data = json.load(f)
            return {fav['relative_path'] for fav in favorites_data}
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

def get_images_from_cache(cache_file):
    """قراءة الصور من ملف الكاش"""
    if not os.path.exists(cache_file):
        return []
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def add_favorite_status(images):
    """إضافة علامة (is_favorite) لكل صورة إذا كانت في المفضلة"""
    favorite_paths = load_favorites_paths()
    for img in images:
        img['is_favorite'] = img['relative_path'] in favorite_paths
    return images

def get_tiktok_folders():
    """جلب قائمة مجلدات تيك توك."""
    folders = []
    if DIB_FOLDER_PATH.exists():
        folders.append({'name': 'Dib'})
    
    if os.path.exists(SUBFOLDER_CACHE_FILE):
        try:
            with open(SUBFOLDER_CACHE_FILE, 'r', encoding='utf-8') as f:
                subfolder_data = json.load(f)
                for folder_name in sorted(subfolder_data.keys()):
                    if folder_name != 'Dib':
                        folders.append({'name': folder_name})
        except:
            pass
    return folders

def apply_sorting(images, sort_method):
    """
    (جديد) دالة لتطبيق الفرز على قائمة الصور
    sort_method: 'newest', 'oldest', 'alpha_asc', 'alpha_desc', 'random'
    """
    if not images:
        return []
        
    if sort_method == 'oldest':
        # الفرز حسب التاريخ (تصاعدي)
        return sorted(images, key=lambda x: x.get('mod_time', ''))
    
    elif sort_method == 'alpha_asc':
        # أبجدي (A-Z) حسب اسم الملف
        return sorted(images, key=lambda x: x.get('name', '').lower())
    
    elif sort_method == 'alpha_desc':
        # أبجدي (Z-A) حسب اسم الملف
        return sorted(images, key=lambda x: x.get('name', '').lower(), reverse=True)
    
    elif sort_method == 'random':
        # عشوائي (يتم إنشاء نسخة جديدة حتى لا نعدل القائمة الأصلية)
        shuffled_list = images[:]
        random.shuffle(shuffled_list)
        return shuffled_list
        
    else: # 'newest' (الافتراضي)
        # الفرز حسب التاريخ (تنازلي)
        return sorted(images, key=lambda x: x.get('mod_time', ''), reverse=True)

# --- المسارات (Routes) ---

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 75, type=int)
    sort_by = request.args.get('sort_by', 'newest')  # استلام معامل الفرز

    all_images = get_images_from_cache(MAIN_CACHE_FILE)
    
    # تطبيق الفرز قبل الترقيم
    all_images = apply_sorting(all_images, sort_by)
    
    all_images = add_favorite_status(all_images)
    
    total_images = len(all_images)
    total_pages = math.ceil(total_images / per_page)
    
    if page < 1: page = 1
    if page > total_pages and total_pages > 0: page = total_pages
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated_images = all_images[start:end]

    tiktok_folders = get_tiktok_folders()
    
    return render_template('index.html', 
                         download_images=paginated_images,
                         tiktok_folders=tiktok_folders,
                         page=page,
                         total_pages=total_pages,
                         per_page=per_page,
                         sort_by=sort_by, # نمرر قيمة الفرز الحالية للقالب
                         total_images=total_images)

@app.route('/models')
def list_models():
    """يعرض قائمة بكل الموديلات"""
    main_images = get_images_from_cache(MAIN_CACHE_FILE)
    
    subfolder_data = get_images_from_cache(SUBFOLDER_CACHE_FILE)
    all_subfolder_images = []
    if isinstance(subfolder_data, dict):
        for sublist in subfolder_data.values():
            all_subfolder_images.extend(sublist)
            
    all_images = main_images + all_subfolder_images
    
    models_data = defaultdict(lambda: {'count': 0, 'preview_path': None})
    
    for img in all_images:
        model_name = img.get('model_name', 'غير معروف')
        models_data[model_name]['count'] += 1
        if models_data[model_name]['preview_path'] is None:
            models_data[model_name]['preview_path'] = img.get('relative_path')
            
    sorted_models = sorted(models_data.items(), key=lambda item: item[0])
    
    return render_template('models_list.html', models=sorted_models)


@app.route('/folder/<path:folder_name>')
def view_folder(folder_name):
    """عرض مجلد محدد"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 75, type=int)
    sort_by = request.args.get('sort_by', 'newest') # استلام معامل الفرز
    
    images = []
    
    if folder_name == "Dib":
        all_main_images = get_images_from_cache(MAIN_CACHE_FILE)
        try:
            dib_relative_start = str(DIB_FOLDER_PATH.relative_to(BASE_DIR)).replace('\\', '/')
            images = [img for img in all_main_images if img['relative_path'].startswith(dib_relative_start)]
        except ValueError:
            images = []
    else:
        if os.path.exists(SUBFOLDER_CACHE_FILE):
            with open(SUBFOLDER_CACHE_FILE, 'r', encoding='utf-8') as f:
                all_folders_data = json.load(f)
            images = all_folders_data.get(folder_name, [])

    # تطبيق الفرز
    images = apply_sorting(images, sort_by)
    
    images = add_favorite_status(images)

    total_images = len(images)
    total_pages = math.ceil(total_images / per_page)
    
    if page < 1: page = 1
    if page > total_pages and total_pages > 0: page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    paginated_images = images[start:end]

    return render_template('folder.html', 
                         folder_name=folder_name,
                         images=paginated_images,
                         page=page,
                         total_pages=total_pages,
                         per_page=per_page,
                         sort_by=sort_by, # نمرر قيمة الفرز الحالية
                         total_images=total_images)

@app.route('/favorites')
def view_favorites():
    """عرض المفضلة"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 75, type=int)
    # لا نطبق الفرز هنا عادة لأن المستخدم يريد ترتيب إضافته، لكن يمكن إضافتها لاحقاً إذا أردت
    
    images = get_images_from_cache(FAVORITES_FILE)
    
    for img in images:
        img['is_favorite'] = True
        if 'prompt_data' not in img: img['prompt_data'] = ''

    images.reverse() # الافتراضي: آخر ما تم إضافته يظهر أولاً

    total_images = len(images)
    total_pages = math.ceil(total_images / per_page)
    
    if page < 1: page = 1
    if page > total_pages and total_pages > 0: page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    paginated_images = images[start:end]

    return render_template('favorites.html', 
                           favorite_images=paginated_images,
                           page=page,
                           total_pages=total_pages,
                           per_page=per_page,
                           total_images=total_images)

@app.route('/search')
def search():
    """البحث المطور"""
    query = request.args.get('q', '').strip().lower()
    if not query:
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 75, type=int)
    sort_by = request.args.get('sort_by', 'newest') # استلام معامل الفرز للبحث

    main_images = get_images_from_cache(MAIN_CACHE_FILE)
    subfolder_images_data = get_images_from_cache(SUBFOLDER_CACHE_FILE)
    all_subfolder_images = []
    if isinstance(subfolder_images_data, dict):
        for folder_list in subfolder_images_data.values():
            all_subfolder_images.extend(folder_list)

    all_images = main_images + all_subfolder_images
    
    # --- منطق البحث المطور ---
    # البحث في: البرومبت، اسم الموديل، اسم الملف، المسار
    search_results = []
    for img in all_images:
        in_prompt = query in img.get('prompt_data', '').lower()
        in_model = query in img.get('model_name', '').lower()
        in_name = query in img.get('name', '').lower() # (جديد) البحث في الاسم
        
        # (جديد) البحث في اسم المجلد الأصلي (إذا كان جزءاً من المسار)
        in_path = query in img.get('relative_path', '').lower()
        
        if in_prompt or in_model or in_name or in_path:
            search_results.append(img)
    
    # تطبيق الفرز على النتائج
    search_results = apply_sorting(search_results, sort_by)
    
    search_results = add_favorite_status(search_results)

    total_images = len(search_results)
    total_pages = math.ceil(total_images / per_page)
    
    if page < 1: page = 1
    if page > total_pages and total_pages > 0: page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    paginated_results = search_results[start:end]

    return render_template('search_results.html',
                           query=query,
                           images=paginated_results,
                           page=page,
                           total_pages=total_pages,
                           per_page=per_page,
                           sort_by=sort_by, # نمرر قيمة الفرز
                           total_images=total_images)

@app.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    """إضافة/إزالة من المفضلة"""
    data = request.json
    image_to_toggle = {
        "relative_path": data.get("relative_path"),
        "name": data.get("name"),
        "model_name": data.get("model_name", "غير معروف"), 
        "prompt_data": data.get("prompt_data", ""),
        "source_group": data.get("source_group", "")
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

@app.route('/notes', methods=['GET', 'POST'])
def handle_notes():
    """الملاحظات"""
    if request.method == 'POST':
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            f.write(request.data.decode('utf-8'))
        return jsonify({"status": "success"})
    else:
        if not os.path.exists(NOTES_FILE):
            return ""
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            return f.read()

@app.route('/exif/<path:image_path>')
def get_exif_data(image_path):
    """جلب بيانات EXIF"""
    full_path = BASE_DIR / image_path
    try:
        result = subprocess.run(
            ['exiftool', '-json', str(full_path)], 
            capture_output=True, text=True, check=True, encoding='utf-8', errors='replace'
        )
        return jsonify(json.loads(result.stdout)[0] if result.stdout else {})
    except Exception as e:
        print(f"Error fetching EXIF: {e}")
        return jsonify({})

@app.route('/image/<path:image_path>')
def serve_image(image_path):
    """خدمة الصور"""
    full_path = BASE_DIR / image_path
    if full_path.exists() and full_path.is_file():
        return send_file(full_path)
    return "Image not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)