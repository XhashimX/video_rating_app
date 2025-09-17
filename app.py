import json
import sys
import os
from flask_session import Session
from flask import Flask, render_template, request, redirect, url_for, flash, session
from utilities.config import SECRET_KEY, BACKUP_FOLDER
from utilities.video_analyzer import update_names_analysis, analyze_names_data, get_video_display_name
from utilities.data_manager import load_data, save_data
from utilities import tournaments_manager
from utilities.file_manager import update_video_list, update_file_names, top_videos as render_top_videos, rename_all_videos as rename_all_videos_function
from utilities.helpers import video_handler
from utilities.routes import init_routes
# --- تعديل الاستيراد هنا ---
from utilities.video_selector import select_winner as select_winner_function, choose_videos_function
# --- نهاية التعديل ---
from utilities.analyze import analyze_data, Color, save_analysis_to_file
from utilities.data_manager import create_backup
from utilities import tour
from utilities.elo_calculator import update_ratings_multiple
app = Flask(__name__, template_folder='templates',
            static_folder='static')  # Added static folder
app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)  # هذا السطر ضروري لتفعيل Flask-Session
init_routes(app)

JSON_FOLDER = os.path.join("utilities")
STATUS_FOLDER = os.path.join("utilities", "status")

# تعريف مسار ملف البيانات الجديدة
PROCESSED_VIDEOS_FILE = 'C:/Users/Stark/Download/myhome/video_rating_app/utilities/processed_videos.json'

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
@app.route('/regroup_competitions', methods=['POST'])
def regroup_competitions():
    """
    يعيد تجميع الفيديوهات داخل ملف بطولة محدد وفقًا لحجم جديد للمسابقة.
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
        
        # تحميل بيانات الفيديو الرئيسية للحصول على التقييمات
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
        
        unique_videos = list(dict.fromkeys(all_videos))
        
        # 5. إنشاء قائمة المسابقات الجديدة
        new_competitions = []
        for i in range(0, len(unique_videos), new_num_videos):
            chunk = unique_videos[i:i + new_num_videos]
            
            if len(chunk) == new_num_videos:
                new_comp = template.copy()
                new_comp['videos'] = chunk
                new_comp['num_videos'] = new_num_videos
                
                # إنشاء قائمة التقييمات الجديدة لهذه المسابقة
                ratings_for_chunk = []
                for video_name in chunk:
                    # جلب التقييم من البيانات الرئيسية، مع قيمة افتراضية 1000
                    rating = main_data.get(video_name, {}).get('rating', 1000)
                    ratings_for_chunk.append(rating)
                
                # إضافة قائمة التقييمات إلى المسابقة الجديدة
                new_comp['rating'] = ratings_for_chunk
                
                # حذف الخصائص القديمة غير الضرورية
                new_comp.pop('file_size', None)
                
                new_competitions.append(new_comp)

        # 6. إعادة كتابة الملف الأصلي
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(new_competitions, f, indent=4, ensure_ascii=False)

        old_count = len(competitions)
        new_count = len(new_competitions)
        message = f"تمت إعادة تجميع {old_count} مسابقة إلى {new_count} مسابقة بنجاح!"
        flash(message, "success")
        return jsonify({'success': True, 'message': message})

    except json.JSONDecodeError:
        return jsonify({'success': False, 'message': 'فشل في قراءة الملف، تأكد من أنه ملف JSON صالح.'}), 500
    except Exception as e:
        print(f"Error in regroup_competitions: {e}")
        return jsonify({'success': False, 'message': f'حدث خطأ في الخادم: {e}'}), 500
# END: MODIFIED SECTION
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
@app.route('/competition', methods=['GET', 'POST'])
def competition():
    """
    معالجة طلبات المنافسة، سواء كانت تأتي من ملف JSON أو نموذج HTML.
    """
    print("\n--- Accessing /competition route ---") # DEBUG
    tournament_files = tour.list_tournament_files()

    if request.method == 'GET' and request.args.get('tournament_file'):
        # تم استلام اسم ملف البطولة من عنوان URL
        tournament_file = request.args.get('tournament_file')
        print(f"GET request with tournament_file param: {tournament_file}") # DEBUG
        try:
            with open(os.path.join("utilities", tournament_file), 'r') as f:
                json_data = f.read()
            print("Tournament file read successfully.") # DEBUG
        except Exception as e:
            flash(f"Error loading tournament file: {str(e)}", "danger")
            print(f"Error reading tournament file: {str(e)}") # DEBUG
            return render_template(
                'start_competition.html', tournament_files=tournament_files)

        if json_data:
            try:
                print("Parsing JSON from tournament file...") # DEBUG
                competitions = json.loads(json_data)
                print("JSON parsed successfully.") # DEBUG
                if not isinstance(competitions, list):
                    raise ValueError("JSON data must be a list.")

                data = load_data()
                if not data:
                    flash("No competition data available.", "danger")
                    print("Loaded data is empty when processing tournament file.") # DEBUG
                    return redirect(url_for('competition')) # Redirect to start page if no data

                session['competitions_queue'] = competitions
                print(f"Stored competitions queue in session, count: {len(competitions)}") # DEBUG
                if not competitions: # Handle empty queue
                     flash("Tournament file contains an empty list of competitions.", "warning")
                     print("Tournament file provided an empty list.") # DEBUG
                     return render_template('start_competition.html', tournament_files=tournament_files)

                current_competition = session['competitions_queue'].pop(0)
                session['competition_params'] = current_competition
                print(f"Popped first competition from queue. Params: {current_competition}") # DEBUG

                # Extract parameters for the first competition from JSON
                videos_from_json = current_competition.get('videos') # Get specific videos if provided
                mode = current_competition.get('mode', 1)
                num_videos = current_competition.get('num_videos', 2)
                ranking_type = current_competition.get('ranking_type', 'winner_only')
                use_dynamic_weighting = current_competition.get('use_dynamic_weighting', False)
                competition_type = current_competition.get('competition_type', 'random')
                value = current_competition.get('value') # This could be a number, dict, or string

                print(f"Starting competition from JSON - Mode: {mode}, Num Videos: {num_videos}, Value: {value}, Type: {competition_type}, Specific Videos: {videos_from_json}") # DEBUG

                # --- Call choose_videos directly here ---
                competition_videos_raw = choose_videos_function( # Changed variable name to indicate raw output
                    data,
                    mode,
                    value,
                    num_videos,
                    use_dynamic_weighting,
                    competition_type,
                    videos_from_json or [], # Pass specific videos if they exist
                    session=session
                )
                print(f"Videos chosen for the first JSON competition (raw): {competition_videos_raw}") # DEBUG

                # --- ابدأ كود دمج بيانات الفيديوهات المعالجة هنا (داخل كتلة try) ---
                processed_data_dict = load_processed_videos_data()
                video_folder = session.get('selected_folder') # نحتاج مسار المجلد للحصول على حجم الملف

                # Check if folder path is available
                if not video_folder:
                     print("WARNING: selected_folder not found in session. Cannot get file sizes.") # DEBUG
                     # Proceed without processed data info if folder not found

                # Create a new list with enriched video data
                # competition_videos_raw from choose_videos_function is (name, rating, times_shown, tags)
                enriched_competition_videos = []
                for vid_name, rating, times_shown, tags, *_ in competition_videos_raw:
                    # احصل على اسم العرض المخصص من البيانات الرئيسية (data)
                    display_name_from_db = data.get(vid_name, {}).get('name', '')

                    # Prepare default enriched data
                    enriched_video_info = {
                        'name': vid_name,  # احتفظ باسم الملف الأصلي هنا
                        'display_name': display_name_from_db, # أضف الاسم المخصص هنا
                        'rating': rating,
                        'times_shown': times_shown,
                        'tags': tags,
                        'is_processed': False, # Default to not processed
                        'weight': None         # Default weight to None
                    }

                    # Try to get file size and check against processed data
                    if video_folder: # Only proceed if we have the folder path
                        full_video_path = os.path.join(video_folder, vid_name)
                        try:
                            file_size = os.path.getsize(full_video_path)
                            # Check if this file size exists in our processed data dictionary
                            if file_size in processed_data_dict:
                                processed_info = processed_data_dict[file_size]
                                enriched_video_info['is_processed'] = True
                                enriched_video_info['weight'] = processed_info.get('total_weight')
                                print(f"Matched video '{vid_name}' with processed data (Size: {file_size}, Weight: {enriched_video_info['weight']})") # DEBUG
                            else:
                                print(f"No processed data found for video '{vid_name}' (Size: {file_size})") # DEBUG

                        except FileNotFoundError:
                            print(f"WARNING: Video file not found to get size: {full_video_path}") # DEBUG
                            # Continue without processed data info for this video
                        except Exception as e:
                            print(f"ERROR getting size for {full_video_path}: {e}") # DEBUG
                            # Continue without processed data info for this video


                    enriched_competition_videos.append(enriched_video_info)

                # Now, replace competition_videos_to_render with the new enriched list
                competition_videos_to_render = enriched_competition_videos
                print(f"Prepared {len(competition_videos_to_render)} enriched videos for rendering.") # DEBUG
                # --- انتهى كود دمج البيانات هنا ---


                if competition_videos_to_render and len(competition_videos_to_render) >= 2: # استخدم القائمة الجديدة هنا
                     print(f"Rendering select_winner.html for JSON GET with {len(competition_videos_to_render)} videos.") # DEBUG
                     # START: تعديل تمرير المعاملات إلى القالب
                     template_params_get = {
                         'competition_videos': competition_videos_to_render,
                         'num_videos': num_videos,
                         'mode': mode,
                         'ranking_type': ranking_type,
                         'competition_type': competition_type,
                         'data': data
                     }
                     # Pass value components correctly based on the structure from JSON
                     if isinstance(value, dict):
                         template_params_get.update(value) # Adds min_value, max_value, min_value1..., min_times_shown, max_times_shown, or tags
                     elif value is not None: # If value is a single number (for mode 3/4)
                         template_params_get['value'] = value

                     return render_template('select_winner.html', **template_params_get)
                     # END: تعديل تمرير المعاملات إلى القالب
                else:
                    flash("Not enough suitable videos found for the first competition from the tournament file.", "warning")
                    print(f"Failed to get enough videos ({len(competition_videos_raw) if competition_videos_raw else 0} found) for the first competition from the JSON file.") # DEBUG
                    # Clear potentially problematic session state if the first step fails
                    session.pop('competitions_queue', None)
                    session.pop('competition_params', None)
                    return render_template('start_competition.html', tournament_files=tournament_files)
                # --- End call choose_videos ---
            except json.JSONDecodeError:
                flash("Invalid JSON data in the tournament file.", "danger")
                print("JSON Decode Error from tournament file.") # DEBUG
                return render_template(
                    'start_competition.html', tournament_files=tournament_files)
            except ValueError as e:
                flash(str(e), "danger")
                print(f"Value Error processing tournament file JSON: {str(e)}") # DEBUG
                return render_template(
                    'start_competition.html', tournament_files=tournament_files)
            except Exception as e: # Catch other potential errors
                 flash(f"An unexpected error occurred: {str(e)}", "danger")
                 print(f"Unexpected error processing tournament file: {str(e)}") # DEBUG
                 import traceback
                 traceback.print_exc()
                 return render_template(
                    'start_competition.html', tournament_files=tournament_files)

    # Handle POST requests or GET requests without tournament_file param
    if not session.get('selected_folder'):
        flash("Please select a folder first.", "warning")
        print("No folder selected, redirecting to select_folder.") # DEBUG
        return redirect(url_for('select_folder'))

    # Initialize videos here for clarity, will be populated later
    videos_from_json = None # Use a different name to avoid conflict

    if request.method == 'POST':
        print("Received POST request for competition.") # DEBUG
        
        # --- START OF MODIFICATION ---
        # الأولوية الأولى: استخدام البيانات من مربع النص إذا لم تكن فارغة.
        # هذا هو التعديل الأساسي لحل المشكلة.
        json_data = request.form.get('json_data')
        
        # الأولوية الثانية: إذا كان مربع النص فارغاً، حاول استخدام الملف المختار من القائمة.
        if not json_data or not json_data.strip():
            tournament_file = request.form.get('tournament_file')
            if tournament_file:
                print(f"Textarea is empty, loading from selected file: {tournament_file}") # DEBUG
                try:
                    with open(os.path.join("utilities", tournament_file), 'r') as f:
                        json_data = f.read()
                    print("Read JSON data from file as fallback.") # DEBUG
                except Exception as e:
                    flash(f"Error loading tournament file from POST: {str(e)}", "danger")
                    print(f"Error reading tournament file from POST: {str(e)}") # DEBUG
                    return render_template('start_competition.html', tournament_files=tournament_files)
        else:
             print("Using JSON data provided in the textarea.") # DEBUG
        # --- END OF MODIFICATION ---

        if json_data:
            try:
                print("Parsing JSON from POST request...") # DEBUG
                competitions = json.loads(json_data)
                print("JSON parsed successfully from POST.") # DEBUG
                if not isinstance(competitions, list):
                    raise ValueError("JSON data must be a list.")

                data = load_data()
                if not data:
                    flash("No competition data available.", "danger")
                    print("Loaded data is empty when processing POST JSON.") # DEBUG
                    return redirect(url_for('competition'))

                session['competitions_queue'] = competitions
                print(f"Stored competitions queue from POST, count: {len(competitions)}") # DEBUG
                if not competitions: # Handle empty queue
                     flash("JSON data contains an empty list of competitions.", "warning")
                     print("JSON data provided an empty list.") # DEBUG
                     return render_template('start_competition.html', tournament_files=tournament_files)

                current_competition = session['competitions_queue'].pop(0)
                session['competition_params'] = current_competition
                print(f"Popped first competition from POST queue. Params: {current_competition}") # DEBUG

                videos_from_json = current_competition.get('videos') # Update variable name
                mode = current_competition.get('mode', 1)
                num_videos = current_competition.get('num_videos', 2)
                ranking_type = current_competition.get('ranking_type', 'winner_only')
                use_dynamic_weighting = current_competition.get('use_dynamic_weighting', False)
                competition_type = current_competition.get('competition_type', 'random')
                value = current_competition.get('value') # This could be a number, dict, or string

                print(f"Starting competition from POST JSON - Mode: {mode}, Num Videos: {num_videos}, Value: {value}, Type: {competition_type}, Specific Videos: {videos_from_json}") # DEBUG

                # --- Common logic after getting parameters (either from JSON or form) ---
                data = load_data()
                if not data:
                    flash("No competition data available.", "danger")
                    print("Loaded data is empty before choosing videos.") # DEBUG
                    return render_template('start_competition.html', tournament_files=tournament_files)

                # Now, use the determined parameters to choose videos
                # Parameters are already set in variables (mode, value, num_videos, etc.)
                # and stored in session['competition_params']
                print(f"Calling choose_videos with: Mode={mode}, Value={value}, NumVids={num_videos}, DynWeight={use_dynamic_weighting}, CompType={competition_type}, SpecificVids={videos_from_json}") # DEBUG
                competition_videos_raw = choose_videos_function( # Changed variable name
                    data,
                    mode,
                    value,
                    num_videos,
                    use_dynamic_weighting,
                    competition_type,
                    videos_from_json or [], # Use specific videos if from JSON
                    session=session
                )
                print(f"Videos chosen (raw): {competition_videos_raw}") # DEBUG

                # --- ابدأ كود دمج بيانات الفيديوهات المعالجة هنا (داخل كتلة try) ---
                processed_data_dict = load_processed_videos_data()
                video_folder = session.get('selected_folder') # نحتاج مسار المجلد للحصول على حجم الملف

                # Check if folder path is available
                if not video_folder:
                     print("WARNING: selected_folder not found in session. Cannot get file sizes.") # DEBUG
                     # Proceed without processed data info if folder not found

                # Create a new list with enriched video data
                # competition_videos_raw from choose_videos_function is (name, rating, times_shown, tags)
                enriched_competition_videos = []
                for vid_name, rating, times_shown, tags, *_ in competition_videos_raw:
                    # احصل على اسم العرض المخصص من البيانات الرئيسية (data)
                    display_name_from_db = data.get(vid_name, {}).get('name', '')

                    # Prepare default enriched data
                    enriched_video_info = {
                        'name': vid_name, # احتفظ باسم الملف الأصلي هنا
                        'display_name': display_name_from_db, # أضف الاسم المخصص هنا
                        'rating': rating,
                        'times_shown': times_shown,
                        'tags': tags,
                        'is_processed': False, # Default to not processed
                        'weight': None         # Default weight to None
                    }

                    # Try to get file size and check against processed data
                    if video_folder: # Only proceed if we have the folder path
                        full_video_path = os.path.join(video_folder, vid_name)
                        try:
                            file_size = os.path.getsize(full_video_path)
                            # Check if this file size exists in our processed data dictionary
                            if file_size in processed_data_dict:
                                processed_info = processed_data_dict[file_size]
                                enriched_video_info['is_processed'] = True
                                enriched_video_info['weight'] = processed_info.get('total_weight')
                                print(f"Matched video '{vid_name}' with processed data (Size: {file_size}, Weight: {enriched_video_info['weight']})") # DEBUG
                            else:
                                print(f"No processed data found for video '{vid_name}' (Size: {file_size})") # DEBUG

                        except FileNotFoundError:
                            print(f"WARNING: Video file not found to get size: {full_video_path}") # DEBUG
                            # Continue without processed data info for this video
                        except Exception as e:
                            print(f"ERROR getting size for {full_video_path}: {e}") # DEBUG
                            # Continue without processed data info for this video


                    enriched_competition_videos.append(enriched_video_info)

                # Now, replace competition_videos with the new enriched list
                competition_videos_to_render = enriched_competition_videos
                print(f"Prepared {len(competition_videos_to_render)} enriched videos for rendering.") # DEBUG
                # --- انتهى كود دمج البيانات هنا ---

                if competition_videos_to_render and len(competition_videos_to_render) >= 2: # استخدم القائمة الجديدة هنا
                    print(f"Rendering select_winner.html with {len(competition_videos_to_render)} videos from POST JSON.") # DEBUG
                     # START: تعديل تمرير المعاملات إلى القالب
                    template_params_post_json = {
                        'competition_videos': competition_videos_to_render,
                        'num_videos': num_videos,
                        'mode': mode,
                        'ranking_type': ranking_type,
                        'competition_type': competition_type,
                        'data': data
                    }
                    # Pass value components correctly based on the structure from JSON
                    if isinstance(value, dict):
                        template_params_post_json.update(value) # Adds min_value, max_value, min_value1..., min_times_shown, max_times_shown, or tags
                    elif value is not None: # If value is a single number (for mode 3/4)
                        template_params_post_json['value'] = value

                    return render_template('select_winner.html', **template_params_post_json)
                    # END: تعديل تمرير المعاملات إلى القالب
                else:
                    flash("Not enough suitable videos found for the selected criteria from JSON data.", "warning")
                    print(f"Failed to get enough videos ({len(competition_videos_raw) if competition_videos_raw else 0} found) based on POST JSON criteria.") # DEBUG
                     # Clear potentially problematic session state if the first step fails
                    session.pop('competitions_queue', None)
                    session.pop('competition_params', None)
                    return render_template('start_competition.html', tournament_files=tournament_files)

            except json.JSONDecodeError:
                flash("Invalid JSON data provided.", "danger")
                print("JSON Decode Error from POST data.") # DEBUG
                return render_template(
                    'start_competition.html', tournament_files=tournament_files)
            except ValueError as e:
                flash(str(e), "danger")
                print(f"Value Error processing POST JSON: {str(e)}") # DEBUG
                return render_template(
                    'start_competition.html', tournament_files=tournament_files)
            except Exception as e: # Catch other potential errors
                 flash(f"An unexpected error occurred processing POST JSON: {str(e)}", "danger")
                 print(f"Unexpected error processing POST JSON: {str(e)}") # DEBUG
                 import traceback
                 traceback.print_exc()
                 return render_template(
                    'start_competition.html', tournament_files=tournament_files)

        else: # No JSON data, process form parameters
            # ... كود معالجة النموذج ...
            mode = int(request.form.get('mode', 1))
            num_videos = int(request.form.get('num_videos', 2))
            ranking_type = request.form.get('ranking_type')
            use_dynamic_weighting = request.form.get('use_dynamic_weighting') == 'true'
            competition_type = request.form.get('competition_type')
            value = None
            videos_from_json = None # Ensure it's None if using form params

            # --- Logic to extract 'value' based on 'mode' from form ---
            if mode == 8:
                print("Mode 8 selected, processing ranges.") # DEBUG
                min_value1_str = request.form.get('min_value1')
                max_value1_str = request.form.get('max_value1')
                min_value2_str = request.form.get('min_value2')
                max_value2_str = request.form.get('max_value2')
                if all([min_value1_str, max_value1_str, min_value2_str, max_value2_str]):
                    try:
                        value = {
                            'min_value1': float(min_value1_str), 'max_value1': float(max_value1_str),
                            'min_value2': float(min_value2_str), 'max_value2': float(max_value2_str)
                        }
                        print(f"Mode 8 ranges parsed: {value}") # DEBUG
                    except ValueError:
                        flash("Please enter valid numeric values for the ranges.", "danger")
                        print("ValueError parsing mode 8 ranges.") # DEBUG
                        return render_template('start_competition.html', tournament_files=tournament_files)
                else:
                    flash("Please enter values for both ranges.", "danger")
                    print("Missing values for mode 8 ranges.") # DEBUG
                    return render_template('start_competition.html', tournament_files=tournament_files)
            elif mode in [5, 6]:
                print(f"Mode {mode} selected, processing min/max.") # DEBUG
                min_value_str = request.form.get('min_value')
                max_value_str = request.form.get('max_value')
                if min_value_str and max_value_str:
                    try:
                        value = {'min_value': float(min_value_str), 'max_value': float(max_value_str)}
                        print(f"Mode {mode} min/max parsed: {value}") # DEBUG
                    except ValueError:
                        flash("Please enter valid numeric values for min/max.", "danger")
                        print(f"ValueError parsing mode {mode} min/max.") # DEBUG
                        return render_template('start_competition.html', tournament_files=tournament_files)
                else:
                    flash("Please enter both minimum and maximum values.", "danger")
                    print(f"Missing values for mode {mode} min/max.") # DEBUG
                    return render_template('start_competition.html', tournament_files=tournament_files)
            elif mode in [3, 4]:
                print(f"Mode {mode} selected, processing single value.") # DEBUG
                value_str = request.form.get('value')
                if value_str:
                    try:
                        value = float(value_str)
                        print(f"Mode {mode} value parsed: {value}") # DEBUG
                    except ValueError:
                        flash("Please enter a valid numeric value.", "danger")
                        print(f"ValueError parsing mode {mode} value.") # DEBUG
                        return render_template('start_competition.html', tournament_files=tournament_files)
                # Allow mode 3/4 without value if needed, handle in choose_videos
                # else:
                #     flash("Please enter a value.", "danger")
                #     print(f"Missing value for mode {mode}.") # DEBUG
                #     return render_template('start_competition.html', tournament_competition_files=tournament_files)
            # START: إضافة منطق للأوضاع الجديدة 9 و 10 من النموذج
            elif mode == 9: # وضع مرات الظهور
                print(f"Mode 9 selected, processing times_shown range.") # DEBUG
                min_times_str = request.form.get('min_times_shown')
                max_ts_str = request.form.get('max_times_shown')
                if min_times_str is not None and max_ts_str is not None: # Use is not None to allow 0
                    try:
                        value = {
                            'min_times_shown': int(min_times_str),
                            'max_times_shown': int(max_ts_str)
                        }
                        print(f"Mode 9 times_shown range parsed: {value}") # DEBUG
                    except ValueError:
                        flash("Please enter valid numeric values for times_shown range.", "danger")
                        print("ValueError parsing mode 9 times_shown range.") # DEBUG
                        return render_template('start_competition.html', tournament_files=tournament_files)
                else:
                    flash("Please enter both minimum and maximum times_shown values.", "danger")
                    print("Missing values for mode 9 times_shown range.") # DEBUG
                    return render_template('start_competition.html', tournament_files=tournament_files)
            elif mode == 10: # وضع الوسوم
                print(f"Mode 10 selected, processing tags input.") # DEBUG
                # Use the ID from the form ('tags_value_mode_input' as specified in the HTML update)
                tags_input_str = request.form.get('tags_value_mode_input')
                if tags_input_str is not None: # Use is not None to allow empty string for value
                     # The actual parsing/cleaning happens in choose_videos_function
                     value = {'tags': tags_input_str.strip()}
                     print(f"Mode 10 tags parsed: {value}") # DEBUG
                     # Note: We allow empty string here; choose_videos_function will handle it
                else:
                    flash("Please enter the required tags.", "danger")
                    print("Missing tags input for mode 10.") # DEBUG
                    return render_template('start_competition.html', tournament_files=tournament_files)
            # END: إضافة منطق للأوضاع الجديدة 9 و 10

            # Store these parameters in session for potential reuse
            # Store the specific value structure based on the mode
            session['competition_params'] = {
                'mode': mode, 'value': value, 'num_videos': num_videos,
                'ranking_type': ranking_type, 'use_dynamic_weighting': use_dynamic_weighting,
                'competition_type': competition_type
            }
            print(f"Stored competition params from form in session: {session['competition_params']}") # DEBUG
            # Clear any leftover queue if we are starting manually
            session.pop('competitions_queue', None)
            print("Cleared competitions_queue as starting manually from form.") # DEBUG

            # --- Common logic after getting parameters (either from JSON or form) ---
            data = load_data()
            if not data:
                flash("No competition data available.", "danger")
                print("Loaded data is empty before choosing videos.") # DEBUG
                return render_template('start_competition.html', tournament_files=tournament_files)

            # Now, use the determined parameters to choose videos
            # Parameters are already set in variables (mode, value, num_videos, etc.)
            # and stored in session['competition_params']
            print(f"Calling choose_videos with: Mode={mode}, Value={value}, NumVids={num_videos}, DynWeight={use_dynamic_weighting}, CompType={competition_type}, SpecificVids={videos_from_json}") # DEBUG
            competition_videos_raw = choose_videos_function( # Changed variable name
                data,
                mode,
                value, # Use the parsed value directly
                num_videos,
                use_dynamic_weighting,
                competition_type,
                videos_from_json or [], # Use specific videos if from JSON (will be empty here for form)
                session=session
            )
            print(f"Videos chosen (raw): {competition_videos_raw}") # DEBUG

            # --- ابدأ كود دمج بيانات الفيديوهات المعالجة هنا (داخل الجزء الذي لا يحتوي على json_data) ---
            processed_data_dict = load_processed_videos_data()
            video_folder = session.get('selected_folder') # نحتاج مسار المجلد للحصول على حجم الملف

            # Check if folder path is available
            if not video_folder:
                 print("WARNING: selected_folder not found in session. Cannot get file sizes.") # DEBUG
                 # Proceed without processed data info if folder not found

            # Create a new list with enriched video data
            # competition_videos_raw from choose_videos_function is (name, rating, times_shown, tags)
            enriched_competition_videos = []
            for vid_name, rating, times_shown, tags, *_ in competition_videos_raw:
                # احصل على اسم العرض المخصص من البيانات الرئيسية (data)
                display_name_from_db = data.get(vid_name, {}).get('name', '')

                # Prepare default enriched data
                enriched_video_info = {
                    'name': vid_name, # احتفظ باسم الملف الأصلي هنا
                    'display_name': display_name_from_db, # أضف الاسم المخصص هنا
                    'rating': rating,
                    'times_shown': times_shown,
                    'tags': tags,
                    'is_processed': False, # Default to not processed
                    'weight': None         # Default weight to None
                }

                # Try to get file size and check against processed data
                if video_folder: # Only proceed if we have the folder path
                    full_video_path = os.path.join(video_folder, vid_name)
                    try:
                        file_size = os.path.getsize(full_video_path)
                        # Check if this file size exists in our processed data dictionary
                        if file_size in processed_data_dict:
                            processed_info = processed_data_dict[file_size]
                            enriched_video_info['is_processed'] = True
                            enriched_video_info['weight'] = processed_info.get('total_weight')
                            print(f"Matched video '{vid_name}' with processed data (Size: {file_size}, Weight: {enriched_video_info['weight']})") # DEBUG
                        else:
                            print(f"No processed data found for video '{vid_name}' (Size: {file_size})") # DEBUG

                    except FileNotFoundError:
                        print(f"WARNING: Video file not found to get size: {full_video_path}") # DEBUG
                        # Continue without processed data info for this video
                    except Exception as e:
                        print(f"ERROR getting size for {full_video_path}: {e}") # DEBUG
                        # Continue without processed data info for this video


                enriched_competition_videos.append(enriched_video_info)

            # Now, replace competition_videos with the new enriched list
            competition_videos_to_render = enriched_competition_videos
            print(f"Prepared {len(competition_videos_to_render)} enriched videos for rendering.") # DEBUG
            # --- انتهى كود دمج البيانات هنا ---


            if competition_videos_to_render and len(competition_videos_to_render) >= 2: # استخدم القائمة الجديدة هنا
                print(f"Rendering select_winner.html with {len(competition_videos_to_render)} videos from form POST.") # DEBUG
                # START: تعديل تمرير المعاملات إلى القالب
                template_params = {
                    'competition_videos': competition_videos_to_render,
                    'num_videos': num_videos,
                    'mode': mode,
                    'ranking_type': ranking_type,
                    'competition_type': competition_type,
                    'data': data
                }
                # Pass value components correctly based on the parsed value structure
                if isinstance(value, dict):
                    template_params.update(value) # Adds min_value, max_value, min_value1..., min_times_shown, max_times_shown, or tags
                elif value is not None: # If value is a single number (for mode 3/4)
                    template_params['value'] = value

                return render_template('select_winner.html', **template_params)
                # END: تعديل تمرير المعاملات إلى القالب
            else:
                flash("Not enough suitable videos found for the selected criteria.", "warning")
                print(f"Failed to get enough videos ({len(competition_videos_raw) if competition_videos_raw else 0} found) based on initial criteria.") # DEBUG
                 # Clear potentially problematic session state if the first step fails
                session.pop('competitions_queue', None)
                session.pop('competition_params', None)
                return render_template('start_competition.html', tournament_files=tournament_files)


    # If it's a GET request without a tournament file param, just show the form
    print("Rendering start_competition.html (GET request or fallback).") # DEBUG
    # Clear session state if we are just loading the start page clean
    session.pop('competitions_queue', None)
    session.pop('competition_params', None)
    session.pop('last_winner', None) # Also clear last winner
    print("Cleared session state (queue, params, last_winner) on loading start page.") # DEBUG

    # Sort tournament files alphabetically before rendering
    sorted_tournament_files = sorted(tournament_files)

    return render_template('start_competition.html', tournament_files=sorted_tournament_files)


@app.route('/select_winner', methods=['POST'])
def select_winner():
    """
    Processes the winner selection form submission.
    Updates ratings based on the result and moves to the next competition if in a queue.
    If no queue, starts a new competition with the same parameters.
    """
    print("\n--- Accessing /select_winner route ---") # DEBUG
    print(f"Request.form: {request.form}") # DEBUG


    if not session.get('selected_folder'):
        flash("Please select a folder first.", "warning")
        print("ERROR: No folder selected in session.") # DEBUG
        return redirect(url_for('select_folder'))

    # --- Handle Tag Updates (Do this first as it might be the only action) ---
    print("\n--- Processing Tag Updates ---") # DEBUG
    data = load_data() # Load data to update tags
    if not data:
        # This is a fallback, usually data will exist if a folder was selected
        flash("No competition data available to update tags.", "danger")
        print("No data loaded for tag updates.") # DEBUG
        # We can't proceed, redirect to competition start
        return redirect(url_for('competition'))

    # Get the list of video names that were originally displayed from the form
    original_video_names_in_competition = request.form.getlist('videos')
    print(f"Original video names in competition (for tag update): {original_video_names_in_competition}") # DEBUG

    if not original_video_names_in_competition:
        flash("No videos were submitted in the form. Cannot process tags or results.", "danger")
        print("ERROR: Form submitted without any 'videos' values.") # DEBUG
        # Clear state and redirect to competition start
        session.pop('competitions_queue', None)
        session.pop('competition_params', None)
        session.pop('last_winner', None)
        return redirect(url_for('competition'))


    tag_updates_made = False
    try: # Wrap tag processing in try-except
        for index, video_name in enumerate(original_video_names_in_competition, start=1): # Use 1-based index for form fields
            if video_name in data:
                # Get tags from the corresponding form input (tag_1, tag_2, etc.)
                tags_input = request.form.get(f'tag_{index}', None) # Default to None if not found

                if tags_input is not None:
                    # Process tags: split, strip, remove empty
                    # Treat '∅' specifically - if present, clear all other tags
                    processed_tags = []
                    if '∅' not in tags_input.split(','): # If '∅' is not selected
                         processed_tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                    # else: processed_tags remains empty, effectively clearing tags

                    new_tags_str = ','.join(sorted(list(set(processed_tags)))) # Clean and sort tags

                    # Update only if tags changed
                    if data[video_name].get('tags', '') != new_tags_str:
                        data[video_name]['tags'] = new_tags_str
                        print(f"Updated tags for {video_name} to: '{new_tags_str}'") # DEBUG
                        tag_updates_made = True
                    else:
                         print(f"Tags for {video_name} unchanged.") # DEBUG

            else:
                print(f"WARNING: Video '{video_name}' from form not found in data during tag update.") # DEBUG
        print("--- End Tag Processing ---")
    except Exception as e:
         flash(f"An error occurred while updating tags: {e}", "danger")
         print(f"ERROR during tag processing: {e}") # DEBUG
         import traceback # Ensure traceback is imported here if needed
         traceback.print_exc()
         # We can attempt to proceed with ranking even if tag update failed


    # --- Handle Special Action Buttons ---
    if request.form.get('tag_only') == 'true':
        print("Action: Apply tags only.") # DEBUG
        # Data was already loaded and tags processed.
        # Save data only if tags were actually updated.
        if tag_updates_made:
            try:
                 save_data(data) # Save just the tag changes
                 flash("Tags updated successfully!", "success")
                 print("Data saved after 'tag_only' action.") # DEBUG
            except Exception as e:
                 flash(f"Error saving data after tag update: {e}", "danger")
                 print(f"ERROR saving data after 'tag_only': {e}") # DEBUG
        else:
             flash("No tag changes detected.", "info")
             print("No tags updated, skipping data save.") # DEBUG

        # For 'tag_only', we usually want to go back to the competition start page.
        # Or, if part of a tournament, maybe stay on the same round?
        # The requirement was "automatic competition after end". 'tag_only' *interrupts* this.
        # Let's redirect to the start page after 'tag_only'.
        print("Redirecting to competition start page after 'tag_only'.") # DEBUG
        # Clear queue/params as we exited the normal flow
        session.pop('competitions_queue', None)
        session.pop('competition_params', None)
        session.pop('last_winner', None)
        return redirect(url_for('competition'))


    # Note: The 'skip_competition' logic was already inside a try block in the original code
    # So the merge code for skip_competition should be placed inside its existing try block as well.
    if request.form.get('skip_competition') == 'true':
        print("Action: Skip competition.") # DEBUG
        # Do not process ratings, do not save (unless tags were updated?), do not determine winner for Elo.
        # Just find the *next* competition parameters and try to load it.
        flash("Competition skipped.", "info")
        print("Skipping competition results processing and saving.") # DEBUG

        # --- Prepare for Next Competition (after skipping) ---
        # Determine parameters for the *next* competition
        next_competition_params = None
        competitions_queue = session.get('competitions_queue')

        # Get the parameters from the *just skipped* round, which are already in session['competition_params']
        # This is the base for the next round if no queue item exists or the queue finishes.
        params_from_skipped_round = session.get('competition_params')
        print(f"Skip: Using params from the skipped round as base: {params_from_skipped_round}") # DEBUG


        if competitions_queue:
            print("Skip: Competitions queue exists. Popping next item.") # DEBUG
            if competitions_queue: # Check if list is not empty
                 next_competition_params = competitions_queue.pop(0)
                 # Store these new params as the current ones for potential reuse later
                 session['competition_params'] = next_competition_params
                 print(f"Skip: Popped next params from queue: {next_competition_params}. Remaining: {len(competitions_queue)}") # DEBUG
            else:
                 # This case happens if the last item was popped and processed successfully
                 print("Skip: competitions_queue key exists but is empty after pop. Clearing queue.") # DEBUG
                 session.pop('competitions_queue')
                 flash("Tournament queue finished (via skip).", "info")
                 # If queue is empty after trying to pop, fall back to repeating the last criteria
                 # The session['competition_params'] already holds the params of the round that was skipped (params_from_skipped_round)
                 # We should use these params to try and find the next round.
                 next_competition_params = params_from_skipped_round
                 print(f"Skip: Queue finished, reusing params from skipped round: {next_competition_params}") # DEBUG
        else:
            print("Skip: No competitions queue. Reusing parameters from skipped round.") # DEBUG
            # No queue, reuse the parameters of the round just skipped
            next_competition_params = params_from_skipped_round
            # No need to update session['competition_params'] here, they are already the ones we want to repeat


        # --- Reconstruct value for Modes 9 and 10 if repeating the last round (no queue) ---
        # This logic is needed specifically if we are *repeating* the last round's criteria
        # and that round was Mode 9 or 10, because the form submitted contains the needed value.
        # If we popped from the queue, the value should already be correct in next_competition_params.
        reconstructed_next_value = next_competition_params.get('value') # Default to value from params

        # Read mode from the form of the *just skipped* competition
        mode_skipped_round = request.form.get('mode', type=int) # This is the mode of the round that was just displayed and skipped.

        # If we are reusing the params and the mode was 9 or 10, reconstruct value from form
        # Check if the queue is empty *after* trying to pop.
        # Note: session.get('competitions_queue') will be None if it was popped and the list became empty.
        if not session.get('competitions_queue') and mode_skipped_round in [9, 10]:
            print(f"Skip: Reconstructing value from form as repeating mode {mode_skipped_round}.") # DEBUG
            if mode_skipped_round == 9:
                min_ts_str = request.form.get('min_times_shown')
                max_ts_str = request.form.get('max_times_shown')
                if min_ts_str is not None and max_ts_str is not None:
                     try:
                          reconstructed_next_value = {
                              'min_times_shown': int(min_ts_str),
                              'max_times_shown': int(max_ts_str)
                          }
                          print(f"Skip: Reconstructed next_value for mode 9: {reconstructed_next_value}") # DEBUG
                     except ValueError:
                          print("Skip: Error reconstructing next_value for mode 9 from form. Falling back to session value.") # DEBUG
                          # Fallback to whatever was originally stored in session['competition_params']['value']
                          reconstructed_next_value = params_from_skipped_round.get('value')
                else:
                     print("Skip: Missing times_shown values in form for mode 9 reconstruction. Falling back to session value.") # DEBUG
                     reconstructed_next_value = params_from_skipped_round.get('value')

            elif mode_skipped_round == 10:
                 tags_str = request.form.get('tags_value_input')
                 if tags_str is not None:
                      reconstructed_next_value = {'tags': tags_str.strip()}
                      print(f"Skip: Reconstructed next_value for mode 10: {reconstructed_next_value}") # DEBUG
                 else:
                      print("Skip: Missing tags value in form for mode 10 reconstruction. Falling back to session value.") # DEBUG
                      reconstructed_next_value = params_from_skipped_round.get('value')
        else:
             print("Skip: Not repeating last round's params or mode is not 9 or 10. No value reconstruction needed from form.") # DEBUG


        # The final value to use for choose_videos is `reconstructed_next_value`
        final_next_value_for_choose_videos = reconstructed_next_value
        print(f"Skip: Final value for choose_videos: {final_next_value_for_choose_videos}") # DEBUG


        # --- Try to load videos for the next competition ---
        # Need latest data in case the user manually updated files outside the app
        data_for_next_round = load_data()
        if not data_for_next_round:
            flash("Cannot start next competition: No data loaded.", "danger")
            print("ERROR Skip: Failed to load data for next round.") # DEBUG
            # Clear state and redirect to start
            session.pop('competitions_queue', None)
            session.pop('competition_params', None)
            session.pop('last_winner', None)
            return redirect(url_for('competition'))

        if not next_competition_params:
             # This is a problem state - no queue and no stored params
             flash("Error: Could not determine parameters for the next competition to skip to.", "danger")
             print("CRITICAL ERROR Skip: No queue and no competition_params found.") # DEBUG
             # Clear state and redirect to start
             session.pop('competitions_queue', None)
             session.pop('competition_params', None)
             session.pop('last_winner', None)
             return redirect(url_for('competition'))


        # Extract parameters for the next round from next_competition_params (excluding value, using the reconstructed one)
        next_mode = next_competition_params.get('mode', 1)
        next_num_videos = next_competition_params.get('num_videos', 2)
        next_ranking_type = next_competition_params.get('ranking_type', 'winner_only')
        next_use_dynamic_weighting = next_competition_params.get('use_dynamic_weighting', False)
        next_competition_type = next_competition_params.get('competition_type', 'random')
        next_specific_videos = next_competition_params.get('videos', []) # Specific videos for the *next* round if defined


        print(f"--- Skip: Preparing choose_videos for Next Competition ---") # DEBUG
        # Use final_next_value_for_choose_videos
        print(f"Skip: Next Params: Mode={next_mode}, Value={final_next_value_for_choose_videos}, NumVids={next_num_videos}, RankType={next_ranking_type}, DynWeight={next_use_dynamic_weighting}, CompType={next_competition_type}, SpecificVids={next_specific_videos}") # DEBUG
        print(f"Skip: Session state: last_winner={session.get('last_winner')}") # DEBUG


        new_competition_videos_raw = choose_videos_function(
            data_for_next_round, # Use the potentially reloaded data
            next_mode,
            final_next_value_for_choose_videos, # Use the final determined value
            next_num_videos,
            next_use_dynamic_weighting,
            next_competition_type,
            next_specific_videos,
            session=session # Pass session for ring mode logic
        )

        print(f"Skip: Result from choose_videos: {new_competition_videos_raw}") # DEBUG
        num_videos_selected = len(new_competition_videos_raw) if new_competition_videos_raw else 0
        print(f"Skip: Number of videos selected: {num_videos_selected}") # DEBUG


        # Check if enough videos were found for the next competition
        if new_competition_videos_raw and num_videos_selected >= 2:
             print(f"Skip: Sufficient videos found ({num_videos_selected}). Rendering select_winner.html.") # DEBUG

             # Format the selected videos for the template (needs name, rating, times_shown, tags)
             # This part was already preparing a list of tuples.
             # We need to convert this to a list of dictionaries *after* choosing videos
             # and before rendering, and add the processed data info.

             # --- ابدأ كود دمج بيانات الفيديوهات المعالجة هنا (داخل حالة skip الناجحة) ---
             processed_data_dict = load_processed_videos_data()
             video_folder = session.get('selected_folder') # نحتاج مسار المجلد للحصول على حجم الملف

             if not video_folder:
                  print("WARNING Skip: selected_folder not found in session. Cannot get file sizes.") # DEBUG

             # Create a new list with enriched video data
             # new_competition_videos_raw is (name, rating, times_shown, tags from choose_videos_function)
             # We should get the latest data from data_for_next_round anyway.
             enriched_competition_videos = []
             for vid_name, _, _, _, *_ in new_competition_videos_raw: # Iterate through names from selected videos
                 # Use the data_for_next_round dictionary as the source of truth for latest values and tags
                 video_data_entry = data_for_next_round.get(vid_name, {})

                 # احصل على اسم العرض المخصص من البيانات الرئيسية (data_for_next_round)
                 display_name_from_db = video_data_entry.get('name', '')

                 enriched_video_info = {
                     'name': vid_name, # احتفظ باسم الملف الأصلي هنا
                     'display_name': display_name_from_db, # أضف الاسم المخصص هنا
                     'rating': video_data_entry.get('rating', 1000.0), # Get latest rating
                     'times_shown': video_data_entry.get('times_shown', 0), # Get latest times_shown
                     'tags': video_data_entry.get('tags', ''),           # Get latest tags
                     'is_processed': False, # Default
                     'weight': None         # Default
                 }

                 if video_folder:
                     full_video_path = os.path.join(video_folder, vid_name)
                     try:
                         file_size = os.path.getsize(full_video_path)
                         if file_size in processed_data_dict:
                             processed_info = processed_data_dict[file_size]
                             enriched_video_info['is_processed'] = True
                             enriched_video_info['weight'] = processed_info.get('total_weight')
                             print(f"Skip: Matched video '{vid_name}' with processed data (Size: {file_size}, Weight: {enriched_video_info['weight']})") # DEBUG
                         else:
                             print(f"Skip: No processed data found for video '{vid_name}' (Size: {file_size})") # DEBUG

                     except FileNotFoundError:
                         print(f"WARNING Skip: Video file not found to get size: {full_video_path}") # DEBUG
                     except Exception as e:
                         print(f"ERROR Skip getting size for {full_video_path}: {e}") # DEBUG

                 enriched_competition_videos.append(enriched_video_info)

             competition_videos_to_render = enriched_competition_videos
             print(f"Skip: Prepared {len(competition_videos_to_render)} enriched videos for rendering.") # DEBUG
             # --- انتهى كود دمج البيانات هنا ---


             # START: تعديل تمرير المعاملات إلى القالب select_winner.html للمنافسة التالية (بعد التخطي)
             template_params_skip = {
                'competition_videos': competition_videos_to_render,
                'num_videos': next_num_videos,
                'mode': next_mode,
                'ranking_type': next_ranking_type,
                'competition_type': next_competition_type,
                'data': data_for_next_round
             }
             # Pass value components correctly based on final_next_value_for_choose_videos
             if isinstance(final_next_value_for_choose_videos, dict):
                 template_params_skip.update(final_next_value_for_choose_videos)
             elif final_next_value_for_choose_videos is not None:
                 template_params_skip['value'] = final_next_value_for_choose_videos

             return render_template('select_winner.html', **template_params_skip)
             # END: تعديل تمرير المعاملات

        else:
            # Could not find videos even for the skipped-to competition
            num_found = len(new_competition_videos_raw) if new_competition_videos_raw else 0
            flash(f"Skipped, but could not find enough videos ({num_found} found, need at least 2) for the next competition based on its criteria.", "warning")
            print(f"WARNING Skip: Insufficient videos ({num_found}) found for the *next* round after skipping.") # DEBUG
            # Clear state and redirect to start
            session.pop('competitions_queue', None)
            session.pop('competition_params', None)
            session.pop('last_winner', None)
            print("Skip: Cleared session state due to insufficient videos for next round.") # DEBUG
            return redirect(url_for('competition'))


    # --- Process regular competition results (if not tag_only or skip) ---
    print("Action: Processing competition results (ratings update).") # DEBUG
    # The main processing logic (rating updates, stats, etc.) is already wrapped in a try block.
    # The part that prepares the *next* competition's videos needs the enrichment.
    try: # Wrap main logic in try-except from the original code

        # ... كود معالجة نتائج المنافسة وتحديث البيانات ...
        # هذا الكود لا يتغير، هو فقط يقرأ ويحدث الـ data dictionary

        # Data was already loaded for tag updates, check again just in case
        if not data:
            flash("No competition data found for rating update.", "danger")
            print("ERROR: Failed to load data before updating ratings.") # DEBUG
            # Clear state and redirect to start
            session.pop('competitions_queue', None)
            session.pop('competition_params', None)
            session.pop('last_winner', None)
            return redirect(url_for('competition'))

        # Reload competition parameters from the form hidden fields (sent from select_winner.html)
        # These represent the parameters of the competition *just completed*
        mode = request.form.get('mode', type=int)
        num_videos = request.form.get('num_videos', type=int)
        ranking_type = request.form.get('ranking_type')
        competition_type = request.form.get('competition_type') # Get type of completed competition
        value = None # Reconstruct value based on mode

        # Reconstruct 'value' based on hidden fields specific to the mode used
        if mode == 8:
            value = {
                'min_value1': request.form.get('min_value1', type=float), 'max_value1': request.form.get('max_value1', type=float),
                'min_value2': request.form.get('min_value2', type=float), 'max_value2': request.form.get('max_value2', type=float)
            }
        elif mode in [5, 6]:
            value = {'min_value': request.form.get('min_value', type=float), 'max_value': request.form.get('max_value', type=float)}
        elif mode in [3, 4]:
             val_str = request.form.get('value')
             value = float(val_str) if val_str is not None and val_str != '' else None # Handle empty string for value
        # START: إعادة بناء value للأوضاع 9 و 10 من الحقول المخفية للنموذج المكتمل
        elif mode == 9:
            min_ts_str = request.form.get('min_times_shown')
            max_ts_str = request.form.get('max_times_shown')
            if min_ts_str is not None and max_ts_str is not None:
                 try:
                      value = {
                          'min_times_shown': int(min_ts_str),
                          'max_times_shown': int(max_ts_str)
                      }
                 except ValueError:
                      print("Error parsing hidden times_shown values from form for mode 9.") # DEBUG
                      value = None # Indicate error or missing value
            # Note: If value is None here, choose_videos_function for the NEXT round might behave differently.
            # This `value` is primarily for storing in session['competition_params'] for the *next* round.
        elif mode == 10:
             tags_str = request.form.get('tags_value_input') # Get the value from the hidden input
             if tags_str is not None:
                  value = {'tags': tags_str.strip()}
             # Note: Allowing empty string for tags value if submitted
        # END: إعادة بناء value للأوضاع 9 و 10


        print(f"Parameters from completed competition form: Mode={mode}, NumVids={num_videos}, RankType={ranking_type}, CompType={competition_type}, Value={value}") # DEBUG

        # `original_video_names_in_competition` already retrieved for tags

        ranks = [] # This list was used in the old winner_only logic, keeping for rank mode below
        winner_vid = None # Explicitly track the winner

        print(f"Videos submitted: {original_video_names_in_competition}") # DEBUG


        if ranking_type == 'winner_only':
            winner_vid = request.form.get('winner') # Get the winner
            print(f"Winner Only mode. Winner selected: {winner_vid}") # DEBUG
            if not winner_vid:
                flash("Please select a winner.", "danger")
                print("ERROR: Winner_only mode, but no winner selected in form.") # DEBUG
                session.pop('competitions_queue', None)
                session.pop('competition_params', None)
                session.pop('last_winner', None)
                return redirect(url_for('competition'))

            if winner_vid not in original_video_names_in_competition:
                 flash("Selected winner was not part of the competition videos.", "danger")
                 print(f"ERROR: Submitted winner '{winner_vid}' not in submitted video list: {original_video_names_in_competition}") # DEBUG
                 session.pop('competitions_queue', None)
                 session.pop('competition_params', None)
                 session.pop('last_winner', None)
                 return redirect(url_for('competition'))


            # === START OF MODIFICATION ===
            # Prepare the list for update_ratings_multiple for winner_only
            # Winner gets rank_index 0, all losers get rank_index 1

            ranked_videos_for_update_sorted = [] # This list will contain (video_name, rating, rank_index)

            # Add the winner first with rank_index 0
            if winner_vid in data:
                 current_rating = float(data[winner_vid].get('rating', 1000.0))
                 ranked_videos_for_update_sorted.append((winner_vid, current_rating, 0)) # Winner is rank 0
                 print(f"Prepared winner for ELO update: ({winner_vid}, {current_rating:.2f}, 0)") # DEBUG
            else:
                 flash(f"Error processing winner-only result: Winner video {winner_vid} not found in data.", "danger")
                 print(f"CRITICAL ERROR: Winner video {winner_vid} from form not found in data for winner-only update.") # DEBUG
                 session.pop('competitions_queue', None)
                 session.pop('competition_params', None)
                 session.pop('last_winner', None)
                 return redirect(url_for('competition'))

            # Add the losers with rank_index 1
            for vid in original_video_names_in_competition:
                if vid != winner_vid:
                    if vid in data:
                        current_rating = float(data[vid].get('rating', 1000.0))
                        ranked_videos_for_update_sorted.append((vid, current_rating, 1)) # Losers are rank 1
                        print(f"Prepared loser for ELO update: ({vid}, {current_rating:.2f}, 1)") # DEBUG
                    else:
                        flash(f"Error processing winner-only result: Loser video {vid} not found in data.", "danger")
                        print(f"CRITICAL ERROR: Loser video {vid} from form not found in data for winner-only update.") # DEBUG
                        # Decided to redirect on finding missing video, can adjust this behavior
                        session.pop('competitions_queue', None)
                        session.pop('competition_params', None)
                        session.pop('last_winner', None)
                        return redirect(url_for('competition'))


            # Note: The list is already "sorted" by rank_index (0 first, then all 1s)
            # The order *among* the losers (those with rank_index 1) no longer implies ranking between them
            # The update_ratings_multiple function will handle the rank_index 1 group as a tie.

            print(f"Prepared ranked list for ELO update (winner_only - MODIFIED): {ranked_videos_for_update_sorted}") # DEBUG
            # === END OF MODIFICATION ===


        else: # Rank mode - This section remains the same
             print("Rank mode. Reading ranks...") # DEBUG
             submitted_ranks = {}
             # Loop through original video names to associate submitted ranks
             for i, video_name in enumerate(original_video_names_in_competition):
                 # Assuming rank input names are rank_1, rank_2 etc. corresponding to the video order in the form
                 rank_val_str = request.form.get(f'rank_{i+1}') # Get rank_1, rank_2 etc. as string
                 if rank_val_str is not None and rank_val_str != '':
                      try:
                           submitted_ranks[video_name] = int(rank_val_str)
                      except ValueError:
                           flash(f"Invalid rank submitted for video {i+1} ('{video_name}'): '{rank_val_str}'. Rank must be a number.", "danger")
                           print(f"ERROR: Invalid rank '{rank_val_str}' for video {i+1} ({video_name}).") # DEBUG
                           session.pop('competitions_queue', None)
                           session.pop('competition_params', None)
                           session.pop('last_winner', None)
                           return redirect(url_for('competition'))
                 else:
                      flash(f"Missing rank for video {i+1} ('{video_name}'). Please rank all videos.", "danger")
                      print(f"ERROR: Missing rank for video {i+1} ({video_name}) in rank mode.") # DEBUG
                      session.pop('competitions_queue', None)
                      session.pop('competition_params', None)
                      session.pop('last_winner', None)
                      return redirect(url_for('competition')) # Or re-render select_winner

             # Ensure all videos have a rank assigned
             if len(submitted_ranks) != len(original_video_names_in_competition):
                  flash("Not all videos were ranked.", "danger")
                  print(f"ERROR: Number of ranks ({len(submitted_ranks)}) doesn't match number of videos ({len(original_video_names_in_competition)}).") # DEBUG
                  session.pop('competitions_queue', None)
                  session.pop('competition_params', None)
                  session.pop('last_winner', None)
                  return redirect(url_for('competition'))

             # Create the list of videos with their ratings and *submitted* ranks
             videos_with_submitted_ranks = []
             for vid_name, submitted_rank in submitted_ranks.items():
                  if vid_name in data:
                       current_rating = float(data[vid_name].get('rating', 1000.0))
                       videos_with_submitted_ranks.append((vid_name, current_rating, submitted_rank))
                  else:
                       flash(f"Error processing ranking result: Video {vid_name} not found in data.", "danger")
                       print(f"CRITICAL ERROR: Video {vid_name} from form not found in data for rank update.") # DEBUG
                       session.pop('competitions_queue', None)
                       session.pop('competition_params', None)
                       session.pop('last_winner', None)
                       return redirect(url_for('competition'))


             # Sort by the submitted rank (ascending) to get the final ranked order for ELO update
             videos_with_submitted_ranks.sort(key=lambda item: item[2])

             # Prepare the list for update_ratings_multiple. It needs (video_name, current_rating, rank_index)
             # The rank_index is the 0-based position in the *sorted* list.
             ranked_videos_for_update_sorted = []
             for i, (vid_name, current_rating, submitted_rank) in enumerate(videos_with_submitted_ranks):
                  ranked_videos_for_update_sorted.append((vid_name, current_rating, i)) # i is the 0-based rank index

             print(f"Prepared ranked list for ELO update (rank mode): {ranked_videos_for_update_sorted}") # DEBUG

             # Determine winner(s) for 'last_winner' session variable (the one with the lowest submitted rank)
             if videos_with_submitted_ranks:
                  lowest_submitted_rank = videos_with_submitted_ranks[0][2] # Rank of the first video in the sorted list
                  winners = [vid for vid, rating, rank in videos_with_submitted_ranks if rank == lowest_submitted_rank]
                  winner_vid = winners[0] if winners else None # Take the first winner in case of tie
                  print(f"Winner(s) in rank mode (lowest submitted rank {lowest_submitted_rank}): {winners}. Using {winner_vid} for session.") # DEBUG
             else:
                  winner_vid = None
                  print("No videos available to determine winner in rank mode.") # DEBUG


        # Check if we have enough videos to proceed with rating updates
        if len(ranked_videos_for_update_sorted) < 2:
             flash("Not enough valid videos found in the ranking after processing submitted data.", "danger")
             print(f"Only {len(ranked_videos_for_update_sorted)} valid videos found for ranking after processing.") # DEBUG
             session.pop('competitions_queue', None)
             session.pop('competition_params', None)
             session.pop('last_winner', None)
             return redirect(url_for('competition'))

        # ===> Get original ratings BEFORE ELO calculation for the Post-ELO Adjustment <===
        original_ratings_before_elo = {
            vid_name: data.get(vid_name, {}).get('rating', 1000.0) # استخدم data للحصول على التقييم الحالي قبل التحديث
            for vid_name, _, _ in ranked_videos_for_update_sorted # استخدم قائمة الفيديوهات المعدة للتحديث
        }
        print(f"Original ratings before ELO for this round: {original_ratings_before_elo}") # DEBUG


        # --- Update Ratings (This modifies the 'data' dictionary) ---
        # The update_ratings_multiple function will now correctly handle the rank_index=1 group as a tie in winner_only mode.
        # Pass is_winner_only=True if ranking_type is 'winner_only'
        update_ratings_multiple(ranked_videos_for_update_sorted, data)
        print("Ratings updated by ELO calculator.") # DEBUG


        # --- Apply Post-ELO Adjustment ---
        print("\n--- Applying Post-ELO Adjustment based on final rank order ---") # DEBUG
        # The list used here reflects the order after ELO calculation (winner rank 0, losers rank 1)
        # We can reuse ranked_videos_for_update_sorted for this, as its structure now represents this.
        # Note: The order *within* the rank_index=1 group doesn't matter for the Post-ELO adjustment logic either.
        # We still need the names in order to process the winner vs all losers.
        ranked_video_names_final_order_for_adjustment = [item[0] for item in ranked_videos_for_update_sorted]
        print(f"Rank order for Post-ELO Adjustment: {ranked_video_names_final_order_for_adjustment}") # DEBUG

        # === START OF MODIFICATION (Post-ELO Adjustment Loop) ===

        # Check if there's a winner (rank_index 0) and at least one loser (rank_index 1)
        if ranked_videos_for_update_sorted and ranked_videos_for_update_sorted[0][2] == 0:
            winner_video_name = ranked_video_names_final_order_for_adjustment[0]
            print(f"Applying Post-ELO Adjustment for Winner ({winner_video_name}) vs Losers.") # DEBUG

            # Iterate through all videos *after* the winner in the list
            for i in range(1, len(ranked_video_names_final_order_for_adjustment)):
                video_a_name = winner_video_name  # Video A is always the winner
                video_b_name = ranked_video_names_final_order_for_adjustment[i] # Video B is a loser from the list

                # Find the rank_index for Video B (should be 1 in winner_only mode)
                # This check is mainly for safety, assuming list is structured correctly
                rank_index_a = 0 # Winner is always rank_index 0
                rank_index_b = None
                for name, _, rank_idx in ranked_videos_for_update_sorted:
                     if name == video_b_name:
                          rank_index_b = rank_idx
                          break # Found Video B

                # Proceed only if Video B is valid and is indeed a loser (rank_index is 1 or greater)
                if video_a_name in data and video_b_name in data and rank_index_b is not None and rank_index_a < rank_index_b: # Ensure A is actually ranked higher than B
                    # Get the NEW ratings *after* the initial Elo calculation
                    rating_a_after_elo = data[video_a_name].get('rating', 1500.0)
                    rating_b_after_elo = data[video_b_name].get('rating', 1500.0)

                    print(f"Comparing Winner ({video_a_name}, After Elo: {rating_a_after_elo:.2f}) with Loser ({video_b_name}, After Elo: {rating_b_after_elo:.2f})...") # DEBUG

                    # --- START: Post-ELO Adjustment Logic (Applies only if rank_index_a < rank_index_b) ---
                    original_rating_a = original_ratings_before_elo.get(video_a_name)
                    original_rating_b = original_ratings_before_elo.get(video_b_name)

                    # Check for the specific exception case (Original 1000 winner beats higher original)
                    # This applies to Winner (rank_index 0) vs Loser (rank_index 1)
                    if (original_rating_a is not None and original_rating_b is not None and
                        original_rating_a < original_rating_b and
                        abs(original_rating_a - 1000.0) < 0.01):

                        print(f"  EXCEPTION CASE MET: Winner '{video_a_name}' (orig {original_rating_a}) beat higher rated '{video_b_name}' (orig {original_rating_b}). Applying special adjustment.") # DEBUG
                        # The Winner (video_a_name) takes the Loser's original rating (original_rating_b)
                        data[video_a_name]['rating'] = original_rating_b
                        # The Loser (video_b_name) keeps their rating *after* the initial ELO calculation (rating_b_after_elo)
                        print(f"  Adjusted (Exception): '{video_a_name}' new rating: {data[video_a_name]['rating']:.2f}, '{video_b_name}' rating remains {rating_b_after_elo:.2f} (from Elo).") # DEBUG
                        # No need to continue to standard adjustment for this pair, exception is applied.
                        continue # Move to the next loser

                    # Standard adjustment condition: Higher ranked video has lower rating *after* Elo calculation
                    if rating_a_after_elo < rating_b_after_elo:
                        print(f"  Standard adjustment condition met: Winner '{video_a_name}' ({rating_a_after_elo:.2f}) "
                              f"< Loser '{video_b_name}' ({rating_b_after_elo:.2f}). Applying standard adjustment.") # DEBUG
                        data[video_a_name]['rating'] = rating_b_after_elo
                        data[video_b_name]['rating'] = (rating_a_after_elo + rating_b_after_elo) / 2.0
                        print(f"  Adjusted (Standard): '{video_a_name}' new rating: {data[video_a_name]['rating']:.2f}, '{video_b_name}' new rating: {data[video_b_name]['rating']:.2f}") # DEBUG
                    else:
                        print("  Condition not met for this pair. No post-ELO adjustment.") # DEBUG

                    # --- END: Post-ELO Adjustment Logic ---

                elif rank_index_a == rank_index_b:
                     # This case should not happen in the loop comparing winner (rank 0) to subsequent items (rank 1).
                     # But as a safeguard:
                     print(f"Unexpected: Winner ({video_a_name}) compared to video {video_b_name} with same rank index ({rank_index_a}). Skipping.") # DEBUG
                else: # video_a_name not in data or video_b_name not in data or rank_index_b is None or rank_index_a >= rank_index_b (shouldn't happen)
                     print(f"Skipping comparison between winner ({video_a_name}) and {video_b_name} - issue found.") # DEBUG

        else:
            print("Skipping Post-ELO Adjustment - Winner not found at rank 0 or no losers.") # DEBUG


        # === END OF MODIFICATION (Post-ELO Adjustment Loop) ===


        print("--- End of Post-ELO Adjustment ---") # هذا السطر موجود في كودك

        # --- تحديد الفائز والخاسرين بوضوح لإحصائيات الأسماء ---
        explicit_winner_id = None
        explicit_loser_ids = []

        if ranking_type == 'winner_only':
            explicit_winner_id = winner_vid # هذا هو الفائز الذي تم اختياره
            explicit_loser_ids = [vid for vid in original_video_names_in_competition if vid != explicit_winner_id]
        else: # Rank mode
            # في وضع Rank mode، الفائز هو صاحب أدنى رتبة (أول فيديو في قائمة ranked_videos_for_update_sorted)
            if ranked_videos_for_update_sorted:
                explicit_winner_id = ranked_videos_for_update_sorted[0][0] # اسم الفيديو الفائز
                # باقي الفيديوهات هي خاسرة في هذا السياق
                explicit_loser_ids = [item[0] for item in ranked_videos_for_update_sorted[1:]]

        # تحديث إحصائيات الأسماء فقط إذا كان هناك فائز وخاسرون واضحون
        if explicit_winner_id and explicit_loser_ids:
            # هنا نمرر data (البيانات الرئيسية المحدثة) للحصول على الـ display name الصحيح
            update_names_analysis(explicit_winner_id, explicit_loser_ids, original_video_names_in_competition, data)
        else:
            print("WARNING: Could not determine explicit winner/losers for names analysis. Skipping update.") # DEBUG

        # --- Update Win/Loss and Times Shown --- # هذا السطر التالي بعد الإضافة
        # This section remains the same
        print("\n--- Updating Win/Loss and Times Shown ---") # DEBUG
        for vid in original_video_names_in_competition:
             if vid in data:
                  # Initialize stats if they don't exist (should ideally be done on initial load/scan)
                  data[vid].setdefault('total_wins', 0)
                  data[vid].setdefault('total_losses', 0)
                  data[vid].setdefault('times_shown', 0)
                  data[vid].setdefault('win_streak', 0) # Ensure streaks are initialized
                  data[vid].setdefault('loss_streak', 0) # Ensure streaks are initialized

                  # Increment win/loss based on the determined winner_vid for *this* competition
                  if winner_vid is not None: # Only update win/loss if a winner was determined
                       if vid == winner_vid:
                           data[vid]['total_wins'] += 1
                           # Streaks are handled within update_ratings_multiple now based on pair comparisons
                           # No need to update win_streak/loss_streak here anymore based on overall winner
                           print(f"{vid}: Win count incremented to {data[vid]['total_wins']}") # DEBUG
                       else:
                           data[vid]['total_losses'] += 1
                           # Streaks handled in update_ratings_multiple
                           print(f"{vid}: Loss count incremented to {data[vid]['total_losses']}") # DEBUG
                  else:
                       # If no winner determined (e.g. insufficient videos), don't update win/loss
                       print(f"No winner determined for this round, skipping win/loss update for {vid}.") # DEBUG


                  # Recalculate win rate
                  total_matches = data[vid]['total_wins'] + data[vid]['total_losses']
                  data[vid]['win_rate'] = (data[vid]['total_wins'] / total_matches) if total_matches > 0 else 0.0
                  print(f"{vid}: New win rate: {data[vid]['win_rate']:.2f}") # DEBUG


                  # Increment times shown for *all* participants in this round
                  data[vid]['times_shown'] = data[vid].get('times_shown', 0) + 1 # Ensure default is 0 if missing
                  print(f"{vid}: Times shown incremented to {data[vid]['times_shown']}") # DEBUG

             else:
                  print(f"WARNING: Video {vid} not found in data during win/loss/times_shown update loop.") # DEBUG

        print("--- End Win/Loss and Times Shown Updates ---")

        # Save the updated data (ratings, stats, tags, streaks)
        try:
             save_data(data)
             create_backup(data) # Create a backup after saving
             print("Data saved and backup created successfully after results processing.") # DEBUG
             flash("Ratings, stats, and tags updated successfully!", "success")
        except Exception as e:
             flash(f"Error saving data after processing results: {e}", "danger")
             print(f"ERROR saving data after results processing: {e}") # DEBUG
             # Decide if we should stop or try to proceed. Let's proceed.


        # --- Prepare for Next Competition (Automatic Continuation) ---
        # Update last winner in session *if* a winner was determined for this completed round
        if winner_vid:
            print(f"Updating session 'last_winner': {winner_vid}") # DEBUG
            session['last_winner'] = winner_vid
        else:
             # If no winner (e.g., 0 videos submitted, though checked), clear last_winner
             session.pop('last_winner', None)
             print("No winner determined for this completed round, cleared session 'last_winner'.") # DEBUG


        print("\n--- Preparing for Next Competition ---") # DEBUG
        next_competition_params = None
        competitions_queue = session.get('competitions_queue')

        # Logic to get parameters for the *next* round:
        # If queue exists, pop from it. Otherwise, reuse params from the *just completed* round (stored in session['competition_params'] from when it started)
        params_from_completed_round = session.get('competition_params')
        print(f"Next Comp: Using params from the completed round as base: {params_from_completed_round}") # DEBUG


        if competitions_queue:
            print("Next Comp: Competitions queue exists. Popping next item.") # DEBUG
            if competitions_queue: # Check if list is not empty
                 next_competition_params = competitions_queue.pop(0)
                 # Store these new params as the current ones for potential reuse later OR if the queue finishes
                 session['competition_params'] = next_competition_params # Update session with the *next* item's params
                 print(f"Next Comp: Popped next params from queue: {next_competition_params}. Remaining queue size: {len(competitions_queue)}") # DEBUG
            else:
                 # This happens if the queue was processed and is now empty
                 print("Next Comp: competitions_queue key exists but is empty after pop. Clearing queue.") # DEBUG
                 session.pop('competitions_queue')
                 flash("Tournament queue finished.", "info")
                 # If queue is empty after trying to pop, fall back to repeating the last criteria
                 # The session['competition_params'] already holds the params of the round that just finished (params_from_completed_round)
                 next_competition_params = params_from_completed_round # Reuse the parameters of the finished round
                 print(f"Next Comp: Queue finished, reusing last competition_params: {next_competition_params}") # DEBUG
        else:
            print("Next Comp: No competitions queue found.") # DEBUG
            # No queue, reuse the parameters of the round just finished
            # These are already stored in session['competition_params'] from when the round started
            next_competition_params = params_from_completed_round
            if not next_competition_params:
                 # This is a problem state - no queue and no stored params at all
                 flash("Error: Could not determine parameters for the next competition.", "danger")
                 print("CRITICAL ERROR Next Comp: No queue and no competition_params found in session.") # DEBUG
                 # Clear state and redirect to start
                 session.pop('competitions_queue', None)
                 session.pop('competition_params', None)
                 session.pop('last_winner', None)
                 return redirect(url_for('competition'))
            # The competition_params are already the ones from the just-finished round
            # No need to update session['competition_params'] here, they are already correct
            print(f"Next Comp: No queue, reusing current session['competition_params']: {next_competition_params}") # DEBUG


        # --- Reconstruct value for Modes 9 and 10 if repeating the last round (no queue) ---
        # This logic is needed specifically if we are *repeating* the last round's criteria
        # and that round was Mode 9 or 10, because the form submitted contains the needed value.
        # If we popped from the queue, the value should already be correct in next_competition_params.
        reconstructed_next_value = next_competition_params.get('value') # Default to value from params

        # Read mode from the form of the *just completed* competition
        # mode variable already contains this at the start of the try block
        # `mode` variable here is the mode of the competition that just finished processing.

        # If we are reusing the params (queue is empty after pop) and the mode was 9 or 10, reconstruct value from form
        # Check if the queue is empty *after* trying to pop.
        if not session.get('competitions_queue') and mode in [9, 10]:
            print(f"Next Comp: Reconstructing value from form as repeating mode {mode}.") # DEBUG
            if mode == 9:
                min_ts_str = request.form.get('min_times_shown')
                max_ts_str = request.form.get('max_times_shown')
                if min_ts_str is not None and max_ts_str is not None:
                     try:
                          reconstructed_next_value = {
                              'min_times_shown': int(min_ts_str),
                              'max_times_shown': int(max_ts_str)
                          }
                          print(f"Next Comp: Reconstructed next_value for mode 9: {reconstructed_next_value}") # DEBUG
                     except ValueError:
                          print("Next Comp: Error reconstructing next_value for mode 9 from form. Falling back to session value.") # DEBUG
                          # Fallback to whatever was originally stored in session['competition_params']['value']
                          reconstructed_next_value = params_from_completed_round.get('value')
                else:
                     print("Next Comp: Missing times_shown values in form for mode 9 reconstruction. Falling back to session value.") # DEBUG
                     reconstructed_next_value = params_from_completed_round.get('value')

            elif mode == 10:
                 tags_str = request.form.get('tags_value_input')
                 if tags_str is not None:
                      reconstructed_next_value = {'tags': tags_str.strip()}
                      print(f"Next Comp: Reconstructed next_value for mode 10: {reconstructed_next_value}") # DEBUG
                 else:
                      print("Next Comp: Missing tags value in form for mode 10 reconstruction. Falling back to session value.") # DEBUG
                      reconstructed_next_value = params_from_completed_round.get('value')
        else:
             print("Next Comp: Not repeating last round's params or mode is not 9 or 10. No value reconstruction needed from form.") # DEBUG


        # The final value to use for choose_videos is `reconstructed_next_value`
        final_next_value_for_choose_videos = reconstructed_next_value
        print(f"Next Comp: Final value for choose_videos: {final_next_value_for_choose_videos}") # DEBUG


        # --- Call choose_videos to get the next set ---
        # Ensure we use the *latest* data after updates
        data_for_next_round = load_data()
        if not data_for_next_round:
            flash("Cannot start next competition: No data loaded after processing results.", "danger")
            print("ERROR Next Comp: Failed to load data for next round.") # DEBUG
            # Clear state and redirect to start
            session.pop('competitions_queue', None)
            session.pop('competition_params', None)
            session.pop('last_winner', None)
            return redirect(url_for('competition'))

        # Extract parameters for the next round from next_competition_params (excluding value, using the reconstructed one)
        next_mode = next_competition_params.get('mode', 1)
        next_num_videos = next_competition_params.get('num_videos', 2)
        next_ranking_type = next_competition_params.get('ranking_type', 'winner_only')
        next_use_dynamic_weighting = next_competition_params.get('use_dynamic_weighting', False)
        next_competition_type = next_competition_params.get('competition_type', 'random')
        next_specific_videos = next_competition_params.get('videos', []) # Specific videos for the *next* round if defined


        print(f"--- Next Comp: Preparing choose_videos Call ---") # DEBUG
        # Use final_next_value_for_choose_videos
        print(f"Next Comp: Params: Mode={next_mode}, Value={final_next_value_for_choose_videos}, NumVids={next_num_videos}, RankType={next_ranking_type}, DynWeight={next_use_dynamic_weighting}, CompType={next_competition_type}, SpecificVids={next_specific_videos}") # DEBUG
        print(f"Session state: last_winner={session.get('last_winner')}") # DEBUG


        new_competition_videos_raw = choose_videos_function(
            data_for_next_round, # Pass the potentially reloaded data with latest ratings/stats
            next_mode,
            final_next_value_for_choose_videos, # Use the final determined value
            next_num_videos,
            next_use_dynamic_weighting,
            next_competition_type,
            next_specific_videos,
            session=session # Pass session for ring mode logic
        )

        print(f"Next Comp: Result from choose_videos: {new_competition_videos_raw}") # DEBUG
        num_videos_selected = len(new_competition_videos_raw) if new_competition_videos_raw else 0
        print(f"Next Comp: Number of videos selected for next round: {num_videos_selected}") # DEBUG

        # Check if enough videos were found for the next competition
        if new_competition_videos_raw and num_videos_selected >= 2:
             print(f"Next Comp: Sufficient videos found ({num_videos_selected}). Rendering select_winner.html for next round.") # DEBUG
             # Format the selected videos for the template (needs name, rating, times_shown, tags)
             # This part was already preparing a list of tuples.
             # We need to convert this to a list of dictionaries *after* choosing videos
             # and before rendering, and add the processed data info.

             # --- ابدأ كود دمج بيانات الفيديوهات المعالجة هنا (داخل حالة Next Comp الناجحة) ---
             processed_data_dict = load_processed_videos_data()
             video_folder = session.get('selected_folder') # نحتاج مسار المجلد للحصول على حجم الملف

             if not video_folder:
                  print("WARNING Next Comp: selected_folder not found in session. Cannot get file sizes.") # DEBUG

             # Create a new list with enriched video data
             # new_competition_videos_raw is (name, rating, times_shown, tags from choose_videos_function)
             # We should get the latest data from data_for_next_round anyway.
             enriched_competition_videos = []
             for vid_name, _, _, _, *_ in new_competition_videos_raw: # Iterate through names from selected videos
                 # Use the data_for_next_round dictionary as the source of truth for latest values and tags
                 video_data_entry = data_for_next_round.get(vid_name, {})

                 # احصل على اسم العرض المخصص من البيانات الرئيسية (data_for_next_round)
                 display_name_from_db = video_data_entry.get('name', '')

                 enriched_video_info = {
                     'name': vid_name, # احتفظ باسم الملف الأصلي هنا
                     'display_name': display_name_from_db, # أضف الاسم المخصص هنا
                     'rating': video_data_entry.get('rating', 1000.0), # Get latest rating
                     'times_shown': video_data_entry.get('times_shown', 0), # Get latest times_shown
                     'tags': video_data_entry.get('tags', ''),           # Get latest tags
                     'is_processed': False, # Default
                     'weight': None         # Default
                 }

                 if video_folder:
                     full_video_path = os.path.join(video_folder, vid_name)
                     try:
                         file_size = os.path.getsize(full_video_path)
                         if file_size in processed_data_dict:
                             processed_info = processed_data_dict[file_size]
                             enriched_video_info['is_processed'] = True
                             enriched_video_info['weight'] = processed_info.get('total_weight')
                             print(f"Next Comp: Matched video '{vid_name}' with processed data (Size: {file_size}, Weight: {enriched_video_info['weight']})") # DEBUG
                         else:
                             print(f"Next Comp: No processed data found for video '{vid_name}' (Size: {file_size})") # DEBUG

                     except FileNotFoundError:
                         print(f"WARNING Next Comp: Video file not found to get size: {full_video_path}") # DEBUG
                     except Exception as e:
                         print(f"ERROR Next Comp getting size for {full_video_path}: {e}") # DEBUG

                 enriched_competition_videos.append(enriched_video_info)

             competition_videos_to_render = enriched_competition_videos
             print(f"Next Comp: Prepared {len(competition_videos_to_render)} enriched videos for rendering.") # DEBUG
             # --- انتهى كود دمج البيانات هنا ---

             # START: تعديل تمرير المعاملات إلى القالب select_winner.html للمنافسة التالية
             template_params_next = {
                'competition_videos': competition_videos_to_render,
                'num_videos': next_num_videos, # Use next params
                'mode': next_mode,
                'ranking_type': next_ranking_type,
                'competition_type': next_competition_type,
                'data': data_for_next_round
             }
             # Pass value components correctly based on final_next_value_for_choose_videos
             if isinstance(final_next_value_for_choose_videos, dict):
                 template_params_next.update(final_next_value_for_choose_videos)
             elif final_next_value_for_choose_videos is not None:
                 template_params_next['value'] = final_next_value_for_choose_videos

             return render_template('select_winner.html', **template_params_next)
             # END: تعديل تمرير المعاملات

        else:
            # Not enough videos found for the *next* competition
            num_found = len(new_competition_videos_raw) if new_competition_videos_raw else 0
            flash(f"Could not find enough videos ({num_found} found, need at least 2) for the next competition based on the current criteria.", "warning")
            print(f"WARNING Next Comp: Insufficient videos ({num_found}) returned by choose_videos for the next round.") # DEBUG
            # What to do now? Go back to the start competition page.
            # Clear potentially problematic state that led to no videos being found.
            session.pop('competitions_queue', None) # Clear any remaining queue
            session.pop('competition_params', None) # Clear params as auto-start failed
            session.pop('last_winner', None) # Clear last winner
            print("Cleared session state (queue, params, last_winner) due to insufficient videos for next round.") # DEBUG
            return redirect(url_for('competition'))

    except Exception as e:
        # Catch any unexpected errors during processing results
        flash(f"An error occurred while processing the results: {e}", "danger")
        print(f"CRITICAL ERROR in select_winner POST route: {e}") # DEBUG
        import traceback
        traceback.print_exc() # Log the full traceback
        # Redirect to start page in case of error
        session.pop('competitions_queue', None)
        session.pop('competition_params', None)
        session.pop('last_winner', None)
        print("Cleared session state due to critical error in select_winner POST route.") # DEBUG
        return redirect(url_for('competition'))


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
@app.route('/tour', methods=['GET', 'POST'])
def tour_page():
    available_files = tour.list_files(exclude_topcut=True)
    tournament_files = tour.list_tournament_files()
    tournament_archive = tour.load_tournament_archive()
    
    # معالجة خيارات الترتيب
    sort_type = request.form.get('sort_type', 'recent') if request.method == 'POST' else 'recent'
    view_type = request.form.get('view_type', 'tournaments') if request.method == 'POST' else 'tournaments'
    
    # ترتيب البطولات
    sorted_tournaments = tour.sort_tournaments_by_weight(tournament_archive, sort_type)
    
    # الحصول على الفيديوهات الفردية
    video_weights, video_counts = tour.get_individual_videos(tournament_archive)
    
    # ترتيب الفيديوهات حسب النوع المطلوب
    if view_type == 'videos':
        if sort_type == "most_frequent":
            sorted_videos = sorted(video_weights.items(), key=lambda x: video_counts[x[0]], reverse=True)
        elif sort_type == "asc_weight":
            sorted_videos = sorted(video_weights.items(), key=lambda x: x[1])
        elif sort_type == "desc_weight":
            sorted_videos = sorted(video_weights.items(), key=lambda x: x[1], reverse=True)
        else:
            sorted_videos = sorted(video_weights.items(), key=lambda x: x[0])
    else:
        sorted_videos = []
    
    return render_template('tour.html', 
                         available_files=available_files,
                         tournament_files=tournament_files, 
                         tournament_archive=sorted_tournaments,
                         video_weights=sorted_videos,
                         video_counts=video_counts,
                         current_sort=sort_type,
                         current_view=view_type)

@app.route('/get_tournament_content/<filename>')
def get_tournament_content(filename):
    try:
        # Sanitize filename - prevent directory traversal
        if '..' in filename or filename.startswith('/'):
             raise ValueError("Invalid filename.")
        safe_path = os.path.join(JSON_FOLDER, filename)
        # Double check it's still within the intended folder
        if not os.path.abspath(safe_path).startswith(os.path.abspath(JSON_FOLDER)):
             raise ValueError("Invalid filename path.")
        with open(safe_path, 'r') as f:
            data = json.load(f)
        return json.dumps(data)
    except FileNotFoundError:
         print(f"Tournament file not found: {filename}") # DEBUG
         return json.dumps({'error': 'File not found'}), 404
    except ValueError as e:
        print(f"Invalid filename requested: {filename}, Error: {e}") # DEBUG
        return json.dumps({'error': str(e)}), 400
    except Exception as e:
        print(f"Error getting tournament content for {filename}: {e}") # DEBUG
        return json.dumps({'error': str(e)}), 500


@app.route('/tour/create', methods=['POST'])
def tour_create():
    selected_file = request.form.get('json_file')
    num_participants = request.form.get('num_participants')
    num_videos = request.form.get('num_videos')
    ranking_type = request.form.get('ranking_type')
    try:
        num_participants = int(num_participants)
        num_videos = int(num_videos)
    except (ValueError, TypeError):
        flash("Number of participants or videos is invalid.", "error")
        return redirect(url_for('tour_page'))
    result = tour.create_tournament_web(
        selected_file,
        num_participants,
        num_videos,
        ranking_type)
    if result.get('success'):
        flash(result.get('message'), "success")
    else:
        flash(result.get('message'), "error")
    return redirect(url_for('tour_page'))


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


def main():
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
    app.run(host='0.0.0.0', port=5000, debug=True)
