import os
from flask import render_template, request, redirect, url_for, flash, session
from urllib.parse import unquote
from werkzeug.utils import safe_join
import mimetypes
from utilities.config import ALLOWED_EXTENSIONS
from utilities.file_manager import url_quote_filter
from flask import send_from_directory


def init_routes(app):
    app.template_filter('quote')(url_quote_filter)

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

    @app.route('/reset_session')
    def reset_session():
        session.pop('selected_folder', None)
        session.pop('competition_mode', None)
        session.pop('competition_num_videos', None)
        session.pop('competition_value', None)
        flash("تم إعادة تعيين الجلسة. اختر مجلدًا جديدًا.", "success")
        return redirect(url_for('select_folder'))

    @app.route('/browse', defaults={'folder_path': ''})
    @app.route('/browse/<path:folder_path>')
    def browse(folder_path):
        if not session.get('selected_folder'):
            flash("يرجى اختيار مجلد أولاً.", "warning")
            return redirect(url_for('select_folder'))

        current_folder = session['selected_folder']
        if folder_path:
            current_folder = os.path.join(current_folder, folder_path)

        if not os.path.isdir(current_folder):
            flash("المجلد غير صالح.", "danger")
            return redirect(url_for('browse'))

        folders = []
        files = []
        try:
            for entry in os.listdir(current_folder):
                path = os.path.join(current_folder, entry)
                if os.path.isdir(path):
                    folders.append(entry)
                elif os.path.isfile(path) and entry.lower().endswith(tuple(ALLOWED_EXTENSIONS)):
                    files.append(entry)
        except PermissionError:
            flash("ليس لديك صلاحيات للوصول إلى هذا المجلد.", "danger")
            return redirect(url_for('browse'))

        relative_path = os.path.relpath(
            current_folder, session['selected_folder'])
        if relative_path == '.':
            relative_path = ''

        return render_template(
            'browse.html', folders=folders, files=files, current_path=relative_path)

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


    @app.route('/videos/<path:filename>')
    def serve_video(filename):
        selected_folder = session.get('selected_folder')
        if not selected_folder:
            flash("يرجى اختيار مجلد أولاً.", "warning")
            return redirect(url_for('select_folder'))

        try:
            decoded_filename = unquote(filename)

            file_path = safe_join(selected_folder, decoded_filename)

            if not file_path or not os.path.exists(file_path):
                try:
                    target_size = int(decoded_filename)
                except ValueError:
                    flash("اسم الملف غير صالح أو الملف غير موجود.", "danger")
                    return redirect(url_for('index'))

                found_file = None
                for entry in os.listdir(selected_folder):
                    current_path = os.path.join(selected_folder, entry)
                    if os.path.isfile(current_path):
                        try:
                            if os.path.getsize(current_path) == target_size:
                                found_file = entry
                                break
                        except Exception as e:
                            print(f"Error getting file size for {entry}: {e}")
                if found_file:
                    file_path = os.path.join(selected_folder, found_file)
                    decoded_filename = found_file  # تحديث اسم الملف
                else:
                    print(f"File not found by size: {target_size}")
                    flash(f"الملف بالحجم {target_size} غير موجود.", "danger")
                    return redirect(url_for('index'))

            directory = os.path.dirname(file_path)
            basename = os.path.basename(file_path)

            mimetype, _ = mimetypes.guess_type(file_path)
            if not mimetype:
                mimetype = 'application/octet-stream'

            response = send_from_directory(
                directory,
                basename,
                mimetype=mimetype,
                as_attachment=False
            )

            safe_filename = basename.encode('ascii', 'ignore').decode('ascii')
            response.headers['Content-Disposition'] = f'inline; filename="{safe_filename}"'

            return response

        except Exception as e:
            print(f"Error serving video: {e}")
            flash("حدث خطأ أثناء تشغيل الفيديو.", "danger")
            return redirect(url_for('index'))

