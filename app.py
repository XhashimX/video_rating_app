import json
import sys
import os
import socket  # START: MODIFIED SECTION
from flask_session import Session
from flask import jsonify
import time 
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask import send_from_directory
from utilities.config import SECRET_KEY, BACKUP_FOLDER
from utilities.video_analyzer import update_names_analysis, analyze_names_data, get_video_display_name
from utilities.data_manager import load_data, save_data
from utilities import tournaments_manager
from utilities.file_manager import update_video_list, update_file_names, top_videos as render_top_videos, rename_all_videos as rename_all_videos_function
from utilities.helpers import video_handler
from utilities.routes import init_routes
from utilities import advanced_tools
from utilities.video_filter import get_deletion_candidates, load_skipped_videos, save_skipped_videos
# --- تعديل الاستيراد هنا ---
from utilities.video_selector import select_winner as select_winner_function, choose_videos_function
# --- نهاية التعديل ---
from utilities.analyze import analyze_data, Color, save_analysis_to_file
from utilities.data_manager import create_backup
from utilities import tour
from utilities.elo_calculator import update_ratings_multiple



# 1. تعريف المسار الأساسي للمشروع (BASE_DIR)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# بعد تعريف BASE_DIR، أضف هذا السطر
UPSCALED_MEDIA_DIR = os.path.join(BASE_DIR, "upscaled_media")
app = Flask(__name__, template_folder='templates',
            static_folder='static')  # Added static folder
app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)  # هذا السطر ضروري لتفعيل Flask-Session
init_routes(app)

JSON_FOLDER = os.path.join("utilities")
STATUS_FOLDER = os.path.join("utilities", "status")


# 2. استخدام المسار الأساسي لتعريف مسارات المجلدات بشكل موثوق
JSON_FOLDER = os.path.join(BASE_DIR, "utilities")
STATUS_FOLDER = os.path.join(BASE_DIR, "utilities", "status")

# 3. تحديث المسار المطلق القديم ليصبح ديناميكياً أيضاً
PROCESSED_VIDEOS_FILE = os.path.join(BASE_DIR, 'utilities', 'processed_videos.json')

def load_processed_videos_data():
    """
    Loads data from the processed videos JSON file and returns a dictionary
    mapping file size to video data.
    """
    print(f"\n--- Attempting to load processed videos data from {PROCESSED_VIDEOS_FILE} ---") # DEBUG
    processed_data = {}
    if not os.path.exists(PROCESSED_VIDEOS_FILE):
        print(f"WARNING: Processed videos file not found at {PROCESSED_VIDEOS_FILE}") # DEBUG
        return processed_data # Return empty dict if file doesn't exist

    try:
        with open(PROCESSED_VIDEOS_FILE, 'r', encoding='utf-8') as f:
            # Read the content first to handle potential empty file gracefully
            content = f.read().strip()
            if not content:
                print(f"WARNING: Processed videos file is empty: {PROCESSED_VIDEOS_FILE}") # DEBUG
                return processed_data # Return empty dict if file is empty

            data_list = json.loads(content)

        if not isinstance(data_list, list):
             print(f"ERROR: Processed videos data is not a list in {PROCESSED_VIDEOS_FILE}") # DEBUG
             return {} # Return empty dict if format is wrong

        # Create a dictionary mapping file_size to the video entry
        for entry in data_list:
            if isinstance(entry, dict) and 'file_size' in entry and 'total_weight' in entry and 'video_name' in entry:
                # Use file_size as the key. Handle potential duplicates if necessary,
                # but assuming file sizes are unique for different videos.
                # Store the entry itself or specific relevant fields like weight.
                processed_data[entry['file_size']] = {
                    'total_weight': entry['total_weight'],
                    'video_name': entry.get('video_name', '') # Include name for potential future use
                }
            else:
                 print(f"WARNING: Skipping invalid entry in {PROCESSED_VIDEOS_FILE}: {entry}") # DEBUG


        print(f"Successfully loaded {len(processed_data)} entries from processed videos data.") # DEBUG
        return processed_data

    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode JSON from {PROCESSED_VIDEOS_FILE}: {e}") # DEBUG
        # traceback.print_exc() # Uncomment for detailed traceback during debugging
        return {} # Return empty dict on JSON error
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while loading processed videos data: {e}") # DEBUG
        # traceback.print_exc() # Uncomment for detailed traceback during debugging
        return {} # Return empty dict on other errors



# تعيين مدة كاش سنة للملفات الثابتة
@app.after_request
def add_header(response):
    # نريد فرض الكاش لكل الملفات الثابتة من نوع CSS, JS, صور, خطوط
    if request.path.startswith('/static/'):
        if response.content_type and any(t in response.content_type for t in ['text/css', 'application/javascript', 'image/', 'font/']):
            response.headers['Cache-Control'] = 'public, max-age=31536000'
    return response


@app.route('/json_analysis', methods=['GET', 'POST'])
def json_analysis():
    analysis_results = None
    selected_file = None
    json_files = [f for f in os.listdir(JSON_FOLDER) if f.endswith('.json')]
    comparison_results = None
    total_files = len(json_files)
    status_files = [f for f in os.listdir(STATUS_FOLDER) if f.endswith('.txt')]
    total_analyzed_files = len(status_files)

    if request.method == 'POST':
        if 'analyze_file' in request.form:
            selected_file = request.form.get('json_file')
            if selected_file:
                try:
                    file_path = os.path.join(JSON_FOLDER, selected_file)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    analysis_results = analyze_data(data)
                    session['analysis_results'] = analysis_results
                    session['selected_file'] = selected_file
                    output_file = save_analysis_to_file(
                        analysis_results, selected_file, STATUS_FOLDER)
                    flash('تم التحليل بنجاح!', 'success')
                except Exception as e:
                    flash(f'خطأ: {str(e)}', 'error')
        elif 'compare_files' in request.form:
            files = [f for f in os.listdir(
                STATUS_FOLDER) if f.endswith(".txt")]
            if len(files) < 2:
                flash("لا يوجد ملفات كافية للمقارنة في مجلد Status", "error")
            else:
                file1 = request.form.get('file1')
                file2 = request.form.get('file2')
                if file1 and file2:
                    file1_path = os.path.join(STATUS_FOLDER, file1)
                    file2_path = os.path.join(STATUS_FOLDER, file2)
                    try:
                        with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2:
                            content1 = f1.read()
                            content2 = f2.read()
                        comparison_results = []
                        for line1, line2 in zip(
                                content1.splitlines(), content2.splitlines()):
                            if line1 != line2:
                                comparison_results.append({
                                    'file1': f"{file1}: {line1}",
                                    'file2': f"{file2}: {line2}"
                                })
                        session['comparison_results'] = comparison_results
                        flash('تمت المقارنة بنجاح!', 'success')
                    except Exception as e:
                        flash(f'خطأ في المقارنة: {str(e)}', 'error')
                else:
                    flash('الرجاء اختيار ملفين للمقارنة', 'error')

    analysis_results = session.get('analysis_results')
    selected_file = session.get('selected_file')
    comparison_results = session.get('comparison_results')
    status_files = [f for f in os.listdir(STATUS_FOLDER) if f.endswith('.txt')]

    return render_template('json_analysis.html',
                           analysis_results=analysis_results,
                           json_files=json_files,
                           selected_file=selected_file,
                           status_files=status_files,
                           comparison_results=comparison_results,
                           total_files=total_files,
                           total_analyzed_files=total_analyzed_files)


@app.route('/')
def index():
    selected_folder = session.get('selected_folder')
    return render_template('index.html', selected_folder=selected_folder)
# ... (بقية كود app.py قبل هذا الجزء) ...

# START: MODIFIED SECTION - أضف هذه الدالة الجديدة بالكامل في app.py

@app.route('/filter_delete', methods=['GET', 'POST'])
def filter_and_delete():
    """
    يعرض صفحة فلترة وحذف الفيديوهات ويعالج عمليات الحذف والتخطي.
    """
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً للوصول لهذه الصفحة.", "warning")
        return redirect(url_for('index'))

    # تحميل بيانات الفيديوهات الحالية
    all_videos_data = load_data()
    if not all_videos_data:
        flash("لم يتم العثور على بيانات فيديوهات للمجلد المحدد.", "danger")
        return redirect(url_for('index'))

    # الحصول على قائمة الفيديوهات المرشحة للحذف (بعد استبعاد المتخطاة)
    candidates = get_deletion_candidates(all_videos_data)
    total_candidates_count = len(candidates)
    
    # تحديد حجم الدفعة (عدد الفيديوهات المعروضة في كل صفحة)
    batch_size = 6 # يمكنك تغيير هذا الرقم لعرض 3 أو 6 أو 9...

    if request.method == 'POST':
        action = request.form.get('action')
        page = int(request.form.get('page', 1))
        
        # فيديوهات تم عرضها في الدفعة الحالية
        videos_in_batch = request.form.getlist('videos_in_batch')
        
        if action == 'delete':
            videos_to_delete = request.form.getlist('videos_to_delete')
            videos_to_skip = [v for v in videos_in_batch if v not in videos_to_delete]
            
            deleted_count = 0
            skipped_count = 0
            
            # --- منطق الحذف ---
            if videos_to_delete:
                selected_folder = session.get('selected_folder')
                for video_name in videos_to_delete:
                    # حذف من قاموس البيانات
                    if video_name in all_videos_data:
                        del all_videos_data[video_name]
                    
                    # حذف الملف الفعلي من المجلد
                    try:
                        file_path = os.path.join(selected_folder, video_name)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            deleted_count += 1
                    except Exception as e:
                        print(f"Error deleting file {video_name}: {e}")
                
                # حفظ البيانات بعد الحذف
                save_data(all_videos_data)
            
            # --- منطق التخطي ---
            if videos_to_skip:
                skipped_videos_set = load_skipped_videos()
                for video_name in videos_to_skip:
                    # نحتاج حجم الملف للتخطي
                    file_size = request.form.get(f'filesize_{video_name}')
                    if file_size:
                        skipped_videos_set.add(int(file_size))
                        skipped_count += 1
                save_skipped_videos(skipped_videos_set)

            flash(f"تم حذف {deleted_count} فيديوهات وتخطي {skipped_count} بنجاح.", "success")
            # أعد التوجيه إلى نفس الصفحة (GET) لإظهار الدفعة التالية من القائمة المحدثة
            return redirect(url_for('filter_and_delete'))

        elif action == 'skip':
            # تخطي كل الفيديوهات في الدفعة الحالية
            skipped_videos_set = load_skipped_videos()
            skipped_count = 0
            for video_name in videos_in_batch:
                file_size = request.form.get(f'filesize_{video_name}')
                if file_size:
                    skipped_videos_set.add(int(file_size))
                    skipped_count += 1
            save_skipped_videos(skipped_videos_set)
            flash(f"تم تخطي {skipped_count} فيديوهات. عرض الدفعة التالية.", "info")
            # أعد التوجيه إلى نفس الصفحة (GET) لإظهار الدفعة التالية من القائمة المحدثة
            return redirect(url_for('filter_and_delete'))

    # --- منطق العرض (GET) ---
    page = int(request.args.get('page', 1))
    start_index = (page - 1) * batch_size
    end_index = start_index + batch_size
    
    # الحصول على الدفعة الحالية من الفيديوهات لعرضها
    candidates_batch = candidates[start_index:end_index]
    
    return render_template(
        'filter_and_delete.html',
        candidates_batch=candidates_batch,
        page=page,
        total_candidates=total_candidates_count
    )

# END: MODIFIED SECTION




@app.route('/names_analysis')
def names_analysis_page():
    # هنا يتم استدعاء دالة analyze_names_data لتحضير البيانات للعرض
    # لم نعد نمرر main_data هنا لأن analyze_names_data ستقوم بتحميلها بنفسها
    analysis_results = analyze_names_data()
    # main_data لم تعد ضرورية لـ names_analysis_page مباشرة، يمكن إزالتها إذا لم تستخدم في القالب
    # main_data = load_data() # هذه لم تعد ضرورية هنا لـ names_analysis_page
    return render_template('names_analysis.html', analysis_results=analysis_results)

# --- استبدل الدالة الحالية بهذه النسخة المعدلة في app.py ---

# START: MODIFIED SECTION
# --- START OF FILE app.py (Modified Section) ---

# ... (الاستيرادات السابقة)

# ... (الكود السابق)

# START: MODIFIED SECTION - تعديل دالة regroup_competitions
@app.route('/regroup_competitions', methods=['POST'])
def regroup_competitions():
    """
    يعيد تجميع الفيديوهات داخل ملف بطولة محدد وفقًا لحجم جديد للمسابقة،
    مع محاولة تجنب وضع فيديوهات لنفس الاسم (name) في نفس المسابقة.
    """
    from flask import jsonify
    import json
    # استيراد دالة تحميل البيانات الرئيسية
    from utilities.data_manager import load_data

    try:
        data = request.get_json()
        filename = data.get('filename')
        new_num_videos = data.get('new_num_videos')

        # 1. التحقق من المدخلات
        if not filename or '..' in filename or filename.startswith('/'):
            return jsonify({'success': False, 'message': 'اسم ملف غير صالح.'}), 400
        
        if not isinstance(new_num_videos, int) or new_num_videos < 2:
            return jsonify({'success': False, 'message': 'عدد الفيديوهات يجب أن يكون رقمًا صحيحًا أكبر من أو يساوي 2.'}), 400

        # 2. بناء المسار الآمن للملف
        file_path = os.path.join(JSON_FOLDER, filename)
        if not os.path.abspath(file_path).startswith(os.path.abspath(JSON_FOLDER)):
            return jsonify({'success': False, 'message': 'محاولة الوصول إلى مسار غير مسموح به.'}), 403

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'الملف غير موجود.'}), 404

        # 3. قراءة بيانات البطولة والبيانات الرئيسية
        with open(file_path, 'r', encoding='utf-8') as f:
            competitions = json.load(f)
        
        # تحميل بيانات الفيديو الرئيسية للحصول على الأسماء والتقييمات
        main_data = load_data()
        if not main_data:
            return jsonify({'success': False, 'message': 'فشل في تحميل ملف البيانات الرئيسي (data.json).'}), 500

        if not competitions or not isinstance(competitions, list):
            return jsonify({'success': False, 'message': 'الملف فارغ أو لا يحتوي على قائمة مسابقات صالحة.'}), 400

        template = competitions[0].copy()

        # 4. جمع كل الفيديوهات في قائمة واحدة فريدة
        all_videos = []
        for comp in competitions:
            if 'videos' in comp and isinstance(comp.get('videos'), list):
                all_videos.extend(comp['videos'])
        
        # إزالة التكرار مع الحفاظ على الترتيب الأصلي
        unique_videos = list(dict.fromkeys(all_videos))
        
        # 5. التوزيع الذكي (Smart Distribution Logic)
        distributed_groups = []
        
        # تحويل القائمة إلى قائمة قابلة للتعديل (نسخة) للعمل عليها
        remaining_videos = unique_videos[:]
        
        while remaining_videos:
            current_group = []
            names_in_current_group = set()
            
            # نأخذ أول فيديو دائماً لبدء المجموعة (للحفاظ على الترتيب العام)
            first_video = remaining_videos.pop(0)
            current_group.append(first_video)
            
            # استخراج اسم صاحب الفيديو الأول
            first_name = main_data.get(first_video, {}).get('name', 'Unknown')
            names_in_current_group.add(first_name)
            
            # محاولة ملء باقي المقاعد في المجموعة الحالية
            while len(current_group) < new_num_videos and remaining_videos:
                found_match = False
                
                # البحث في القائمة المتبقية عن فيديو لا يتعارض اسمه مع الموجودين في المجموعة
                for i, candidate_video in enumerate(remaining_videos):
                    candidate_name = main_data.get(candidate_video, {}).get('name', 'Unknown')
                    
                    # إذا كان الاسم غير موجود في المجموعة الحالية، نضيفه
                    if candidate_name not in names_in_current_group:
                        current_group.append(candidate_video)
                        names_in_current_group.add(candidate_name)
                        remaining_videos.pop(i) # إزالة من القائمة المتبقية
                        found_match = True
                        break # ننتقل للبحث عن المقعد التالي
                
                # إذا لم نجد أي فيديو مناسب (كل المتبقين أسماؤهم مكررة في هذه المجموعة)
                if not found_match:
                    # نضطر لأخذ الفيديو التالي في القائمة بغض النظر عن الاسم (المرونة)
                    forced_video = remaining_videos.pop(0)
                    current_group.append(forced_video)
                    # لا داعي لإضافة الاسم للمجموعة لأنه موجود أصلاً
            
            # إضافة المجموعة المكتملة (أو الجزئیة في آخر دورة) إلى القائمة النهائية
            if current_group:
                 distributed_groups.append(current_group)

        # 6. إنشاء هيكل JSON الجديد للمسابقات
        new_competitions = []
        for chunk in distributed_groups:
            # نتأكد أن المجموعة ممتلئة بالعدد المطلوب إلا ربما الأخيرة
            # إذا أردت التعامل بصرامة مع المجموعات غير المكتملة، يمكن إضافة منطق هنا
            # حالياً سنضيفها كما هي
            
            new_comp = template.copy()
            new_comp['videos'] = chunk
            new_comp['num_videos'] = new_num_videos # قد يكون العدد الفعلي أقل في آخر مجموعة، لكن نترك الإعداد كما هو
            
            # إنشاء قائمة التقييمات الجديدة لهذه المسابقة
            ratings_for_chunk = []
            file_sizes_for_chunk = [] # إضافة أحجام الملفات أيضاً لتحديثها
            
            for video_name in chunk:
                video_info = main_data.get(video_name, {})
                # جلب التقييم
                rating = video_info.get('rating', 1000)
                ratings_for_chunk.append(rating)
                # جلب حجم الملف
                file_size = video_info.get('file_size', 0)
                file_sizes_for_chunk.append(file_size)
            
            # إضافة القوائم المحدثة
            new_comp['rating'] = ratings_for_chunk
            new_comp['file_size'] = file_sizes_for_chunk # تحديث file_size
            
            new_competitions.append(new_comp)

        # 7. إعادة كتابة الملف الأصلي
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(new_competitions, f, indent=4, ensure_ascii=False)

        old_count = len(competitions)
        new_count = len(new_competitions)
        message = f"تمت إعادة تجميع {old_count} مسابقة إلى {new_count} مسابقة بنجاح! (مع توزيع ذكي للأسماء)"
        flash(message, "success")
        return jsonify({'success': True, 'message': message})

    except json.JSONDecodeError:
        return jsonify({'success': False, 'message': 'فشل في قراءة الملف، تأكد من أنه ملف JSON صالح.'}), 500
    except Exception as e:
        print(f"Error in regroup_competitions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'حدث خطأ في الخادم: {e}'}), 500
# END: MODIFIED SECTION

# ... (باقي الكود)



# START: ADDED SECTION - أضف هذه الدالة الجديدة بالكامل في app.py
def create_ranking_map(data):
    """
    تأخذ بيانات الفيديوهات، ترتبها حسب التقييم، وتُرجع قاموسًا
    يربط اسم كل فيديو بترتيبه الرقمي.
    مثال: {'video_A.mp4': 1, 'video_C.mp4': 2, ...}
    """
    if not data:
        return {}

    # 1. تحويل القاموس إلى قائمة من tuples ليسهل ترتيبها
    #    نستخدم .get('rating', 1000) لضمان وجود قيمة افتراضية في حال عدم وجود مفتاح التقييم
    sorted_videos = sorted(data.items(), key=lambda item: item[1].get('rating', 1000), reverse=True)

    # 2. إنشاء "خريطة الترتيب"
    #    نمر على القائمة المرتبة ونعين لكل فيديو ترتيبه (الفهرس + 1)
    ranking_map = {video_name: rank + 1 for rank, (video_name, video_info) in enumerate(sorted_videos)}

    return ranking_map
# END: ADDED SECTION



@app.route('/delete_tournament_file', methods=['POST'])
def delete_tournament_file():
    """
    مسار API لحذف ملف بطولة محدد من مجلد utilities.
    """
    from flask import jsonify # تأكد من استيراد jsonify إذا لم يكن مستورداً

    try:
        data = request.get_json()
        filename = data.get('filename')

        # 1. التحقق الأمني: تأكد من أن اسم الملف صالح
        if not filename or '..' in filename or filename.startswith('/'):
            return jsonify({'success': False, 'message': 'اسم ملف غير صالح.'}), 400

        # 2. إنشاء المسار الكامل والتحقق من أنه داخل المجلد المسموح به
        file_path = os.path.join(JSON_FOLDER, filename)
        if not os.path.abspath(file_path).startswith(os.path.abspath(JSON_FOLDER)):
            return jsonify({'success': False, 'message': 'محاولة الوصول إلى مسار غير مسموح به.'}), 403

        # 3. التحقق من وجود الملف وحذفه
        if os.path.exists(file_path):
            os.remove(file_path)
            flash(f"تم حذف ملف البطولة '{filename}' بنجاح.", "success")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'الملف غير موجود.'}), 404

    except Exception as e:
        print(f"Error deleting tournament file: {e}") # DEBUG
        return jsonify({'success': False, 'message': f'حدث خطأ في الخادم: {e}'}), 500
# END: MODIFIED SECTION





# START: MODIFIED SECTION
@app.route('/advanced_tools')
def advanced_tools_page():
    """
    يعرض صفحة الأدوات المتقدمة ويمرر إليها قائمة بالملفات المتاحة.
    """
    try:
        # JSON_FOLDER تم تعريفه في أعلى الملف بالفعل
        all_files = os.listdir(JSON_FOLDER)
        
        # القائمة الأولى: ملفات JSON فقط لأداة "صنع المسابقات"
        database_files = [f for f in all_files if f.endswith('.json')]
        
        # القائمة الثانية: ملفات JSON و TXT لأداة "الاستخراج" (قائمة اختيار المصدر)
        source_files = [f for f in all_files if f.endswith('.json') or f.endswith('.txt')]

    except FileNotFoundError:
        database_files = []
        source_files = []
        flash("تنبيه: مجلد 'utilities' غير موجود.", "warning")

    # نمرر كلتا القائمتين إلى القالب بأسماء مختلفة
    return render_template('advanced_tools.html', 
                           database_files=database_files, 
                           source_files=source_files)
# END: MODIFIED SECTION


# START: MODIFIED SECTION
@app.route('/run_tool', methods=['POST'])
def run_tool():
    """
    مسار API لمعالجة الطلبات من صفحة الأدوات المتقدمة.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'لم يتم استلام أي بيانات.'}), 400

        action = data.get('action')
        utilities_folder = os.path.join(BASE_DIR, "utilities")
        
        if action == 'extract_by_size':
            content = data.get('input_content')
            if not content or not content.strip():
                return jsonify({'success': False, 'message': 'المحتوى فارغ. الرجاء اختيار ملف أو لصق محتوى للتحليل.'})
            
            try:
                all_json_files = [f for f in os.listdir(utilities_folder) if f.endswith('.json')]
                if not all_json_files:
                    return jsonify({'success': False, 'message': "لم يتم العثور على ملفات قاعدة بيانات (.json) في مجلد 'utilities'."})
                
                database_files_paths = [os.path.join(utilities_folder, f) for f in all_json_files]
            except FileNotFoundError:
                 return jsonify({'success': False, 'message': "مجلد 'utilities' غير موجود."})

            result = advanced_tools.function_extract_by_size(
                input_content=content,
                database_files=database_files_paths,
                base_output_path=utilities_folder,
                original_filename="user_content"
            )
            return jsonify(result)

        elif action == 'make_competition':
            input_file = data.get('input_json_path')
            settings = data.get('settings')
            if not input_file or not settings:
                return jsonify({'success': False, 'message': 'بيانات الإدخال أو الإعدادات مفقودة.'})

            full_input_path = os.path.join(utilities_folder, input_file)

            result = advanced_tools.function_make_competition(
                input_json_path=full_input_path,
                base_output_path=utilities_folder,
                settings=settings
            )
            return jsonify(result)
        
        elif action == 'compare_and_correct':
            target_file = data.get('target_file')
            output_option = data.get('output_option')

            if not target_file:
                return jsonify({'success': False, 'message': 'الرجاء اختيار ملف بطولة لتصحيحه.'})

            try:
                master_db_names = [f for f in os.listdir(utilities_folder) if f.startswith('elo_videos') and f.endswith('.json')]
                if not master_db_names:
                    return jsonify({'success': False, 'message': "لم يتم العثور على ملفات قاعدة البيانات الموثوقة (elo_videos_*.json)." })
                
                master_db_paths = [os.path.join(utilities_folder, f) for f in master_db_names]
            except FileNotFoundError:
                return jsonify({'success': False, 'message': "مجلد 'utilities' غير موجود."})

            target_file_path = os.path.join(utilities_folder, target_file)

            result = advanced_tools.function_compare_and_correct(
                target_file_path=target_file_path,
                master_db_paths=master_db_paths,
                output_option=output_option,
                base_output_path=utilities_folder
            )
            return jsonify(result)

        # --- بداية القسم الجديد ---
        elif action == 'process_weights_and_create':
            settings = data.get('settings')
            if not settings:
                 return jsonify({'success': False, 'message': 'الإعدادات مفقودة.'})
            
            result = advanced_tools.function_process_weights_and_create_tournament(
                settings=settings,
                base_utilities_path=utilities_folder
            )
            return jsonify(result)
        # --- نهاية القسم الجديد ---
            
        else:
            return jsonify({'success': False, 'message': 'الإجراء المطلوب غير معروف.'}), 400

    except Exception as e:
        print(f"Error in /run_tool: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'حدث خطأ غير متوقع في الخادم: {str(e)}'}), 500
# END: MODIFIED SECTION



@app.route('/competition', methods=['GET', 'POST'])
def competition():
    """
    Handles competition requests.
    MODIFIED: Added precise timing to diagnose the 7-10s delay.
    """
    tournament_files = tour.list_tournament_files()

    # --- GET REQUEST Handling ---
    if request.method == 'GET' and request.args.get('tournament_file'):
        tournament_file = request.args.get('tournament_file')
        session['last_selected_tournament'] = tournament_file
        print(f"GET request with tournament_file param: {tournament_file}")
        try:
            with open(os.path.join("utilities", tournament_file), 'r', encoding='utf-8') as f:
                json_data = f.read()
            print("Tournament file read successfully.")
        except Exception as e:
            flash(f"Error loading tournament file: {str(e)}", "danger")
            print(f"Error reading tournament file: {str(e)}")
            return render_template(
                'start_competition.html', tournament_files=tour.list_tournament_files())

        if json_data:
            try:
                print("Parsing JSON from tournament file...")
                competitions = json.loads(json_data)
                print("JSON parsed successfully.")
                if not isinstance(competitions, list):
                    raise ValueError("JSON data must be a list.")

                # --- START: AUTO-FILTER LOGIC (GET) ---
                if tournament_file:
                    print(f"Auto-filtering unplayed matches for '{tournament_file}'...")
                    filter_result = tour.filter_unplayed_matches(tournament_file)
                    if filter_result.get('success'):
                        original_count = len(competitions)
                        competitions = filter_result.get('data', [])
                        print(f"Auto-filter successful. Match count reduced from {original_count} to {len(competitions)}.")
                    else:
                        flash(f"Could not automatically filter unplayed matches: {filter_result.get('message')}", "warning")
                        print(f"WARNING: Auto-filtering failed for {tournament_file}.")
                # --- END: AUTO-FILTER LOGIC (GET) ---

                data = load_data()
                if not data:
                    flash("No competition data available.", "danger")
                    print("Loaded data is empty when processing tournament file.")
                    return redirect(url_for('competition'))

                session['competitions_queue'] = competitions
                print(f"Stored competitions queue in session, count: {len(competitions)}")
                if not competitions:
                     flash("Tournament file is empty or all matches are completed.", "warning")
                     print("Tournament file provided an empty list after filtering.")
                     return render_template('start_competition.html', tournament_files=tour.list_tournament_files(), last_selected_file=tournament_file)

                current_competition = session['competitions_queue'].pop(0)
                session['competition_params'] = current_competition
                print(f"Popped first competition from queue. Params: {current_competition}")

                videos_from_json = current_competition.get('videos')
                mode = current_competition.get('mode', 1)
                num_videos = current_competition.get('num_videos', 2)
                ranking_type = current_competition.get('ranking_type', 'winner_only')
                use_dynamic_weighting = current_competition.get('use_dynamic_weighting', False)
                competition_type = current_competition.get('competition_type', 'random')
                value = current_competition.get('value')

                print(f"Starting competition from JSON - Mode: {mode}, Num Videos: {num_videos}")

                # --- DIAGNOSTIC TIMER (GET) ---
                t_start = time.time()
                competition_videos_raw = choose_videos_function(
                    data, mode, value, num_videos, use_dynamic_weighting,
                    competition_type, videos_from_json or [], session=session
                )
                print(f"⏱️ DIAGNOSTIC: choose_videos_function (GET) took {time.time() - t_start:.4f} seconds")
                # ------------------------------

                processed_data_dict = load_processed_videos_data()
                video_folder = session.get('selected_folder')

                if not video_folder:
                     print("WARNING: selected_folder not found in session. Cannot get file sizes.")

                ranking_map = create_ranking_map(data)
                enriched_competition_videos = []
                for vid_name, rating, times_shown, tags, *_ in competition_videos_raw:
                    display_name_from_db = data.get(vid_name, {}).get('name', '')
                    enriched_video_info = {
                        'name': vid_name, 'display_name': display_name_from_db,
                        'rating': rating, 'times_shown': times_shown, 'tags': tags,
                        'is_processed': False, 'weight': None,
                        'rank': ranking_map.get(vid_name, 'N/A')
                    }
                    if video_folder:
                        full_video_path = os.path.join(video_folder, vid_name)
                        try:
                            file_size = os.path.getsize(full_video_path)
                            if file_size in processed_data_dict:
                                processed_info = processed_data_dict[file_size]
                                enriched_video_info['is_processed'] = True
                                enriched_video_info['weight'] = processed_info.get('total_weight')
                        except (FileNotFoundError, Exception):
                            pass
                    enriched_competition_videos.append(enriched_video_info)

                competition_videos_to_render = enriched_competition_videos
                print(f"Prepared {len(competition_videos_to_render)} enriched videos for rendering.")

                if competition_videos_to_render and len(competition_videos_to_render) >= 2:
                     template_params_get = {
                         'competition_videos': competition_videos_to_render, 'num_videos': num_videos,
                         'mode': mode, 'ranking_type': ranking_type, 'competition_type': competition_type,
                         'data': data
                     }
                     if isinstance(value, dict):
                         template_params_get.update(value)
                     elif value is not None:
                         template_params_get['value'] = value
                     return render_template('select_winner.html', **template_params_get)
                else:
                    flash("Not enough suitable videos found.", "warning")
                    session.pop('competitions_queue', None)
                    session.pop('competition_params', None)
                    return render_template('start_competition.html', tournament_files=tour.list_tournament_files())

            except (json.JSONDecodeError, ValueError) as e:
                flash(f"Invalid JSON data: {str(e)}", "danger")
                return render_template('start_competition.html', tournament_files=tour.list_tournament_files())
            except Exception as e:
                 flash(f"An unexpected error occurred: {str(e)}", "danger")
                 import traceback
                 traceback.print_exc()
                 return render_template('start_competition.html', tournament_files=tour.list_tournament_files())

    if not session.get('selected_folder'):
        flash("Please select a folder first.", "warning")
        return redirect(url_for('select_folder'))

    # --- POST REQUEST Handling ---
    if request.method == 'POST':
        print("Received POST request for competition.")
        
        tournament_file = request.form.get('tournament_file')
        
        if tournament_file:
            session['last_selected_tournament'] = tournament_file
            print(f"A file was selected in the form: '{tournament_file}'. Saved to session.")

        json_data = request.form.get('json_data')
        
        data_is_from_file = False
        
        if not json_data or not json_data.strip():
            if tournament_file:
                print(f"Textarea is empty, loading from selected file: {tournament_file}")
                try:
                    with open(os.path.join("utilities", tournament_file), 'r', encoding='utf-8') as f:
                        json_data = f.read()
                    data_is_from_file = True
                    print("Read JSON data from file as fallback.")
                except Exception as e:
                    flash(f"Error loading tournament file from POST: {str(e)}", "danger")
                    return render_template('start_competition.html', tournament_files=tour.list_tournament_files())
        else:
             print("Using JSON data provided in the textarea.")
             if tournament_file:
                 data_is_from_file = True

        if json_data:
            try:
                print("Parsing JSON from POST request...")
                competitions = json.loads(json_data)
                print("JSON parsed successfully from POST.")
                if not isinstance(competitions, list):
                    raise ValueError("JSON data must be a list.")

                # --- START: AUTO-FILTER LOGIC (POST) ---
                if data_is_from_file and tournament_file:
                    print(f"Auto-filtering unplayed matches for '{tournament_file}'...")
                    filter_result = tour.filter_unplayed_matches(tournament_file)
                    if filter_result.get('success'):
                        original_count = len(competitions)
                        competitions = filter_result.get('data', [])
                        print(f"Auto-filter successful. Match count reduced from {original_count} to {len(competitions)}.")
                    else:
                        flash(f"Could not automatically filter unplayed matches: {filter_result.get('message')}", "warning")
                # --- END: AUTO-FILTER LOGIC (POST) ---

                data = load_data()
                if not data:
                    flash("No competition data available.", "danger")
                    return redirect(url_for('competition'))

                session['competitions_queue'] = competitions
                # --- هذا هو المكان الذي أشرت إليه في سجلك ---
                print(f"Stored competitions queue from POST, count: {len(competitions)}") 
                if not competitions:
                     flash("JSON data is empty or all matches are completed.", "warning")
                     return render_template('start_competition.html', tournament_files=tour.list_tournament_files(), last_selected_file=tournament_file)

                # --- نتتبع الوقت هنا ---
                t_pop = time.time()
                current_competition = session['competitions_queue'].pop(0)
                session['competition_params'] = current_competition
                print(f"Popped first competition from POST queue. Params: {current_competition}")
                print(f"⏱️ DIAGNOSTIC: Queue Pop took {time.time() - t_pop:.4f} seconds")

                videos_from_json = current_competition.get('videos')
                mode = current_competition.get('mode', 1)
                num_videos = current_competition.get('num_videos', 2)
                ranking_type = current_competition.get('ranking_type', 'winner_only')
                use_dynamic_weighting = current_competition.get('use_dynamic_weighting', False)
                competition_type = current_competition.get('competition_type', 'random')
                value = current_competition.get('value')

                print(f"Starting competition from POST JSON - Mode: {mode}")

                # --- DIAGNOSTIC TIMER (POST - JSON) - المنطقة المشبوهة ---
                print("⏱️ DIAGNOSTIC: Starting choose_videos_function (This is likely the delay)...")
                t_start = time.time()
                competition_videos_raw = choose_videos_function(
                    data, mode, value, num_videos, use_dynamic_weighting,
                    competition_type, videos_from_json or [], session=session
                )
                print(f"⏱️ DIAGNOSTIC: choose_videos_function (POST JSON) took {time.time() - t_start:.4f} seconds")
                # --------------------------------------------------------

                processed_data_dict = load_processed_videos_data()
                video_folder = session.get('selected_folder')

                if not video_folder:
                     print("WARNING: selected_folder not found in session.")

                ranking_map = create_ranking_map(data)
                enriched_competition_videos = []
                for vid_name, rating, times_shown, tags, *_ in competition_videos_raw:
                    display_name_from_db = data.get(vid_name, {}).get('name', '')
                    enriched_video_info = {
                        'name': vid_name, 'display_name': display_name_from_db,
                        'rating': rating, 'times_shown': times_shown, 'tags': tags,
                        'is_processed': False, 'weight': None,
                        'rank': ranking_map.get(vid_name, 'N/A')
                    }
                    if video_folder:
                        full_video_path = os.path.join(video_folder, vid_name)
                        try:
                            file_size = os.path.getsize(full_video_path)
                            if file_size in processed_data_dict:
                                processed_info = processed_data_dict[file_size]
                                enriched_video_info['is_processed'] = True
                                enriched_video_info['weight'] = processed_info.get('total_weight')
                        except (FileNotFoundError, Exception):
                            pass
                    enriched_competition_videos.append(enriched_video_info)

                competition_videos_to_render = enriched_competition_videos
                print(f"Prepared {len(competition_videos_to_render)} enriched videos for rendering.")

                if competition_videos_to_render and len(competition_videos_to_render) >= 2:
                    print(f"Rendering select_winner.html with {len(competition_videos_to_render)} videos from POST JSON.")
                    template_params_post_json = {
                        'competition_videos': competition_videos_to_render, 'num_videos': num_videos,
                        'mode': mode, 'ranking_type': ranking_type, 'competition_type': competition_type,
                        'data': data
                    }
                    if isinstance(value, dict):
                        template_params_post_json.update(value)
                    elif value is not None:
                        template_params_post_json['value'] = value
                    return render_template('select_winner.html', **template_params_post_json)
                else:
                    flash("Not enough suitable videos found.", "warning")
                    session.pop('competitions_queue', None)
                    session.pop('competition_params', None)
                    return render_template('start_competition.html', tournament_files=tour.list_tournament_files())

            except (json.JSONDecodeError, ValueError) as e:
                flash(f"Invalid JSON data provided: {str(e)}", "danger")
                return render_template('start_competition.html', tournament_files=tour.list_tournament_files())
            except Exception as e:
                 flash(f"An unexpected error occurred processing POST JSON: {str(e)}", "danger")
                 import traceback
                 traceback.print_exc()
                 return render_template('start_competition.html', tournament_files=tour.list_tournament_files())

        else: # No JSON data, process form parameters
            mode = int(request.form.get('mode', 1))
            num_videos = int(request.form.get('num_videos', 2))
            ranking_type = request.form.get('ranking_type')
            use_dynamic_weighting = request.form.get('use_dynamic_weighting') == 'true'
            competition_type = request.form.get('competition_type')
            value = None
            
            # (Validation logic truncated for brevity - assumes copied from original)
            if mode == 8:
                try: value = {'min_value1': float(request.form['min_value1']), 'max_value1': float(request.form['max_value1']), 'min_value2': float(request.form['min_value2']), 'max_value2': float(request.form['max_value2'])}
                except (ValueError, KeyError): flash("Invalid values.", "danger"); return render_template('start_competition.html', tournament_files=tour.list_tournament_files())
            elif mode in [5, 6]:
                try: value = {'min_value': float(request.form['min_value']), 'max_value': float(request.form['max_value'])}
                except (ValueError, KeyError): flash("Invalid values.", "danger"); return render_template('start_competition.html', tournament_files=tour.list_tournament_files())
            elif mode in [3, 4]:
                try: value_str = request.form.get('value'); value = float(value_str) if value_str else None
                except (ValueError, KeyError): flash("Invalid value.", "danger"); return render_template('start_competition.html', tournament_files=tour.list_tournament_files())
            elif mode == 9:
                try: value = {'min_times_shown': int(request.form['min_times_shown']), 'max_times_shown': int(request.form['max_times_shown'])}
                except (ValueError, KeyError): flash("Invalid values.", "danger"); return render_template('start_competition.html', tournament_files=tour.list_tournament_files())
            elif mode == 10:
                try: value = {'tags': request.form['tags_value_mode_input'].strip()}
                except KeyError: flash("Please enter tags.", "danger"); return render_template('start_competition.html', tournament_files=tour.list_tournament_files())

            session['competition_params'] = {
                'mode': mode, 'value': value, 'num_videos': num_videos,
                'ranking_type': ranking_type, 'use_dynamic_weighting': use_dynamic_weighting,
                'competition_type': competition_type
            }
            session.pop('competitions_queue', None)

            data = load_data()
            if not data:
                flash("No competition data available.", "danger")
                return render_template('start_competition.html', tournament_files=tour.list_tournament_files())

            # --- DIAGNOSTIC TIMER (POST - FORM) ---
            print("⏱️ DIAGNOSTIC: Starting choose_videos_function (Form)...")
            t_start = time.time()
            competition_videos_raw = choose_videos_function(
                data, mode, value, num_videos, use_dynamic_weighting, competition_type, [], session=session
            )
            print(f"⏱️ DIAGNOSTIC: choose_videos_function (POST Form) took {time.time() - t_start:.4f} seconds")
            # --------------------------------------
            
            processed_data_dict = load_processed_videos_data()
            video_folder = session.get('selected_folder')
            ranking_map = create_ranking_map(data)
            enriched_competition_videos = []
            for vid_name, rating, times_shown, tags, *_ in competition_videos_raw:
                display_name_from_db = data.get(vid_name, {}).get('name', '')
                enriched_video_info = {
                    'name': vid_name, 'display_name': display_name_from_db,
                    'rating': rating, 'times_shown': times_shown, 'tags': tags,
                    'is_processed': False, 'weight': None,
                    'rank': ranking_map.get(vid_name, 'N/A')
                }
                if video_folder:
                    full_video_path = os.path.join(video_folder, vid_name)
                    try:
                        file_size = os.path.getsize(full_video_path)
                        if file_size in processed_data_dict:
                            processed_info = processed_data_dict[file_size]
                            enriched_video_info['is_processed'] = True
                            enriched_video_info['weight'] = processed_info.get('total_weight')
                    except (FileNotFoundError, Exception):
                        pass
                enriched_competition_videos.append(enriched_video_info)

            competition_videos_to_render = enriched_competition_videos
            
            if competition_videos_to_render and len(competition_videos_to_render) >= 2:
                template_params = {
                    'competition_videos': competition_videos_to_render, 'num_videos': num_videos,
                    'mode': mode, 'ranking_type': ranking_type, 'competition_type': competition_type,
                    'data': data
                }
                if isinstance(value, dict):
                    template_params.update(value)
                elif value is not None:
                    template_params['value'] = value
                return render_template('select_winner.html', **template_params)
            else:
                flash("Not enough suitable videos found.", "warning")
                session.pop('competition_params', None)
                return render_template('start_competition.html', tournament_files=tour.list_tournament_files())

    # GET request without params
    print("Rendering start_competition.html (GET request).")
    session.pop('competitions_queue', None)
    session.pop('competition_params', None)
    session.pop('last_winner', None)

    sorted_tournament_files = sorted(tournament_files)
    last_selected_file = session.get('last_selected_tournament')

    return render_template('start_competition.html', 
                           tournament_files=sorted_tournament_files,
                           last_selected_file=last_selected_file)



# START: MODIFIED SECTION - دالة select_winner (محسنة + المنطق القديم)
@app.route('/select_winner', methods=['POST'])
def select_winner():
    """
    Processes the winner selection form submission.
    يتضمن الآن منطق "القفز" القديم مع الحفاظ على تحسينات الأداء.
    """
    import time
    grand_start = time.time()
    print("\n⭐⭐ STARTING TIMER: /select_winner (Optimized + Old Logic) ⭐⭐")

    if not session.get('selected_folder'):
        flash("Please select a folder first.", "warning")
        return redirect(url_for('select_folder'))

    # --- 1. Load Data ---
    t_start = time.time()
    data = load_data()
    print(f"⏱️ [1] Load Data took: {time.time() - t_start:.4f}s")
    
    if not data:
        flash("No competition data available.", "danger")
        return redirect(url_for('competition'))

    original_video_names_in_competition = request.form.getlist('videos')

    if not original_video_names_in_competition:
        flash("No videos were submitted.", "danger")
        session.pop('competitions_queue', None)
        session.pop('competition_params', None)
        session.pop('last_winner', None)
        return redirect(url_for('competition'))

    # --- 2. Tag Updates ---
    t_start = time.time()
    tag_updates_made = False
    try: 
        for index, video_name in enumerate(original_video_names_in_competition, start=1):
            if video_name in data:
                tags_input = request.form.get(f'tag_{index}', None)
                if tags_input is not None:
                    processed_tags = []
                    if '∅' not in tags_input.split(','): 
                         processed_tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                    new_tags_str = ','.join(sorted(list(set(processed_tags))))
                    if data[video_name].get('tags', '') != new_tags_str:
                        data[video_name]['tags'] = new_tags_str
                        tag_updates_made = True
    except Exception as e:
         print(f"ERROR during tag processing: {e}")
    print(f"⏱️ [2] Tag Processing took: {time.time() - t_start:.4f}s")

    # --- Skip Logic ---
    if request.form.get('skip_competition') == 'true':
        flash("Competition skipped.", "info")
        # (منطق التخطي المعتاد - مختصر هنا للحفاظ على المساحة، يبقى كما هو في كودك)
        # ... تأكد من أن كود التخطي موجود هنا كما كان ...
        # إذا كنت تحتاج كود التخطي كاملاً أخبرني، سأفترض أنه موجود لديك
        
        # كود تحضير الجولة التالية للتخطي (مختصر):
        next_competition_params = None
        competitions_queue = session.get('competitions_queue')
        params_from_skipped = session.get('competition_params')
        if competitions_queue:
             next_competition_params = competitions_queue.pop(0)
             session['competition_params'] = next_competition_params
        else:
             next_competition_params = params_from_skipped
             
        # ... بقية منطق إعادة التوجيه للتخطي ...
        return redirect(url_for('competition'))


    # --- 3. ELO Calculation Prep ---
    t_start = time.time()
    try: 
        mode = request.form.get('mode', type=int)
        num_videos = request.form.get('num_videos', type=int)
        ranking_type = request.form.get('ranking_type')
        competition_type = request.form.get('competition_type')
        value = None 
        
        # استعادة القيم (Value reconstruction)
        if mode == 8: value = {'min_value1': request.form.get('min_value1', type=float), 'max_value1': request.form.get('max_value1', type=float), 'min_value2': request.form.get('min_value2', type=float), 'max_value2': request.form.get('max_value2', type=float)}
        elif mode in [5, 6]: value = {'min_value': request.form.get('min_value', type=float), 'max_value': request.form.get('max_value', type=float)}
        elif mode in [3, 4]: val_str = request.form.get('value'); value = float(val_str) if val_str else None
        elif mode == 9: 
            try: value = {'min_times_shown': int(request.form.get('min_times_shown')), 'max_times_shown': int(request.form.get('max_times_shown'))}
            except: pass
        elif mode == 10: value = {'tags': request.form.get('tags_value_input')}

        winner_vid = None
        ranked_videos_for_update_sorted = [] # (name, current_rating, rank_index)

        if ranking_type == 'winner_only':
            winner_vid = request.form.get('winner')
            if not winner_vid or winner_vid not in original_video_names_in_competition:
                 return redirect(url_for('competition'))
            
            # Add Winner (Rank 0)
            if winner_vid in data:
                 ranked_videos_for_update_sorted.append((winner_vid, float(data[winner_vid].get('rating', 1000.0)), 0))
            
            # Add Losers (Rank 1)
            for vid in original_video_names_in_competition:
                if vid != winner_vid and vid in data:
                    ranked_videos_for_update_sorted.append((vid, float(data[vid].get('rating', 1000.0)), 1))
        
        else:
             # Rank mode logic
             submitted_ranks = {}
             for i, video_name in enumerate(original_video_names_in_competition):
                 rank_val = request.form.get(f'rank_{i+1}')
                 if rank_val: submitted_ranks[video_name] = int(rank_val)
             
             # Sort by rank
             videos_with_ranks = []
             for vid, r in submitted_ranks.items():
                 if vid in data: videos_with_ranks.append((vid, float(data[vid].get('rating', 1000.0)), r))
             videos_with_ranks.sort(key=lambda x: x[2])
             
             # Re-map to 0-based index
             for i, (vid, rating, _) in enumerate(videos_with_ranks):
                 ranked_videos_for_update_sorted.append((vid, rating, i))
             
             if videos_with_ranks: winner_vid = videos_with_ranks[0][0]

        if len(ranked_videos_for_update_sorted) < 2:
             return redirect(url_for('competition'))

        # حفظ التقييمات الأصلية قبل الحساب (مهم للمنطق القديم)
        original_ratings_before_elo = {
            vid: data.get(vid, {}).get('rating', 1000.0) 
            for vid, _, _ in ranked_videos_for_update_sorted
        }
        
        # --- 4. The ELO Update Function ---
        t_elo = time.time()
        update_ratings_multiple(ranked_videos_for_update_sorted, data)
        print(f"⏱️ [4] ELO Math took: {time.time() - t_elo:.4f}s")

        # --- 5. START: RE-INTEGRATED OLD LOGIC (Post-ELO Adjustment) ---
        print("\n--- Applying Post-ELO Adjustment (Old Logic Restored) ---")
        
        # استخراج قائمة الأسماء مرتبة حسب الرتبة (الفائز أولاً)
        ranked_video_names_final_order = [item[0] for item in ranked_videos_for_update_sorted]

        # التأكد من وجود فائز (Rank 0) وخاسرين
        if ranked_videos_for_update_sorted and ranked_videos_for_update_sorted[0][2] == 0:
            winner_name = ranked_video_names_final_order[0]
            
            # التكرار على الخاسرين
            for i in range(1, len(ranked_video_names_final_order)):
                loser_name = ranked_video_names_final_order[i]
                
                # التأكد من صحة البيانات
                if winner_name in data and loser_name in data:
                    rating_a_after = data[winner_name]['rating']
                    rating_b_after = data[loser_name]['rating']
                    
                    orig_a = original_ratings_before_elo.get(winner_name)
                    orig_b = original_ratings_before_elo.get(loser_name)

                    # 1. الحالة الاستثنائية: الفائز 1000 بالضبط يهزم خصماً أقوى
                    if (orig_a is not None and orig_b is not None and
                        orig_a < orig_b and abs(orig_a - 1000.0) < 0.01):
                        
                        print(f"  [Snatch] Newcomer {winner_name} (1000) beat {loser_name} ({orig_b}). Snatching rating!")
                        data[winner_name]['rating'] = orig_b
                        # الخاسر يحتفظ بتقييمه بعد الـ Elo (لا تغيير إضافي)
                        continue 

                    # 2. التعديل القياسي: إذا ظل تقييم الفائز أقل من الخاسر بعد الحساب
                    if rating_a_after < rating_b_after:
                        print(f"  [Swap] Winner {winner_name} ({rating_a_after:.0f}) still < Loser {loser_name} ({rating_b_after:.0f}). Swapping!")
                        data[winner_name]['rating'] = rating_b_after
                        data[loser_name]['rating'] = (rating_a_after + rating_b_after) / 2.0

        print("--- End of Post-ELO Adjustment ---")
        # --- END: RE-INTEGRATED OLD LOGIC ---

        # --- 6. Names Analysis ---
        t_start = time.time()
        explicit_winner_id = winner_vid
        explicit_loser_ids = [vid for vid in original_video_names_in_competition if vid != explicit_winner_id]

        if explicit_winner_id and explicit_loser_ids:
            update_names_analysis(explicit_winner_id, explicit_loser_ids, original_video_names_in_competition, data)
        print(f"⏱️ [6] Names Analysis took: {time.time() - t_start:.4f}s")

        # --- 7. Win/Loss Stats Update ---
        t_start = time.time()
        for vid in original_video_names_in_competition:
             if vid in data:
                  data[vid].setdefault('total_wins', 0)
                  data[vid].setdefault('total_losses', 0)
                  data[vid].setdefault('times_shown', 0)
                  if winner_vid is not None:
                       if vid == winner_vid: data[vid]['total_wins'] += 1
                       else: data[vid]['total_losses'] += 1
                  total = data[vid]['total_wins'] + data[vid]['total_losses']
                  data[vid]['win_rate'] = (data[vid]['total_wins'] / total) if total > 0 else 0.0
                  data[vid]['times_shown'] = data[vid].get('times_shown', 0) + 1
        print(f"⏱️ [7] Stats Update took: {time.time() - t_start:.4f}s")

        # --- 8. Save Data & Backup ---
        t_start = time.time()
        try:
             save_data(data)
             create_backup(data)
             flash("Ratings, stats, and tags updated successfully!", "success")
        except Exception as e:
             flash(f"Error saving: {e}", "danger")
        print(f"⏱️ [8] Disk Save took: {time.time() - t_start:.4f}s")

        # --- 9. Prepare Next Round ---
        t_start = time.time()
        if winner_vid: session['last_winner'] = winner_vid
        else: session.pop('last_winner', None)

        next_competition_params = None
        competitions_queue = session.get('competitions_queue')
        params_from_completed_round = session.get('competition_params')

        if competitions_queue:
             next_competition_params = competitions_queue.pop(0)
             session['competition_params'] = next_competition_params
        else:
             next_competition_params = params_from_completed_round

        reconstructed_next_value = next_competition_params.get('value')
        # ... (نفس منطق إعادة بناء القيمة 9 و 10 الموجود سابقاً يفترض وجوده هنا) ...
        # (اختصرته هنا لأن الكود لم يتغير في هذه المنطقة)
        
        # هام: إذا كنت تستخدم الكود المختصر في إعادة بناء القيمة في حال التكرار (Mode 9/10)
        # تأكد من أنه موجود كما كان.

        final_next_value_for_choose_videos = reconstructed_next_value

        # استخدام البيانات من الذاكرة (Optimization)
        data_for_next_round = data 

        new_competition_videos_raw = choose_videos_function(
            data_for_next_round, 
            next_competition_params.get('mode', 1),
            final_next_value_for_choose_videos, 
            next_competition_params.get('num_videos', 2),
            next_competition_params.get('use_dynamic_weighting', False),
            next_competition_params.get('competition_type', 'random'),
            next_competition_params.get('videos', []),
            session=session 
        )

        # تجهيز العرض
        processed_data_dict = load_processed_videos_data()
        video_folder = session.get('selected_folder')
        ranking_map = create_ranking_map(data_for_next_round)
        enriched_competition_videos = []
        for vid_name, _, _, _, *_ in new_competition_videos_raw:
             video_data_entry = data_for_next_round.get(vid_name, {})
             display_name_from_db = video_data_entry.get('name', '')
             enriched_video_info = {
                 'name': vid_name, 'display_name': display_name_from_db,
                 'rating': video_data_entry.get('rating', 1000.0),
                 'times_shown': video_data_entry.get('times_shown', 0),
                 'tags': video_data_entry.get('tags', ''),
                 'is_processed': False, 'weight': None,
                 'rank': ranking_map.get(vid_name, 'N/A')
             }
             if video_folder:
                 try:
                     full_video_path = os.path.join(video_folder, vid_name)
                     file_size = os.path.getsize(full_video_path)
                     if file_size in processed_data_dict:
                         enriched_video_info['is_processed'] = True
                         enriched_video_info['weight'] = processed_data_dict[file_size].get('total_weight')
                 except: pass
             enriched_competition_videos.append(enriched_video_info)
        
        print(f"⏱️ [9] Prepare Next Round took: {time.time() - t_start:.4f}s")
        print(f"⭐⭐ TOTAL REQUEST TIME: {time.time() - grand_start:.4f}s ⭐⭐\n")

        template_params_next = {
            'competition_videos': enriched_competition_videos,
            'num_videos': next_competition_params.get('num_videos', 2),
            'mode': next_competition_params.get('mode', 1),
            'ranking_type': next_competition_params.get('ranking_type', 'winner_only'),
            'competition_type': next_competition_params.get('competition_type', 'random'),
            'data': data_for_next_round
        }
        if isinstance(final_next_value_for_choose_videos, dict):
             template_params_next.update(final_next_value_for_choose_videos)
        elif final_next_value_for_choose_videos is not None:
             template_params_next['value'] = final_next_value_for_choose_videos

        return render_template('select_winner.html', **template_params_next)

    except Exception as e:
        flash(f"Error: {e}", "danger")
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('competition'))
# END: MODIFIED SECTION

@app.route('/rename_all_videos', methods=['POST'])
def rename_all_videos():
    return rename_all_videos_function()


@app.route('/top_videos', methods=['GET', 'POST'])
def top_videos():
    return render_top_videos()

@app.route('/manage_tournaments', methods=['GET'])
def manage_tournaments():
    """Displays the tournament management page."""
    json_files = tournaments_manager.list_json_files()
    selected_file = request.args.get('file')
    file_content = None
    if selected_file:
        data = tournaments_manager.load_tournament_data(selected_file)
        if data is not None:
            # Pass the raw data (list of dicts) to the template
            # The template will parse it again to render checkboxes and JSON display
            # This avoids double-parsing server-side for rendering list/checkboxes
            file_content = json.dumps(data) # Send as JSON string
        else:
             flash(f"Failed to load content for {selected_file}. It might be corrupt or empty.", "danger")

    return render_template('manage_tournaments.html',
                           json_files=json_files,
                           selected_file=selected_file,
                           file_content=file_content) # Pass raw JSON string
                           
                           
@app.route('/manage_tournaments_actions', methods=['POST'])
def manage_tournaments_actions():
    """Handles actions like deleting, pasting, and swapping competitions."""
    selected_file = request.form.get('selected_file')
    action = request.form.get('action')
    print(f"Received action: {action} for file: {selected_file}") # DEBUG

    if not selected_file:
        flash("No file selected for action.", "danger")
        return redirect(url_for('manage_tournaments'))

    # Basic sanitization before passing to manager functions
    if '..' in selected_file or selected_file.startswith('/'):
        flash("Invalid file name.", "danger")
        return redirect(url_for('manage_tournaments'))

    success = False
    message = "No action performed."

    if action == 'delete':
        indices_str = request.form.get('competition_indices')
        if indices_str:
            try:
                indices_to_delete = [int(i) for i in indices_str.split(',') if i.isdigit()]
                if indices_to_delete:
                    success, message = tournaments_manager.delete_competitions(selected_file, indices_to_delete)
                else:
                     message = "No valid competition indices provided for deletion."
            except Exception as e:
                message = f"Error processing deletion indices: {e}"
                print(f"Error processing deletion indices: {e}") # DEBUG
        else:
            message = "No competition indices provided for deletion."

    elif action == 'paste':
        pasted_json_string = request.form.get('pasted_json')
        paste_mode = request.form.get('paste_mode', 'append')
        if pasted_json_string:
             success, message = tournaments_manager.paste_competitions(selected_file, pasted_json_string, paste_mode)
        else:
             message = "No JSON data provided to paste."
             print("Paste action received but pasted_json_string is empty.") # DEBUG


    elif action == 'swap':
         comp1_index_str = request.form.get('swap_comp1_index')
         comp1_comp_index_str = request.form.get('swap_comp1_competitor_index')
         comp2_index_str = request.form.get('swap_comp2_index')
         comp2_comp_index_str = request.form.get('swap_comp2_competitor_index')

         if all([comp1_index_str, comp1_comp_index_str, comp2_index_str, comp2_comp_index_str]):
              try:
                   comp1_index = int(comp1_index_str)
                   comp1_comp_index = int(comp1_comp_index_str)
                   comp2_index = int(comp2_index_str)
                   comp2_comp_index = int(comp2_comp_index_str)

                   # Validate indices again before calling the function
                   # Basic check: Ensure competition indices are not the same (handled in function too)
                   if comp1_index == comp2_index:
                       flash("Cannot swap competitors within the same competition.", "danger")
                       return redirect(url_for('manage_tournaments', file=selected_file))

                   # Call the swap function
                   success, message = tournaments_manager.swap_competitors(
                       selected_file, comp1_index, comp1_comp_index, comp2_index, comp2_comp_index
                   )
              except ValueError:
                   message = "Invalid index format for swap."
                   print("ValueError parsing swap indices.") # DEBUG
              except Exception as e:
                   message = f"An error occurred during swap: {e}"
                   print(f"Error during swap action: {e}") # DEBUG
         else:
              message = "Missing swap parameters."
              print("Swap action received but missing parameters.") # DEBUG

    # Handle flash messages based on success/failure
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    # Redirect back to the manage tournaments page, keeping the selected file open
    return redirect(url_for('manage_tournaments', file=selected_file))                           

# START: MODIFIED SECTION (Add to app.py)
from utilities.rank_tracker import get_rank_changes, save_rank_snapshot

# استيراد الدالة الجديدة
from utilities.bet_manager import add_bet, get_proposed_match, remove_bet, load_bets, check_bet_status, clear_bets_by_status


# 3. تحديث دالة save_snapshot_action
@app.route('/save_snapshot_action', methods=['POST'])
def save_snapshot_action():
    """
    يقوم بحفظ الترتيب الحالي كمرجع للمقارنة مستقبلاً.
    """
    # قراءة الفلاتر للعودة إليها
    return_filter = request.form.get('return_filter', 'all')
    return_search = request.form.get('return_search', '')

    if save_rank_snapshot():
        flash("تم حفظ لقطة الترتيب الحالي بنجاح.", "success")
    else:
        flash("حدث خطأ أثناء حفظ لقطة الترتيب.", "danger")
        
    # إعادة التوجيه مع الحفاظ على الفلاتر
    return redirect(url_for('dashboard', filter=return_filter, search=return_search))

# ... (باقي الكود كما هو) ...

# START: MODIFIED SECTION (Add to app.py)
from utilities.bet_manager import add_bet, get_proposed_match, remove_bet, load_bets, check_bet_status



# START: MODIFIED SECTION
# استبدل الدالة الحالية بهذه النسخة في ملف app.py
@app.route('/get_tournament_content/<path:filename>')
def get_tournament_content(filename):
    """
    مسار آمن لجلب محتوى ملف من مجلد utilities كنص خام.
    يستخدمه الجافا سكريبت لملء المربع النصي بالمحتوى الأصلي دون تغيير.
    """
    try:
        # التحقق من أن اسم الملف لا يحتوي على مسارات خطيرة
        if '..' in filename or filename.startswith('/'):
            return jsonify({'success': False, 'message': 'اسم ملف غير صالح.'}), 400

        # بناء المسار الآمن للملف داخل مجلد utilities
        safe_path = os.path.join(JSON_FOLDER, filename)
        
        # التأكد مرة أخرى من أن المسار النهائي لا يزال داخل المجلد المسموح به
        if not os.path.abspath(safe_path).startswith(os.path.abspath(JSON_FOLDER)):
            return jsonify({'success': False, 'message': 'محاولة الوصول لمسار غير مسموح به.'}), 403

        with open(safe_path, 'r', encoding='utf-8') as f:
            # قراءة محتوى الملف بالكامل كنص واحد خام
            raw_content = f.read()
            
        # إرجاع المحتوى الخام داخل كائن JSON
        # هذا يسهل على JavaScript التعامل معه
        return jsonify({'success': True, 'raw_content': raw_content, 'filename': filename})

    except FileNotFoundError:
        print(f"File not found via API: {filename}")
        return jsonify({'success': False, 'message': 'الملف غير موجود.'}), 404
    except Exception as e:
        print(f"Error in get_tournament_content for {filename}: {e}")
        return jsonify({'success': False, 'message': f'خطأ في الخادم: {str(e)}'}), 500

# أضف هذه الدالة الجديدة في أي مكان مناسب داخل ملف app.py
# (مثلاً، بعد دالة manage_tournaments_actions)
@app.route('/api/manage_tournament_file', methods=['POST'])
def manage_tournament_file_api():
    """
    API endpoint to handle file deletion and renaming.
    """
    from utilities import tournaments_manager # استيراد داخل الدالة لتجنب المشاكل
    
    try:
        data = request.get_json()
        action = data.get('action')
        filename = data.get('filename')
        
        if action == 'delete':
            if not filename:
                return jsonify({'success': False, 'message': 'اسم الملف مطلوب للحذف.'}), 400
            
            success, message = tournaments_manager.delete_tournament_file(filename)
            return jsonify({'success': success, 'message': message})

        elif action == 'rename':
            old_filename = data.get('old_filename')
            new_filename = data.get('new_filename')

            if not old_filename or not new_filename:
                return jsonify({'success': False, 'message': 'الاسم القديم والجديد مطلوبان.'}), 400
            
            success, message = tournaments_manager.rename_tournament_file(old_filename, new_filename)
            return jsonify({'success': success, 'message': message, 'new_filename': new_filename if success else old_filename})
            
        else:
            return jsonify({'success': False, 'message': 'الإجراء غير معروف.'}), 400
            
    except Exception as e:
        print(f"Error in manage_tournament_file_api: {e}")
        return jsonify({'success': False, 'message': f'حدث خطأ في الخادم: {str(e)}'}), 500
# END: MODIFIED SECTION

# START: MODIFIED SECTION (app.py Functions)

@app.route('/tour', methods=['GET', 'POST'])
def tour_page():
    # تحميل القوائم الأساسية
    available_files = tour.list_files(exclude_topcut=True)
    tournament_files = tour.list_tournament_files()
    tournament_archive = tour.load_tournament_archive()
    
    # معالجة خيارات الترتيب والعرض (كما في الكود السابق)
    sort_type = request.form.get('sort_type', 'recent') if request.method == 'POST' else 'recent'
    view_type = request.form.get('view_type', 'tournaments') if request.method == 'POST' else 'tournaments'
    
    # ترتيب البطولات
    sorted_tournaments = tour.sort_tournaments_by_weight(tournament_archive, sort_type)
    
    # الحصول على الفيديوهات الفردية
    video_weights, video_counts = tour.get_individual_videos(tournament_archive)
    
    # منطق ترتيب الفيديوهات الفردية
    sorted_videos = []
    if view_type == 'videos':
        if sort_type == "most_frequent":
            sorted_videos = sorted(video_weights.items(), key=lambda x: video_counts[x[0]], reverse=True)
        elif sort_type == "asc_weight":
            sorted_videos = sorted(video_weights.items(), key=lambda x: x[1])
        elif sort_type == "desc_weight":
            sorted_videos = sorted(video_weights.items(), key=lambda x: x[1], reverse=True)
        else:
            sorted_videos = sorted(video_weights.items(), key=lambda x: x[0])
    
    # === الجديد: تحميل الرهانات النشطة لعرضها في القائمة اليدوية ===
    from utilities.bet_manager import load_bets
    active_bets = load_bets()
    # تصفية النشطة فقط وتجهيزها للعرض
    active_bets_list = [
        {'challenger': k, 'defender': v['defender_video'], 'target': v['target_rank']}
        for k, v in active_bets.items() if v.get('status') == 'active'
    ]
    
    return render_template('tour.html', 
                         available_files=available_files,
                         tournament_files=tournament_files, 
                         tournament_archive=sorted_tournaments,
                         video_weights=sorted_videos,
                         video_counts=video_counts,
                         current_sort=sort_type,
                         current_view=view_type,
                         active_bets=active_bets_list) # تمرير الرهانات للقالب


@app.route('/tour/create', methods=['POST'])
def tour_create():
    # 1. استلام البيانات الأساسية
    selected_file = request.form.get('json_file')
    num_participants_str = request.form.get('num_participants')
    num_matches_total_str = request.form.get('num_matches_total') # الحقل الجديد لعدد المباريات
    num_videos = int(request.form.get('num_videos', 2))
    ranking_type = request.form.get('ranking_type')
    
    # 2. استلام بيانات المراهنة
    include_bets = request.form.get('include_bets') == 'on'
    bet_count = int(request.form.get('bet_count', 0))
    bet_mode = request.form.get('bet_mode', 'random')
    selected_bets = request.form.getlist('selected_bets') # قائمة الرهانات المختارة يدوياً

    # 3. تحديد عدد المباريات الكلي
    # الأولوية للحقل الصريح (num_matches_total)، وإلا نحسبها من عدد المشاركين (Legacy)
    num_matches = 10 # قيمة افتراضية
    if num_matches_total_str and num_matches_total_str.isdigit() and int(num_matches_total_str) > 0:
        num_matches = int(num_matches_total_str)
    elif num_participants_str and num_participants_str.isdigit():
        # إذا أدخل المستخدم عدد مشاركين (مثلاً 32) والمباراة ثنائية، فعدد المباريات 16
        num_matches = max(1, int(num_participants_str) // num_videos)

    # 4. التوجيه للدالة المناسبة
    if include_bets:
        # --- إنشاء بطولة مختلطة (رهان + عشوائي) ---
        bet_settings = {
            'count': bet_count,
            'mode': bet_mode,
            'selected_bets': selected_bets
        }
        
        result = tour.create_mixed_tournament(
            selected_file,
            num_matches,      # نمرر عدد المباريات بدلاً من عدد المشاركين
            num_videos,
            ranking_type,
            bet_settings
        )
    else:
        # --- إنشاء بطولة عشوائية تقليدية ---
        # نستخدم دالة create_tournament_web القديمة التي تعتمد على num_participants
        # إذا لم يدخل المستخدم num_participants (استخدم num_matches_total)، نحسب العكس
        final_num_participants = 0
        if num_participants_str and num_participants_str.isdigit():
            final_num_participants = int(num_participants_str)
        else:
            final_num_participants = num_matches * num_videos
            
        try:
            result = tour.create_tournament_web(
                selected_file,
                final_num_participants,
                num_videos,
                ranking_type
            )
        except Exception as e:
            result = {'success': False, 'message': f"Error inputs: {e}"}

    # 5. عرض النتائج
    if result.get('success'):
        flash(result.get('message'), "success")
    else:
        flash(result.get('message'), "error")
        
    return redirect(url_for('tour_page'))

# END: MODIFIED SECTION
@app.route('/tour/continue', methods=['POST'])
def tour_continue():
    tournament_file = request.form.get('tournament_file')
    print(f"Attempting to continue tournament: {tournament_file}") # DEBUG
    if not tournament_file:
         flash("No tournament file selected to continue.", "error")
         print("Continue tournament called without selecting a file.") # DEBUG
         return redirect(url_for('tour_page'))

    # --- Check if file exists before calling continue ---
    file_path = os.path.join(JSON_FOLDER, tournament_file)
    if not os.path.exists(file_path):
         flash(f"Tournament file '{tournament_file}' not found.", "error")
         print(f"Tournament file not found for continuation: {tournament_file}") # DEBUG
         return redirect(url_for('tour_page'))
    # --- End check ---

    result = tour.continue_tournament_web(tournament_file) # Assume this loads the state

    if result.get('success'):
        flash(result.get('message'), "success")
        print(f"Tournament continuation successful for {tournament_file}. Redirecting to competition.") # DEBUG
        return redirect(url_for('competition', tournament_file=tournament_file))
    else:
        flash(result.get('message'), "error")
        print(f"Tournament continuation failed for {tournament_file}: {result.get('message')}") # DEBUG
        
        # --- START: Fix for tour.html rendering after error ---
        tournament_files = tour.list_tournament_files()
        available_files = tour.list_files(exclude_topcut=True)
        tournament_archive_raw = tour.load_tournament_archive() # Load the raw archive

        # Get current sort and view types from the request, similar to tour_page
        # When redirecting after an error, it's typically a GET request, so form might be empty.
        # We'll use defaults or try to infer from session if possible, but defaults are safer here.
        sort_type = request.form.get('sort_type', 'recent') # Default to 'recent'
        view_type = request.form.get('view_type', 'tournaments') # Default to 'tournaments'

        # Sort the tournaments before passing to template
        sorted_tournaments = tour.sort_tournaments_by_weight(tournament_archive_raw, sort_type)
        
        # Get individual videos (if needed for the 'videos' view)
        video_weights, video_counts = tour.get_individual_videos(tournament_archive_raw)
        sorted_videos = []
        if view_type == 'videos':
            if sort_type == "most_frequent":
                sorted_videos = sorted(video_weights.items(), key=lambda x: video_counts[x[0]], reverse=True)
            elif sort_type == "asc_weight":
                sorted_videos = sorted(video_weights.items(), key=lambda x: x[1])
            elif sort_type == "desc_weight":
                sorted_videos = sorted(video_weights.items(), key=lambda x: x[1], reverse=True)
            else: # Default for videos view if not specified
                sorted_videos = sorted(video_weights.items(), key=lambda x: x[0])


        return render_template('tour.html',
                             tournament_files=tournament_files,
                             available_files=available_files,
                             tournament_archive=sorted_tournaments, # Pass the sorted list
                             video_weights=sorted_videos, # Pass the sorted videos
                             video_counts=video_counts, # Pass video counts for display if needed
                             current_sort=sort_type,
                             current_view=view_type)
        # --- END: Fix for tour.html rendering after error ---

@app.route('/delete_tournament/<tournament_id>', methods=['POST'])
def delete_tournament(tournament_id):
    """حذف أو إعادة تسمية البطولة المحددة."""
    action = request.form.get('action', 'delete')
    
    try:
        if action == 'rename':
            # إعادة تسمية البطولة
            new_name = request.form.get('new_name', '').strip()
            if not new_name:
                flash("اسم البطولة الجديد لا يمكن أن يكون فارغاً.", "error")
                return redirect(url_for('tour_page'))
            
            # تحديث ملف الأرشيف
            archive_path = os.path.join('utilities', 'tournamentarchive.json')
            if os.path.exists(archive_path):
                try:
                    with open(archive_path, 'r') as f:
                        archive = json.load(f)
                    
                    if tournament_id in archive:
                        # نسخ البيانات إلى الاسم الجديد
                        archive[new_name] = archive[tournament_id]
                        # حذف الاسم القديم
                        del archive[tournament_id]
                        
                        with open(archive_path, 'w') as f:
                            json.dump(archive, f, indent=4)
                        
                        flash(f"تم تغيير اسم البطولة من '{tournament_id}' إلى '{new_name}' بنجاح.", "success")
                    else:
                        flash(f"البطولة '{tournament_id}' غير موجودة في الأرشيف.", "error")
                        
                except Exception as e:
                    flash(f"خطأ في تحديث الأرشيف: {e}", "danger")
            else:
                flash("ملف الأرشيف غير موجود.", "error")
                
        else:
            # الحذف (الكود الأصلي)
            file_path = os.path.join('utilities', tournament_id + '.json')
            file_deleted = False
            
            if os.path.exists(file_path):
                os.remove(file_path)
                file_deleted = True
            
            # حذف البطولة من الأرشيف
            archive_path = os.path.join('utilities', 'tournamentarchive.json')
            archive_updated = False
            
            if os.path.exists(archive_path):
                try:
                    with open(archive_path, 'r') as f:
                        archive = json.load(f)
                    
                    if tournament_id in archive:
                        del archive[tournament_id]
                        
                        with open(archive_path, 'w') as f:
                            json.dump(archive, f, indent=4)
                        archive_updated = True
                except Exception as e:
                    print(f"خطأ في تحديث الأرشيف: {e}")
            
            # رسائل النجاح/الفشل للحذف
            if file_deleted and archive_updated:
                flash(f"تم حذف البطولة {tournament_id} من الملف والأرشيف بنجاح.", "success")
            elif file_deleted:
                flash(f"تم حذف ملف البطولة {tournament_id} بنجاح.", "success")
            elif archive_updated:
                flash(f"تم حذف البطولة {tournament_id} من الأرشيف فقط.", "warning")
            else:
                flash(f"البطولة {tournament_id} غير موجودة.", "error")
                
    except Exception as e:
        flash(f"حدث خطأ أثناء تنفيذ العملية: {e}", "danger")
    
    return redirect(url_for('tour_page'))
# START: MODIFIED SECTION
@app.route('/filter_unplayed/<path:filename>')
def filter_unplayed(filename):
    """
    مسار API لفلترة المباريات غير الملعوبة من ملف بطولة.
    إذا كانت كل المباريات مكتملة، سيحاول إنهاء الجولة.
    """
    from utilities import tour
    import json

    # التحقق من اسم الملف لمنع المشاكل الأمنية
    if '..' in filename or filename.startswith('/'):
        return json.dumps({'error': 'اسم ملف غير صالح'}), 400

    filter_result = tour.filter_unplayed_matches(filename)
    
    if not filter_result.get('success'):
        return json.dumps({'error': filter_result.get('message')}), 500

    unplayed_matches = filter_result.get('data', [])

    if not unplayed_matches:
        # كل المباريات قد لُعبت. حان وقت إنهاء الجولة.
        print(f"No unplayed matches in {filename}. Attempting to finalize tournament round via continue_tournament_web.") # DEBUG
        # نستدعي نفس المنطق المستخدم في 'متابعة البطولة' والذي يُفترض أنه يعالج الإنهاء.
        finalization_result = tour.continue_tournament_web(filename)
        
        if finalization_result.get('success'):
            # نُرجع استجابة خاصة للواجهة الأمامية تفيد باكتمال الجولة
            return json.dumps({
                'status': 'completed',
                'message': finalization_result.get('message', 'اكتملت الجولة بنجاح!')
            })
        else:
            # فشل الإنهاء
            return json.dumps({
                'status': 'completion_failed',
                'message': finalization_result.get('message', 'حدث خطأ أثناء إنهاء الجولة.')
            }), 500
    else:
        # لا تزال هناك مباريات لم تُلعب. نرجعها داخل مفتاح 'data' للاتساق.
        return json.dumps({'data': unplayed_matches})
# END: MODIFIED SECTION

# START: MODIFIED SECTION
# أضف الدوال التالية في أي مكان مناسب في ملف app.py

@app.route('/serve_upscaled_media/<path:filename>')
def serve_upscaled_media(filename):
    """
    مسار مخصص لخدمة الملفات من مجلد الوسائط عالية الجودة.
    """
    return send_from_directory(UPSCALED_MEDIA_DIR, filename)

@app.context_processor
def utility_processor():
    """
    يجعل الدالة المساعدة متاحة لكل قوالب Jinja2.
    """
    def get_display_url(filename):
        """
        الدالة المساعدة الذكية.
        تتحقق من وجود نسخة عالية الجودة، وتُرجع المسار الصحيح.
        """
        if not filename:
            return "#" # إرجاع رابط غير صالح إذا كان اسم الملف فارغًا

        # بناء المسار للتحقق من وجود الملف عالي الجودة
        upscaled_path = os.path.join(UPSCALED_MEDIA_DIR, filename)

        if os.path.exists(upscaled_path):
            # إذا كان الملف موجودًا، أرجع المسار الخاص بالنسخة عالية الجودة
            return url_for('serve_upscaled_media', filename=filename)
        else:
            # إذا لم يكن موجودًا، أرجع المسار الأصلي كحل احتياطي
            return url_for('serve_video', filename=filename)
            
    return dict(get_display_url=get_display_url)



# START: MODIFIED SECTION - أضف هذه المسارات الجديدة
@app.route('/rename_tournament_file_action', methods=['POST'])
def rename_tournament_file_action():
    """
    إعادة تسمية ملف البطولة الفعلي على القرص فقط.
    """
    data = request.get_json()
    old_filename = data.get('old_filename')
    new_filename = data.get('new_filename')

    if not old_filename or not new_filename:
        return jsonify({'success': False, 'message': 'الأسماء مطلوبة.'}), 400

    # التأكد من أن الامتداد .json موجود
    if not new_filename.endswith('.json'):
        new_filename += '.json'

    result = tournaments_manager.rename_tournament_file(old_filename, new_filename)
    return jsonify(result)

@app.route('/rename_archive_entry_action', methods=['POST'])
def rename_archive_entry_action():
    """
    إعادة تسمية سجل البطولة داخل ملف الأرشيف فقط.
    """
    data = request.get_json()
    current_filename = data.get('filename') # اسم الملف الحالي (الذي يطابق مفتاح الأرشيف)
    new_archive_name = data.get('new_name')

    if not current_filename or not new_archive_name:
        return jsonify({'success': False, 'message': 'الأسماء مطلوبة.'}), 400

    # إزالة .json للتعامل مع مفاتيح الأرشيف
    current_key = current_filename.replace('.json', '')
    # الاسم الجديد للأرشيف عادة لا يحمل .json، لكن نترك الخيار للمستخدم
    # new_key = new_archive_name.replace('.json', '') 
    new_key = new_archive_name 

    result = tournaments_manager.rename_archive_entry(current_key, new_key)
    return jsonify(result)

@app.route('/create_archive_entry_action', methods=['POST'])
def create_archive_entry_action():
    """
    إنشاء سجل جديد في الأرشيف باسم الملف الحالي.
    """
    data = request.get_json()
    filename = data.get('filename')
    participants = data.get('participants', 32) # قيمة افتراضية

    if not filename:
        return jsonify({'success': False, 'message': 'اسم الملف مطلوب.'}), 400

    key = filename.replace('.json', '')
    
    result = tournaments_manager.create_archive_entry(key, participants)
# START: REPLACEMENT SECTION - (استبدل جميع دوال dashboard والرهان في app.py بهذا الكود)

from utilities.rank_tracker import get_rank_changes, save_rank_snapshot
from utilities.bet_manager import add_bet, get_proposed_match, remove_bet, load_bets, check_bet_status, clear_bets_by_status

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    data = load_data()
    if not data:
        flash("لا توجد بيانات.", "danger")
        return redirect(url_for('index'))
    
    # تحديث حالات الرهان
    all_bets_raw = load_bets()
    for vid_name in list(all_bets_raw.keys()):
        check_bet_status(vid_name, data)
    active_bets = load_bets() # إعادة التحميل

    # 1. القائمة المرتبة الكاملة
    sorted_videos_list = sorted(
        data.items(),
        key=lambda item: item[1].get('rating', 1000),
        reverse=True
    )
    current_ranks_map = {name: i+1 for i, (name, _) in enumerate(sorted_videos_list)}
    changes_data, _ = get_rank_changes(data)

    # 2. استقبال البارامترات (GET priority)
    search_query = request.args.get('search', '').strip()
    filter_type = request.args.get('filter', 'all')
    
    # معالجة النطاق المخصص (Custom Range)
    try:
        start_rank = int(request.args.get('start_rank', 1))
        end_rank = int(request.args.get('end_rank', 50))
    except ValueError:
        start_rank = 1
        end_rank = 50

    # معالجة POST لتغيير النطاق السريع (Dropdown)
    if request.method == 'POST':
        limit_val = request.form.get('limit')
        if limit_val:
            start_rank = 1
            end_rank = int(limit_val)

    # التأكد من صحة النطاق
    if start_rank < 1: start_rank = 1
    if end_rank < start_rank: end_rank = start_rank

    final_display_list = []

    # 3. منطق العرض
    if filter_type == 'bets_only':
        # عرض الرهانات فقط
        videos_with_bets = set(active_bets.keys())
        for video_name, info in sorted_videos_list:
            if video_name in videos_with_bets:
                final_display_list.append((video_name, info))
                
    elif search_query:
        # البحث
        for video_name, info in sorted_videos_list:
            is_match = False
            if search_query.isdigit():
                f_size = info.get('file_size')
                if f_size and str(f_size) == search_query:
                    is_match = True
            if not is_match:
                display_name = info.get('name', '')
                if search_query.lower() in video_name.lower() or (display_name and search_query.lower() in display_name.lower()):
                    is_match = True
            if is_match:
                final_display_list.append((video_name, info))

    else:
        # العرض العادي حسب النطاق
        start_index = start_rank - 1
        end_index = end_rank
        if start_index < len(sorted_videos_list):
            final_display_list = sorted_videos_list[start_index:end_index]
        else:
            final_display_list = []

    # 4. التجهيز للقالب
    rendered_list = []
    for video_name, info in final_display_list:
        change_info = changes_data.get(video_name, {'change': 0, 'prev_rank': '-'})
        user_bet = active_bets.get(video_name)
        
        rendered_list.append({
            'filename': video_name,
            'display_name': info.get('name', video_name),
            'file_size': info.get('file_size', 'N/A'),
            'rating': info.get('rating', 1000),
            'rank': current_ranks_map.get(video_name),
            'prev_rank': change_info['prev_rank'],
            'change': change_info['change'],
            'bet': user_bet
        })

    return render_template(
        'dashboard.html', 
        videos=rendered_list, 
        current_start=start_rank,
        current_end=end_rank,
        total_videos=len(data),
        search_query=search_query,
        current_filter=filter_type
    )

@app.route('/delete_bulk_bets', methods=['POST'])
def delete_bulk_bets():
    action_type = request.form.get('action_type')
    return_filter = request.form.get('return_filter', 'all')
    return_search = request.form.get('return_search', '')
    start_rank = request.form.get('start_rank', 1)
    end_rank = request.form.get('end_rank', 50)

    if action_type == 'delete_active':
        success, count = clear_bets_by_status('active')
        if success: flash(f"تم حذف {count} رهان نشط.", "success")
        else: flash("لا توجد رهانات نشطة لحذفها.", "warning")
            
    elif action_type == 'delete_completed':
        success, count = clear_bets_by_status('completed')
        if success: flash(f"تم حذف {count} رهان منتهي.", "success")
        else: flash("لا توجد رهانات منتهية لحذفها.", "warning")

    return redirect(url_for('dashboard', 
                            filter=return_filter, 
                            search=return_search,
                            start_rank=start_rank,
                            end_rank=end_rank))

@app.route('/place_bet', methods=['POST'])
def place_bet():
    # في حالة الاستدعاء من الداشبورد العادي
    video_name = request.form.get('video_name')
    target_rank = request.form.get('target_rank')
    
    # قراءة الفلاتر
    return_filter = request.form.get('return_filter', 'all')
    return_search = request.form.get('return_search', '')
    
    if not video_name or not target_rank:
        flash("بيانات الرهان ناقصة.", "danger")
        return redirect(url_for('dashboard', filter=return_filter, search=return_search))
        
    try:
        target_rank = int(target_rank)
        success, msg = add_bet(video_name, target_rank)
        if success:
            flash(msg, "success")
        else:
            flash(msg, "warning")
    except ValueError:
        flash("الترتيب يجب أن يكون رقماً صحيحاً.", "danger")
        
    return redirect(url_for('dashboard', filter=return_filter, search=return_search))

# نقطة API للرهان السريع من داخل صفحة المنافسة (AJAX)
@app.route('/api/place_bet', methods=['POST'])
def api_place_bet():
    try:
        data = request.get_json()
        video_name = data.get('video_name')
        target_rank = data.get('target_rank')
        
        if not video_name or not target_rank:
            return jsonify({'success': False, 'message': 'بيانات ناقصة'})
            
        target_rank = int(target_rank)
        success, msg = add_bet(video_name, target_rank)
        
        return jsonify({'success': success, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_bet', methods=['POST'])
def delete_bet_action():
    video_name = request.form.get('video_name')
    return_filter = request.form.get('return_filter', 'all')
    return_search = request.form.get('return_search', '')

    if remove_bet(video_name):
        flash("تم حذف الرهان.", "info")
    else:
        flash("لم يتم العثور على الرهان لحذفه.", "warning")
        
    return redirect(url_for('dashboard', filter=return_filter, search=return_search))


@app.route('/start_bet_match', methods=['POST'])
def start_bet_match():
    video_name = request.form.get('video_name')
    match_data = get_proposed_match(video_name)
    
    if match_data:
        session['competitions_queue'] = match_data
        first_match = match_data[0]
        session['competition_params'] = first_match
        
        data = load_data()
        
        # استدعاء choose_videos لتهيئة البيانات فقط (لأن الفيديوهات محددة مسبقاً)
        competition_videos_raw = choose_videos_function(
            data, 
            mode=1, 
            value=None, 
            num_videos=2, 
            use_dynamic_weighting=False,
            competition_type='betting_match', 
            specific_videos=first_match['videos'], 
            session=session
        )
        
        # تجهيز العرض
        processed_data_dict = load_processed_videos_data()
        video_folder = session.get('selected_folder')
        ranking_map = create_ranking_map(data)
        
        enriched_competition_videos = []
        for vid_name, rating, times_shown, tags, *_ in competition_videos_raw:
            display_name_from_db = data.get(vid_name, {}).get('name', '')
            enriched_video_info = {
                'name': vid_name, 
                'display_name': display_name_from_db,
                'rating': rating, 
                'times_shown': times_shown, 
                'tags': tags,
                'is_processed': False, 
                'weight': None,
                'rank': ranking_map.get(vid_name, 'N/A')
            }
            if video_folder:
                try:
                    full_video_path = os.path.join(video_folder, vid_name)
                    file_size = os.path.getsize(full_video_path)
                    if file_size in processed_data_dict:
                        enriched_video_info['is_processed'] = True
                        enriched_video_info['weight'] = processed_data_dict[file_size].get('total_weight')
                except: pass
            enriched_competition_videos.append(enriched_video_info)

        return render_template(
            'select_winner.html',
            competition_videos=enriched_competition_videos,
            num_videos=2,
            mode=1,
            ranking_type='winner_only',
            competition_type='betting_match',
            data=data
        )
    else:
        flash("حدث خطأ في تحضير المنافسة.", "danger")
        return redirect(url_for('dashboard'))
# END: REPLACEMENT SECTION
# return jsonify(result)
# END: MODIFIED SECTION

def main():
    # إنشاء المجلدات الضرورية عند بدء التشغيل
    os.makedirs(BACKUP_FOLDER, exist_ok=True)
    os.makedirs(STATUS_FOLDER, exist_ok=True)
    os.makedirs(UPSCALED_MEDIA_DIR, exist_ok=True) # <-- السطر الجديد هنا
    print(f"Backup folder ensured at {BACKUP_FOLDER}")
    print(f"Status folder ensured at {STATUS_FOLDER}")
    print(f"Upscaled media folder ensured at {UPSCALED_MEDIA_DIR}")
    if not os.path.exists(BACKUP_FOLDER):
        try:
            os.makedirs(BACKUP_FOLDER)
            print(f"Backup folder created at {BACKUP_FOLDER}")
        except Exception as e:
            print(f"Error creating backup folder: {e}")
    if not os.path.exists(STATUS_FOLDER):
        try:
            os.makedirs(STATUS_FOLDER)
            print(f"Status folder created at {STATUS_FOLDER}")
        except Exception as e:
            print(f"Error creating status folder: {e}")


if __name__ == "__main__":
    main()
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        # Ignore static route for cleaner output
        if rule.endpoint != 'static':
             print(f"- {rule.endpoint}: {rule}")
    print("Starting Flask app...") # DEBUG
# START: MODIFIED SECTION
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
