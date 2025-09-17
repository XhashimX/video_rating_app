from urllib.parse import quote, unquote
from flask import render_template, session, flash, redirect, url_for
from .data_manager import load_data, save_data
from .file_manager import update_video_list, update_file_names
from .video_selector import choose_videos_function
from .config import BACKUP_FOLDER
import os
from flask import send_from_directory




def video_handler(filename):
    filename_decoded = unquote(filename)
    selected_folder = session.get('selected_folder')
    if not selected_folder:
        flash("يرجى اختيار مجلد أولاً.", "warning")
        return redirect(url_for('select_folder'))

    file_path = os.path.join(selected_folder, filename_decoded)
    if not os.path.exists(file_path):
        flash(f"الملف {filename_decoded} غير موجود.", "danger")
        return redirect(url_for('index'))

    return send_from_directory(selected_folder, filename_decoded)
