import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from utilities.config import SECRET_KEY, BACKUP_FOLDER
from utilities.data_manager import load_data, save_data, create_backup
from utilities.file_manager import update_video_list, update_file_names, allowed_file
from utilities.elo_calculator import update_ratings_multiple
from utilities.helpers import  url_quote_filter, start_new_competition, video_handler
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = SECRET_KEY
app.template_filter('quote')(url_quote_filter)

# مسار اختيار المجلد
@app.route('/select_folder', methods=['GET', 'POST'])
def select_folder():
    if request.method == 'POST':
        folder_path = request.form.get('folder_path')
        if folder_path and os.path.isdir(folder_path):
            session['selected_folder'] = os.path.abspath(folder_path)
            flash(f"تم اختيار المجلد: {folder_path}", "success")
            return redirect(url_for('index'))
        else:
            flash("المجلد غير صالح. يرجى إدخال مسار مجلد صحيح.", "danger")
            return redirect(url_for('select_folder'))
    return render_template('select_folder.html')

# الصفحة الرئيسية
@app.route('/')
def index():
    selected_folder = session.get('selected_folder')
    return render_template('index.html', selected_folder=selected_folder)

# مسابقة
@app.route('/competition', methods=['GET', 'POST'])
def competition():
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    if request.method == 'POST':
        mode = request.form.get('mode', type=int)
        num_videos = request.form.get('num_videos', type=int)

        # التحقق من الوضع وتمرير القيم المناسبة
        if mode == 5:  # الوضع الخاص بالفيديوهات بين رقمين
            min_value = request.form.get('min_value', type=int, default=0)
            max_value = request.form.get('max_value', type=int, default=1000)
            value = {'min_value': min_value, 'max_value': max_value}
        else:
            value = request.form.get('value', type=int)

        print(f"Starting competition with mode: {mode}, num_videos: {num_videos}, value: {value}")
        competition_videos = start_new_competition(mode, num_videos, value)

        if competition_videos:
            return render_template('select_winner.html', competition_videos=competition_videos, num_videos=num_videos, mode=mode)
        else:
            return redirect(url_for('competition'))
    else:
        return render_template('start_competition.html')


# دالة اختيار الفائزين
@app.route('/select_winner', methods=['POST'])
def select_winner():
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    # استلام البيانات من النموذج
    mode = request.form.get('mode', type=int)
    num_videos = request.form.get('num_videos', type=int)
    
    if mode == 5:
        min_value = request.form.get('min_value', type=int, default=0)
        max_value = request.form.get('max_value', type=int, default=1000)
        value = {'min_value': min_value, 'max_value': max_value}
    elif mode in [3, 4]:
        value = request.form.get('value', type=int)
    else:
        value = None

    competition_videos = request.form.getlist('videos')
    ranks = []
    for i in range(1, num_videos + 1):
        rank = request.form.get(f'rank_{i}', type=int)
        if rank:
            ranks.append(rank)
        else:
            ranks.append(None)

    print(f"Competition videos: {competition_videos}")
    print(f"Ranks: {ranks}")

    if not competition_videos or any(r is None for r in ranks):
        flash("يرجى تحديد جميع المراكز.", "danger")
        return redirect(url_for('competition'))

    # تحميل البيانات قبل استخدام 'data'
    data = load_data()
    if not data:
        flash("لا توجد بيانات للمنافسة.", "danger")
        return redirect(url_for('competition'))

    # تحليل الفيديوهات إلى قائمة من tuples مع المراكز
    ranked_videos = []
    for vid, rank in zip(competition_videos, ranks):
        # تأكد من أن vid يحتوي فقط على اسم الملف بدون معلومات إضافية
        video_id = vid.strip().split('|')[0]  # إذا كان 'vid' يحتوي على '|', نفصل ونأخذ الاسم
        if video_id in data:
            rating = float(data[video_id].get('rating', 1000))
            ranked_videos.append((video_id, rating, rank))
        else:
            flash(f"الفيديو {video_id} غير موجود في البيانات.", "danger")
            return redirect(url_for('competition'))

    if not ranked_videos:
        flash("تعذر تحليل الفيديوهات.", "danger")
        return redirect(url_for('competition'))

    print(f"Ranked competition videos: {ranked_videos}")

    # التحقق من صحة المراكز
    unique_ranks = set()
    for vid, rating, rank in ranked_videos:
        if rank in unique_ranks:
            flash(f"المركز {rank} تم اختياره بالفعل.", "danger")
            return redirect(url_for('competition'))
        unique_ranks.add(rank)

    # ترتيب الفيديوهات بناءً على المراكز
    ranked_videos_sorted = sorted(ranked_videos, key=lambda x: x[2])  # ترتيب حسب المركز

    # تحديث التصنيفات باستخدام نظام Elo متعدد المراكز
    try:
        update_ratings_multiple(ranked_videos_sorted, data)
        save_data(data)
        flash("تم تحديث التصنيفات بنجاح!", "success")
    except Exception as e:
        flash(f"حدث خطأ أثناء تحديث التصنيفات: {e}", "danger")
        print(f"Error updating ratings: {e}")
        return redirect(url_for('competition'))

    # بدء منافسة جديدة تلقائيًا بعد اختيار الفائزين
    competition_videos = start_new_competition(mode, num_videos, value)
    if competition_videos:
        return render_template('select_winner.html', competition_videos=competition_videos, num_videos=num_videos, mode=mode)
    else:
        return redirect(url_for('competition'))

# إعادة تسمية جميع الفيديوهات بناءً على تقييماتها
@app.route('/rename_all_videos', methods=['POST'])
def rename_all_videos():
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))
    
    # منطق إعادة تسمية الفيديوهات
    data = load_data()
    if not data:
        flash("لا توجد بيانات لإعادة التسمية.", "danger")
        return redirect(url_for('top_videos'))
    
    updated_data = update_file_names(data)
    
    save_data(updated_data)
    flash("تمت إعادة تسمية جميع الفيديوهات بنجاح.", "success")
    return redirect(url_for('top_videos'))

# عرض أفضل الفيديوهات
@app.route('/top_videos', methods=['GET', 'POST'])
def top_videos():
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    data = load_data()
    # ترتيب الفيديوهات بناءً على 'rating' بالترتيب التنازلي
    top_videos = sorted(data.items(), key=lambda x: x[1]['rating'], reverse=True)[:50]
    # ترميز أسماء الفيديوهات للتعامل مع الأحرف الخاصة
    top_videos_encoded = [(video[0], video[1]['rating'], url_quote_filter(video[0])) for video in top_videos]
    print(f"Top videos: {top_videos_encoded}")
    return render_template('top_videos.html', top_videos=top_videos_encoded)

# خدمة الفيديوهات
from flask import send_from_directory

@app.route('/videos/<path:filename>')
def serve_video(filename):
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    file_path = os.path.join(selected_folder, filename)
    if not os.path.exists(file_path):
        flash(f"الملف {filename} غير موجود.", "danger")
        return redirect(url_for('index'))
    
    return send_from_directory(selected_folder, filename)

# مسار تصفح المجلدات
@app.route('/browse', defaults={'folder_path': ''})
@app.route('/browse/<path:folder_path>')
def browse(folder_path):
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    current_folder = session['selected_folder']
    if folder_path:
        current_folder = os.path.join(current_folder, folder_path)

    # التأكد من أن المسار موجود ومجلد
    if not os.path.isdir(current_folder):
        flash("المجلد غير صالح.", "danger")
        return redirect(url_for('browse'))

    # الحصول على قائمة المجلدات والملفات
    folders = []
    files = []
    try:
        for entry in os.listdir(current_folder):
            path = os.path.join(current_folder, entry)
            if os.path.isdir(path):
                folders.append(entry)
            elif os.path.isfile(path) and entry.lower().endswith(tuple(allowed_file(entry))):
                files.append(entry)
    except PermissionError:
        flash("ليس لديك صلاحيات للوصول إلى هذا المجلد.", "danger")
        return redirect(url_for('browse'))

    # تحديد المسار النسبي للمجلد الحالي بالنسبة للمجلد المختار
    relative_path = os.path.relpath(current_folder, session['selected_folder'])
    if relative_path == '.':
        relative_path = ''

    return render_template('browse.html', folders=folders, files=files, current_path=relative_path)

# اختيار المجلد من التصفح
@app.route('/select_folder_post/<path:folder_path>', methods=['POST'])
def select_folder_post(folder_path):
    selected_folder = os.path.join(session['selected_folder'], folder_path)
    if os.path.isdir(selected_folder):
        session['selected_folder'] = os.path.abspath(selected_folder)
        flash(f"تم اختيار المجلد: {selected_folder}", "success")
        return redirect(url_for('index'))
    else:
        flash("المجلد غير صالح.", "danger")
        return redirect(url_for('browse'))

# مسار تحميل الفيديوهات
@app.route('/upload_video', methods=['GET', 'POST'])
def upload_video():
    if not session.get('selected_folder'):
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    if request.method == 'POST':
        if 'video' not in request.files:
            flash('لا يوجد ملف مرفق.', 'danger')
            return redirect(request.url)
        file = request.files['video']
        if file.filename == '':
            flash('لم يتم اختيار ملف.', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            selected_folder = session['selected_folder']
            file_path = os.path.join(selected_folder, filename)
            try:
                file.save(file_path)
                flash('تم تحميل الفيديو بنجاح!', "success")
                # تحديث بيانات الفيديو بعد التحميل
                data = load_data()
                data[filename] = {
                    'rating': 1000,
                    'win_streak': 0,
                    'loss_streak': 0
                }  # التصنيف الافتراضي مع الستيك
                data = update_file_names(data)
                save_data(data)
                print(f"Uploaded video: {filename}")
            except Exception as e:
                flash(f"حدث خطأ أثناء تحميل الفيديو: {e}", "danger")
                print(f"Error uploading video: {e}")
                return redirect(request.url)
            return redirect(url_for('upload_video'))
        else:
            flash('نوع الملف غير صالح.', 'danger')
            return redirect(request.url)
    return render_template('upload.html')


# مسار إعادة تعيين الجلسة
@app.route('/reset_session')
def reset_session():
    session.pop('selected_folder', None)
    session.pop('competition_mode', None)
    session.pop('competition_num_videos', None)
    session.pop('competition_value', None)
    flash("تم إعادة تعيين الجلسة. اختر مجلدًا جديدًا.", "success")
    return redirect(url_for('select_folder'))

# دمج الوظيفة مع البرنامج الرئيسي
def main():
    # التأكد من وجود مجلد النسخ الاحتياطية
    if not os.path.exists(BACKUP_FOLDER):
        try:
            os.makedirs(BACKUP_FOLDER)
            print(f"Backup folder created at {BACKUP_FOLDER}")
        except Exception as e:
            print(f"Error creating backup folder: {e}")
    # لا حاجة لتحديث البيانات هنا لأننا سنقوم بذلك عند بدء المنافسة

if __name__ == "__main__":
    main()
    # طباعة جميع النقاط النهائية للتأكد من تسجيلها
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule}")
    app.run(host='0.0.0.0', port=5000, debug=True)  # تفعيل وضع التصحيح
