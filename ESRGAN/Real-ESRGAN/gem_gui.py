# START: FULL SCRIPT (IMPROVED GUI VERSION)
import os
import sys
import subprocess
import json
import shutil
import threading
import PySimpleGUI as sg

# --- الإعدادات والمسارات الأساسية ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INFERENCE_SCRIPT = os.path.join(BASE_DIR, "inference_realesrgan.py")

DB_FILES = [
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\utilities\\elo_videos_A1000 elo tik.json",
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\utilities\\elo_videos_A1000 elo pic.json",
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\utilities\\elo_videos_Dib.json"
]

SOURCE_MEDIA_FOLDERS = [
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\NS\\TikTok\\ELO TIK\\A1000 elo pic",
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\NS\\TikTok\\ELO TIK\\A1000 elo tik",
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app\\NS\\TikTok\\ELO TIK\\Dib"
]

# قائمة بجميع الأزرار لتعطيلها أثناء العمليات
ACTION_BUTTON_KEYS = ['-UPSCALE_IMG-', '-UPSCALE_VID-', '-RENAME-', '-UPDATE_DB-', '-MOVE-']

# --- دوال الواجهة الرسومية والوظائف المنطقية ---

def run_command_in_thread(command, window):
    """لتشغيل الأوامر في الطرفية وعرض المخرجات مباشرة في نافذة الواجهة."""
    try:
        window['-OUTPUT-'].print(f"🚀 Executing Command:\n{' '.join(command)}\n" + "="*50)
        window.refresh()
        
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', cwd=BASE_DIR
        )

        for line in iter(process.stdout.readline, ''):
            window['-OUTPUT-'].print(line.strip())
            window.refresh()
        
        process.wait()
        if process.returncode != 0:
            window['-OUTPUT-'].print(f"\n❌ Command finished with an error (exit code: {process.returncode}).")
        else:
            window['-OUTPUT-'].print(f"\n✅ Command finished successfully.")
            
    except FileNotFoundError:
        window['-OUTPUT-'].print(f"❌ Error: Command '{command[0]}' not found.")
    except Exception as e:
        window['-OUTPUT-'].print(f"❌ An unexpected error occurred: {e}")
    finally:
        # إرسال حدث مخصص للنافذة الرئيسية لإعادة تفعيل الأزرار
        window.write_event_value('-THREAD_DONE-', '')

def upscale_images_logic(values, window):
    """الوظيفة المنطقية لرفع جودة الصور."""
    command = [
        sys.executable, INFERENCE_SCRIPT,
        '-n', values['-MODEL-'],
        '-i', INPUT_DIR, '-o', OUTPUT_DIR,
        '--outscale', values['-OUTSCALE-'], '--fp32'
    ]
    # -- تعديل منطق البلاط --
    tile_value = values['-TILE-'].strip()
    if tile_value and tile_value != '0':
        command.extend(['--tile', tile_value])
        
    if values['-SUFFIX-'].strip():
        command.extend(['--suffix', values['-SUFFIX-'].strip()])
        
    run_command_in_thread(command, window)

def upscale_videos_logic(values, window):
    """الوظيفة المنطقية لرفع جودة الفيديوهات."""
    video_extensions = ('.mp4', '.mkv', '.mov', '.avi', '.webm')
    videos = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(video_extensions)]

    if not videos:
        sg.popup("No videos found in the input directory.")
        window.write_event_value('-THREAD_DONE-', '') # لإعادة تفعيل الأزرار
        return

    window['-OUTPUT-'].print(f"Found {len(videos)} video(s) to process.")
    tile_value = values['-TILE-'].strip()

    for video_name in videos:
        window['-OUTPUT-'].print(f"\n--- Processing Video: {video_name} ---")
        video_path = os.path.join(INPUT_DIR, video_name)
        video_size_str = str(os.path.getsize(video_path))
        
        frames_input_dir = os.path.join(INPUT_DIR, video_size_str)
        frames_output_dir = os.path.join(OUTPUT_DIR, video_size_str)
        os.makedirs(frames_input_dir, exist_ok=True)
        os.makedirs(frames_output_dir, exist_ok=True)

        steps = [
            ('Extracting frames', ['ffmpeg', '-i', video_path, os.path.join(frames_input_dir, 'frame_%05d.png')]),
        ]
        
        # بناء أمر رفع الجودة
        suffix = values['-SUFFIX-'].strip() if values['-SUFFIX-'].strip() else 'out'
        upscale_cmd = [
            sys.executable, INFERENCE_SCRIPT, '-n', values['-MODEL-'],
            '-i', frames_input_dir, '-o', frames_output_dir,
            '--outscale', values['-OUTSCALE-'], '--fp32', '--suffix', suffix
        ]
        if tile_value and tile_value != '0':
            upscale_cmd.extend(['--tile', tile_value])
        steps.append(('Upscaling frames', upscale_cmd))

        # بناء باقي الأوامر
        video_base_name = os.path.splitext(video_name)[0]
        temp_video_name = f"{video_base_name}_without_voice.mp4"
        temp_video_path = os.path.join(OUTPUT_DIR, temp_video_name)
        final_video_name = f"{video_base_name}_upscaled.mp4"
        final_video_path = os.path.join(OUTPUT_DIR, final_video_name)

        steps.extend([
            ('Assembling video (no audio)', ['ffmpeg', '-y', '-framerate', '24', '-i', os.path.join(frames_output_dir, f'frame_%05d_{suffix}.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', temp_video_path]),
            ('Adding audio', ['ffmpeg', '-y', '-i', temp_video_path, '-i', video_path, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', final_video_path])
        ])
        
        all_successful = True
        for i, (desc, cmd) in enumerate(steps):
            window['-OUTPUT-'].print(f"\nStep {i+1}/{len(steps)}: {desc}")
            if run_command_in_thread(cmd, window) != 0:
                window['-OUTPUT-'].print(f"❌ Step failed. Skipping rest of the process for {video_name}.")
                all_successful = False
                break
        
        if all_successful:
             window['-OUTPUT-'].print("\nStep 5/5: Cleaning up temporary files...")
             try:
                shutil.rmtree(frames_input_dir)
                shutil.rmtree(frames_output_dir)
                os.remove(temp_video_path)
                window['-OUTPUT-'].print("✅ Cleanup successful.")
             except Exception as e:
                window['-OUTPUT-'].print(f"⚠️ Warning: Could not clean up all temporary files. {e}")
    
    window.write_event_value('-THREAD_DONE-', '') # تم الانتهاء من جميع الفيديوهات

# --- دوال المعالجة اللاحقة (تعمل الآن داخل الواجهة) ---

def rename_files_logic(window):
    files_to_rename = [f for f in os.listdir(OUTPUT_DIR) if os.path.splitext(f)[0].endswith('_out')]
    if not files_to_rename:
        sg.popup("No files with '_out' suffix found.")
        window.write_event_value('-THREAD_DONE-', '')
        return

    # عرض الملفات للمستخدم للتأكيد
    file_list_str = "\n".join(files_to_rename)
    if sg.popup_ok_cancel(f"Found {len(files_to_rename)} files to rename:\n\n{file_list_str}\n\nProceed?", title="Confirm Rename") == 'OK':
        renamed_count = 0
        for filename in files_to_rename:
            name, ext = os.path.splitext(filename)
            new_name = name[:-4] + ext
            try:
                os.rename(os.path.join(OUTPUT_DIR, filename), os.path.join(OUTPUT_DIR, new_name))
                window['-OUTPUT-'].print(f"Renamed: {filename} -> {new_name}")
                renamed_count += 1
            except Exception as e:
                window['-OUTPUT-'].print(f"ERROR renaming {filename}: {e}")
        sg.popup(f"Successfully renamed {renamed_count} files.")
    else:
        window['-OUTPUT-'].print("Rename operation cancelled by user.")
    window.write_event_value('-THREAD_DONE-', '')

def update_db_logic(window):
    output_files = {f: os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in os.listdir(OUTPUT_DIR)}
    found_matches = {}
    for db_path in DB_FILES:
        try:
            with open(db_path, 'r', encoding='utf-8') as f: data = json.load(f)
            for key, value in data.items():
                if key in output_files and value.get('file_size') != output_files[key]:
                    found_matches[key] = {'old': value.get('file_size', 'N/A'), 'new': output_files[key]}
        except Exception as e: window['-OUTPUT-'].print(f"⚠️ Warning: Could not process DB {db_path}. {e}")

    if not found_matches:
        sg.popup("No matching files found in databases that need updating.")
        window.write_event_value('-THREAD_DONE-', '')
        return

    match_list_str = "\n".join([f"- {name}: {sizes['old']} -> {sizes['new']}" for name, sizes in found_matches.items()])
    if sg.popup_ok_cancel(f"Found {len(found_matches)} records to update:\n\n{match_list_str}\n\nUpdate databases?", title="Confirm DB Update") == 'OK':
        for db_path in DB_FILES:
            try:
                with open(db_path, 'r', encoding='utf-8') as f: data = json.load(f)
                changes_made = any(key in found_matches for key in data)
                if changes_made:
                    for key, value in data.items():
                        if key in found_matches: value['file_size'] = found_matches[key]['new']
                    with open(db_path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
                    window['-OUTPUT-'].print(f"✅ Database updated: {os.path.basename(db_path)}")
            except Exception as e: window['-OUTPUT-'].print(f"❌ Error updating DB {db_path}: {e}")
        sg.popup("Database update process finished.")
    else:
        window['-OUTPUT-'].print("Database update cancelled by user.")
    window.write_event_value('-THREAD_DONE-', '')
    
def move_files_logic(window):
    files_to_move = []
    for output_file in os.listdir(OUTPUT_DIR):
        for source_folder in SOURCE_MEDIA_FOLDERS:
            dest_path = os.path.join(source_folder, output_file)
            if os.path.exists(dest_path):
                files_to_move.append((os.path.join(OUTPUT_DIR, output_file), dest_path))
                break
    
    if not files_to_move:
        sg.popup("No original files found to replace.")
        window.write_event_value('-THREAD_DONE-', '')
        return

    move_list_str = "\n".join([f"- {os.path.basename(src)}" for src, dest in files_to_move])
    if sg.popup_ok_cancel(f"Found {len(files_to_move)} files to move and replace:\n\n{move_list_str}\n\nThis cannot be undone. Proceed?", title="Confirm Move & Replace") == 'OK':
        moved_count = 0
        for src, dest in files_to_move:
            try:
                shutil.move(src, dest)
                window['-OUTPUT-'].print(f"Moved and replaced: {os.path.basename(dest)}")
                moved_count += 1
            except Exception as e:
                window['-OUTPUT-'].print(f"❌ Error moving {os.path.basename(src)}: {e}")
        sg.popup(f"Successfully moved and replaced {moved_count} files.")
    else:
        window['-OUTPUT-'].print("Move operation cancelled by user.")
    window.write_event_value('-THREAD_DONE-', '')

def main_gui():
    """الدالة الرئيسية للواجهة الرسومية."""
    sg.theme('DarkGrey2')
    
    model_choices = ['RealESRGAN_x2plus', 'RealESRGAN_x4plus', 'realesr-general-x4v3', 'RealESRGAN_x4plus_anime_6B', 'realesr-animevideov3']

    upscale_layout = [
        [sg.Text('Model:', size=(10, 1)), sg.Combo(model_choices, default_value='RealESRGAN_x2plus', key='-MODEL-', readonly=True)],
        [sg.Text('Tile Size:', size=(10, 1)), sg.Input('128', key='-TILE-', size=(10, 1)), sg.Text('(0 to disable)')],
        [sg.Text('Outscale:', size=(10, 1)), sg.Input('1.2', key='-OUTSCALE-', size=(10, 1))],
        [sg.Text('Suffix:', size=(10, 1)), sg.Input('', key='-SUFFIX-', size=(20, 1))],
        [sg.Button('Upscale Images', key='-UPSCALE_IMG-'), sg.Button('Upscale Videos', key='-UPSCALE_VID-')]
    ]

    post_process_layout = [
        [sg.Text('Actions for files in the output folder:')],
        [sg.Button('Rename Files (_out)', key='-RENAME-'), sg.Button('Update DB Sizes', key='-UPDATE_DB-'), sg.Button('Move & Replace', key='-MOVE-')]
    ]

    layout = [
        [sg.Frame('1. Upscaling Actions', upscale_layout)],
        [sg.Frame('2. Post-Processing Actions', post_process_layout)],
        [sg.Text('_' * 80)],
        [sg.Text('Output Log:')],
        [sg.Multiline(size=(90, 20), key='-OUTPUT-', autoscroll=True, reroute_stdout=False, reroute_stderr=False, disabled=True)],
        [sg.StatusBar('Ready', size=(80,1), key='-STATUS-')],
        [sg.Button('Exit')]
    ]

    window = sg.Window('Real-ESRGAN Manager v2.0', layout, finalize=True)
    
    active_thread = None

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == 'Exit':
            if active_thread and active_thread.is_alive():
                if sg.popup_ok_cancel("A process is still running. Are you sure you want to exit?", title="Warning") == 'OK':
                    break
            else:
                break
        
        # إذا انتهى الخيط، أعد تفعيل الأزرار
        if event == '-THREAD_DONE-':
            active_thread = None
            for key in ACTION_BUTTON_KEYS: window[key].update(disabled=False)
            window['-STATUS-'].update('Done. Ready for next task.')
            continue

        # بدء عملية جديدة فقط إذا لم تكن هناك عملية أخرى قيد التشغيل
        if active_thread and active_thread.is_alive():
            sg.popup_animated(None) # إخفاء أي نافذة منبثقة للانتظار
            sg.popup("A process is already running. Please wait for it to complete.", title="Busy")
            continue
        
        # تعطيل الأزرار وبدء الخيط
        target_function = None
        if event == '-UPSCALE_IMG-':
            target_function = upscale_images_logic
            args = (values, window)
        elif event == '-UPSCALE_VID-':
            target_function = upscale_videos_logic
            args = (values, window)
        elif event == '-RENAME-':
            target_function = rename_files_logic
            args = (window,)
        elif event == '-UPDATE_DB-':
            target_function = update_db_logic
            args = (window,)
        elif event == '-MOVE-':
            target_function = move_files_logic
            args = (window,)

        if target_function:
            window['-OUTPUT-'].update('') # مسح السجل
            for key in ACTION_BUTTON_KEYS: window[key].update(disabled=True)
            window['-STATUS-'].update(f'Working on: {event}...')
            active_thread = threading.Thread(target=target_function, args=args, daemon=True)
            active_thread.start()

    window.close()

if __name__ == "__main__":
    if shutil.which("ffmpeg") is None:
        sg.popup_error("CRITICAL ERROR: 'ffmpeg' not found.", "Please install ffmpeg and ensure it's in your system's PATH to process videos.")
    
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    main_gui()

# END: FULL SCRIPT (IMPROVED GUI VERSION)