# START: FULL SCRIPT

import os
import sys
import subprocess
import json
import shutil
import threading

# يمكنك استخدام أي من المكتبتين:
try:
    import PySimpleGUI as sg
except ImportError:
    import FreeSimpleGUI as sg

# --- الإعدادات والمسارات الأساسية ---
# تأكد من أن هذه المسارات صحيحة
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

# إعداد ثيم الواجهة
sg.theme('DarkBlue3')

# --- دوال مساعدة ---

def run_command_gui(command, window, output_key):
    """
    لتشغيل الأوامر في الطرفية وعرض المخرجات مباشرة في نافذة GUI.
    
    START: MODIFIED SECTION
    تم تحويل هذه الدالة لتعمل مع PySimpleGUI بدلاً من print
    END: MODIFIED SECTION
    """
    separator = "="*50
    window[output_key].print(f"\n{separator}")
    window[output_key].print(f"🚀 تنفيذ الأمر:\n{' '.join(command)}")
    window[output_key].print(f"{separator}\n")
    window.refresh()
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=BASE_DIR
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                window[output_key].print(output.strip())
                window.refresh()
        
        rc = process.poll()
        if rc != 0:
            window[output_key].print(f"\n❌ انتهى الأمر بخطأ (exit code: {rc}).")
        else:
            window[output_key].print(f"\n✅ انتهى الأمر بنجاح.")
        
        window.refresh()
        return rc
        
    except FileNotFoundError:
        window[output_key].print(f"❌ خطأ: الأمر '{command[0]}' غير موجود. تأكد من تثبيته.")
        window.refresh()
        return -1
    except Exception as e:
        window[output_key].print(f"❌ حدث خطأ غير متوقع: {e}")
        window.refresh()
        return -1


def get_upscale_options_gui(media_type):
    """
    START: MODIFIED SECTION
    نافذة GUI للحصول على خيارات رفع الجودة من المستخدم.
    استبدال questionary بنافذة PySimpleGUI.
    END: MODIFIED SECTION
    """
    model_choices = [
        'RealESRGAN_x2plus',
        'RealESRGAN_x4plus',
        'realesr-general-x4v3',
        'RealESRGAN_x4plus_anime_6B',
        'realesr-animevideov3'
    ]
    
    layout = [
        [sg.Text(f'إعدادات رفع جودة {media_type}', font=('Arial', 14, 'bold'))],
        [sg.HorizontalSeparator()],
        [sg.Text('اختر النموذج:', size=(20, 1)), 
         sg.Combo(model_choices, default_value='RealESRGAN_x2plus', key='-MODEL-', size=(30, 1))],
        [sg.Text('حجم البلاط (Tile):', size=(20, 1)), 
         sg.Input('128', key='-TILE-', size=(32, 1))],
        [sg.Text('(أدخل 0 لتعطيل البلاط)', font=('Arial', 8), text_color='gray')],
        [sg.Text('عامل التكبير (Outscale):', size=(20, 1)), 
         sg.Input('1.2', key='-OUTSCALE-', size=(32, 1))],
        [sg.Text('لاحقة الملف (Suffix):', size=(20, 1)), 
         sg.Input('', key='-SUFFIX-', size=(32, 1))],
        [sg.Text('(اتركه فارغاً لعدم الإضافة)', font=('Arial', 8), text_color='gray')],
        [sg.Push(), sg.Button('بدء المعالجة', button_color=('white', 'green')), 
         sg.Button('إلغاء', button_color=('white', 'red'))]
    ]
    
    window = sg.Window('إعدادات رفع الجودة', layout, modal=True)
    
    while True:
        event, values = window.read()
        
        if event in (sg.WIN_CLOSED, 'إلغاء'):
            window.close()
            return None
        
        if event == 'بدء المعالجة':
            options = {
                'model_name': values['-MODEL-'],
                'tile': values['-TILE-'].strip(),
                'outscale': values['-OUTSCALE-'].strip(),
                'suffix': values['-SUFFIX-'].strip()
            }
            window.close()
            return options
    

def upscale_images_gui():
    """
    START: MODIFIED SECTION
    واجهة رفع جودة الصور مع نافذة عرض المخرجات.
    END: MODIFIED SECTION
    """
    options = get_upscale_options_gui('الصور')
    if options is None:
        return
    
    # نافذة عرض التقدم والمخرجات
    layout = [
        [sg.Text('جاري معالجة الصور...', font=('Arial', 12, 'bold'))],
        [sg.Multiline(size=(100, 25), key='-OUTPUT-', autoscroll=True, disabled=True, 
                      background_color='black', text_color='white')],
        [sg.Push(), sg.Button('إغلاق', disabled=True, key='-CLOSE-')]
    ]
    
    window = sg.Window('رفع جودة الصور', layout, finalize=True)
    
    # تشغيل الأمر في thread منفصل
    def run_process():
        command = [
            sys.executable, INFERENCE_SCRIPT,
            '-n', options['model_name'],
            '-i', INPUT_DIR,
            '-o', OUTPUT_DIR,
            '--outscale', options['outscale'],
            '--fp32'
        ]
        
        tile_value = options['tile']
        if tile_value and tile_value != '0':
            command.extend(['--tile', tile_value])
        
        if options['suffix']:
            command.extend(['--suffix', options['suffix']])
        
        run_command_gui(command, window, '-OUTPUT-')
        window['-CLOSE-'].update(disabled=False)
    
    threading.Thread(target=run_process, daemon=True).start()
    
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, '-CLOSE-'):
            break
    
    window.close()


def upscale_videos_gui():
    """
    START: MODIFIED SECTION
    واجهة رفع جودة الفيديوهات مع نافذة عرض المخرجات.
    END: MODIFIED SECTION
    """
    video_extensions = ('.mp4', '.mkv', '.mov', '.avi', '.webm')
    videos = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(video_extensions)]
    
    if not videos:
        sg.popup_error('لم يتم العثور على فيديوهات في مجلد الإدخال.', title='خطأ')
        return
    
    sg.popup(f'تم العثور على {len(videos)} فيديو للمعالجة.', title='معلومات')
    
    options = get_upscale_options_gui('الفيديوهات')
    if options is None:
        return
    
    # نافذة عرض التقدم والمخرجات
    layout = [
        [sg.Text('جاري معالجة الفيديوهات...', font=('Arial', 12, 'bold'))],
        [sg.ProgressBar(len(videos), orientation='h', size=(70, 20), key='-PROGRESS-', 
                        bar_color=('green', 'white'))],
        [sg.Text('', key='-STATUS-', size=(80, 1))],
        [sg.Multiline(size=(100, 20), key='-OUTPUT-', autoscroll=True, disabled=True,
                      background_color='black', text_color='white')],
        [sg.Push(), sg.Button('إغلاق', disabled=True, key='-CLOSE-')]
    ]
    
    window = sg.Window('رفع جودة الفيديوهات', layout, finalize=True)
    
    def run_process():
        tile_value = options['tile']
        
        for idx, video_name in enumerate(videos, 1):
            window['-STATUS-'].update(f'معالجة الفيديو {idx}/{len(videos)}: {video_name}')
            window['-OUTPUT-'].print(f"\n{'='*50}")
            window['-OUTPUT-'].print(f"--- معالجة الفيديو: {video_name} ---")
            window['-OUTPUT-'].print(f"{'='*50}\n")
            window.refresh()
            
            video_path = os.path.join(INPUT_DIR, video_name)
            video_size_str = str(os.path.getsize(video_path))
            
            frames_input_dir = os.path.join(INPUT_DIR, video_size_str)
            frames_output_dir = os.path.join(OUTPUT_DIR, video_size_str)
            os.makedirs(frames_input_dir, exist_ok=True)
            os.makedirs(frames_output_dir, exist_ok=True)
            
            # الخطوة 1: استخراج الإطارات
            window['-OUTPUT-'].print("الخطوة 1: استخراج الإطارات...")
            window.refresh()
            extract_command = [
                'ffmpeg', '-i', video_path,
                os.path.join(frames_input_dir, 'frame_%05d.png')
            ]
            if run_command_gui(extract_command, window, '-OUTPUT-') != 0:
                window['-OUTPUT-'].print(f"فشل استخراج الإطارات لـ {video_name}. تخطي...")
                window.refresh()
                continue
            
            # الخطوة 2: رفع جودة الإطارات
            window['-OUTPUT-'].print("\nالخطوة 2: رفع جودة الإطارات...")
            window.refresh()
            upscale_command = [
                sys.executable, INFERENCE_SCRIPT,
                '-n', options['model_name'],
                '-i', frames_input_dir,
                '-o', frames_output_dir,
                '--outscale', options['outscale'],
                '--fp32'
            ]
            
            if tile_value and tile_value != '0':
                upscale_command.extend(['--tile', tile_value])
            
            suffix = options['suffix'] if options['suffix'] else 'out'
            upscale_command.extend(['--suffix', suffix])
            
            if run_command_gui(upscale_command, window, '-OUTPUT-') != 0:
                window['-OUTPUT-'].print(f"فشل رفع جودة الإطارات لـ {video_name}. تخطي...")
                window.refresh()
                continue
            
            # الخطوة 3: تجميع الفيديو (بدون صوت)
            window['-OUTPUT-'].print("\nالخطوة 3: تجميع الفيديو (بدون صوت)...")
            window.refresh()
            video_base_name = os.path.splitext(video_name)[0]
            temp_video_name = f"{video_base_name}_without_voice.mp4"
            temp_video_path = os.path.join(OUTPUT_DIR, temp_video_name)
            
            assemble_command = [
                'ffmpeg', '-framerate', '24',
                '-i', os.path.join(frames_output_dir, f'frame_%05d_{suffix}.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                temp_video_path
            ]
            if run_command_gui(assemble_command, window, '-OUTPUT-') != 0:
                window['-OUTPUT-'].print(f"فشل تجميع الفيديو لـ {video_name}. تخطي...")
                window.refresh()
                continue
            
            # الخطوة 4: إضافة الصوت
            window['-OUTPUT-'].print("\nالخطوة 4: إضافة الصوت...")
            window.refresh()
            final_video_name = f"{video_base_name}_upscaled.mp4"
            final_video_path = os.path.join(OUTPUT_DIR, final_video_name)
            
            audio_command = [
                'ffmpeg', '-i', temp_video_path, '-i', video_path,
                '-c:v', 'copy', '-c:a', 'aac',
                '-map', '0:v:0', '-map', '1:a:0',
                '-y', final_video_path
            ]
            if run_command_gui(audio_command, window, '-OUTPUT-') != 0:
                window['-OUTPUT-'].print(f"فشل إضافة الصوت لـ {video_name}. تخطي...")
                window.refresh()
                continue
            
            # الخطوة 5: تنظيف الملفات المؤقتة
            window['-OUTPUT-'].print("\nالخطوة 5: تنظيف الملفات المؤقتة...")
            window.refresh()
            try:
                shutil.rmtree(frames_input_dir)
                shutil.rmtree(frames_output_dir)
                os.remove(temp_video_path)
                window['-OUTPUT-'].print("تم التنظيف بنجاح.")
            except Exception as e:
                window['-OUTPUT-'].print(f"تحذير: لم يتم تنظيف جميع الملفات المؤقتة. {e}")
            
            window['-PROGRESS-'].update(idx)
            window.refresh()
        
        window['-STATUS-'].update('اكتملت جميع العمليات!')
        window['-CLOSE-'].update(disabled=False)
        window.refresh()
    
    threading.Thread(target=run_process, daemon=True).start()
    
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, '-CLOSE-'):
            break
    
    window.close()


def post_process_rename_files_gui(media_type):
    """
    START: MODIFIED SECTION
    واجهة إعادة تسمية الملفات باستخدام PySimpleGUI.
    END: MODIFIED SECTION
    """
    files_to_rename = []
    for filename in os.listdir(OUTPUT_DIR):
        name, ext = os.path.splitext(filename)
        if name.endswith('_out'):
            files_to_rename.append(filename)
    
    if not files_to_rename:
        sg.popup('لم يتم العثور على ملفات تحتوي على اللاحقة "_out" لإعادة تسميتها.', 
                 title='معلومات')
        return
    
    # نافذة عرض الملفات للتأكيد
    file_list = '\n'.join(files_to_rename)
    layout = [
        [sg.Text('سيتم إعادة تسمية الملفات التالية:', font=('Arial', 11, 'bold'))],
        [sg.Multiline(file_list, size=(60, 15), disabled=True)],
        [sg.Text(f'إجمالي الملفات: {len(files_to_rename)}')],
        [sg.Push(), sg.Button('متابعة', button_color=('white', 'green')), 
         sg.Button('إلغاء', button_color=('white', 'red'))]
    ]
    
    window = sg.Window(f'إعادة تسمية {media_type}', layout, modal=True)
    event, values = window.read()
    window.close()
    
    if event in (sg.WIN_CLOSED, 'إلغاء'):
        return
    
    # تنفيذ إعادة التسمية
    renamed_count = 0
    errors = []
    
    for filename in files_to_rename:
        name, ext = os.path.splitext(filename)
        new_name = name[:-4] + ext
        old_path = os.path.join(OUTPUT_DIR, filename)
        new_path = os.path.join(OUTPUT_DIR, new_name)
        try:
            os.rename(old_path, new_path)
            renamed_count += 1
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")
    
    # عرض النتيجة
    if errors:
        error_msg = '\n'.join(errors)
        sg.popup_scrolled(f'تمت إعادة تسمية {renamed_count} ملف.\n\nأخطاء:\n{error_msg}',
                         title='نتيجة العملية', size=(60, 20))
    else:
        sg.popup_ok(f'✅ تمت إعادة تسمية {renamed_count} ملف بنجاح!', title='نجحت العملية')


def post_process_update_db_gui(media_type):
    """
    START: MODIFIED SECTION
    واجهة تحديث أحجام الملفات في قاعدة البيانات باستخدام PySimpleGUI.
    END: MODIFIED SECTION
    """
    output_files = {f: os.path.getsize(os.path.join(OUTPUT_DIR, f)) 
                    for f in os.listdir(OUTPUT_DIR)}
    
    found_matches = {}
    for db_path in DB_FILES:
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for key in data.keys():
                if key in output_files:
                    old_size = data[key].get('file_size', 'N/A')
                    new_size = output_files[key]
                    if old_size != new_size:
                        found_matches[key] = {'old': old_size, 'new': new_size, 'db': db_path}
        except Exception as e:
            sg.popup_error(f'تحذير: لم يتم معالجة قاعدة البيانات {db_path}.\n{e}', 
                          title='تحذير')
    
    if not found_matches:
        sg.popup('لم يتم العثور على ملفات مطابقة في قواعد البيانات تحتاج إلى تحديث.', 
                 title='معلومات')
        return
    
    # إنشاء جدول للعرض
    table_data = [[name, sizes['old'], sizes['new']] 
                  for name, sizes in found_matches.items()]
    
    layout = [
        [sg.Text('الملفات التالية سيتم تحديثها في قواعد البيانات:', 
                 font=('Arial', 11, 'bold'))],
        [sg.Table(values=table_data,
                  headings=['اسم الملف', 'الحجم القديم', 'الحجم الجديد'],
                  auto_size_columns=True,
                  justification='right',
                  num_rows=min(15, len(table_data)),
                  key='-TABLE-')],
        [sg.Text(f'إجمالي الملفات: {len(found_matches)}')],
        [sg.Push(), sg.Button('تحديث', button_color=('white', 'green')), 
         sg.Button('إلغاء', button_color=('white', 'red'))]
    ]
    
    window = sg.Window(f'تحديث قاعدة البيانات - {media_type}', layout, modal=True)
    event, values = window.read()
    window.close()
    
    if event in (sg.WIN_CLOSED, 'إلغاء'):
        return
    
    # تنفيذ التحديث
    updated_count = 0
    for db_path in DB_FILES:
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            made_change = False
            for key, value in data.items():
                if key in found_matches:
                    value['file_size'] = found_matches[key]['new']
                    made_change = True
            
            if made_change:
                with open(db_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                updated_count += 1
        except Exception as e:
            sg.popup_error(f'خطأ في تحديث قاعدة البيانات {db_path}:\n{e}', 
                          title='خطأ')
    
    sg.popup_ok(f'✅ تم تحديث السجلات في قواعد البيانات بنجاح!', title='نجحت العملية')


def post_process_move_files_gui(media_type):
    """
    START: MODIFIED SECTION
    واجهة نقل الملفات واستبدال القديمة باستخدام PySimpleGUI.
    END: MODIFIED SECTION
    """
    files_to_move = []
    output_files = os.listdir(OUTPUT_DIR)
    
    for output_file in output_files:
        for source_folder in SOURCE_MEDIA_FOLDERS:
            potential_dest_path = os.path.join(source_folder, output_file)
            if os.path.exists(potential_dest_path):
                src_path = os.path.join(OUTPUT_DIR, output_file)
                files_to_move.append((src_path, potential_dest_path))
                break
    
    if not files_to_move:
        sg.popup('لم يتم العثور على ملفات أصلية لاستبدالها.', title='معلومات')
        return
    
    # إنشاء قائمة للعرض
    file_list = []
    for src, dest in files_to_move:
        file_list.append(f"من: {src}")
        file_list.append(f"إلى: {dest}")
        file_list.append("---")
    
    files_text = '\n'.join(file_list)
    
    layout = [
        [sg.Text('⚠️ تحذير: هذه العملية لا يمكن التراجع عنها!', 
                 font=('Arial', 12, 'bold'), text_color='red')],
        [sg.Text('سيتم نقل الملفات التالية واستبدال الأصلية:')],
        [sg.Multiline(files_text, size=(80, 20), disabled=True)],
        [sg.Text(f'إجمالي الملفات: {len(files_to_move)}')],
        [sg.Checkbox('أنا متأكد من رغبتي في استبدال الملفات', 
                     key='-CONFIRM-', default=False)],
        [sg.Push(), sg.Button('نقل واستبدال', button_color=('white', 'red')), 
         sg.Button('إلغاء', button_color=('white', 'green'))]
    ]
    
    window = sg.Window(f'نقل واستبدال {media_type}', layout, modal=True)
    event, values = window.read()
    window.close()
    
    if event in (sg.WIN_CLOSED, 'إلغاء'):
        return
    
    if not values['-CONFIRM-']:
        sg.popup_error('يجب التأكيد على العملية!', title='خطأ')
        return
    
    # تنفيذ النقل
    moved_count = 0
    errors = []
    
    for src, dest in files_to_move:
        try:
            shutil.move(src, dest)
            moved_count += 1
        except Exception as e:
            errors.append(f"{os.path.basename(src)}: {str(e)}")
    
    # عرض النتيجة
    if errors:
        error_msg = '\n'.join(errors)
        sg.popup_scrolled(f'تم نقل واستبدال {moved_count} ملف.\n\nأخطاء:\n{error_msg}',
                         title='نتيجة العملية', size=(60, 20))
    else:
        sg.popup_ok(f'✅ تم نقل واستبدال {moved_count} ملف بنجاح!', title='نجحت العملية')


def post_process_gui(media_type):
    """
    START: MODIFIED SECTION
    القائمة الرئيسية للمعالجة اللاحقة باستخدام PySimpleGUI.
    END: MODIFIED SECTION
    """
    layout = [
        [sg.Text(f'المعالجة اللاحقة - {media_type}', font=('Arial', 14, 'bold'))],
        [sg.HorizontalSeparator()],
        [sg.Button('إعادة تسمية الملفات (إزالة "_out")', size=(35, 2), 
                   button_color=('white', '#1f77b4'))],
        [sg.Button('تحديث أحجام الملفات في قاعدة البيانات', size=(35, 2), 
                   button_color=('white', '#ff7f0e'))],
        [sg.Button('نقل الملفات إلى الموقع الأصلي (استبدال)', size=(35, 2), 
                   button_color=('white', '#d62728'))],
        [sg.HorizontalSeparator()],
        [sg.Push(), sg.Button('العودة للقائمة الرئيسية', button_color=('white', 'gray'))]
    ]
    
    window = sg.Window('المعالجة اللاحقة', layout, modal=True)
    
    while True:
        event, values = window.read()
        
        if event in (sg.WIN_CLOSED, 'العودة للقائمة الرئيسية'):
            break
        
        if event == 'إعادة تسمية الملفات (إزالة "_out")':
            post_process_rename_files_gui(media_type)
        elif event == 'تحديث أحجام الملفات في قاعدة البيانات':
            post_process_update_db_gui(media_type)
        elif event == 'نقل الملفات إلى الموقع الأصلي (استبدال)':
            post_process_move_files_gui(media_type)
    
    window.close()


def main():
    """
    START: MODIFIED SECTION
    الدالة الرئيسية للبرنامج مع واجهة PySimpleGUI الرئيسية.
    END: MODIFIED SECTION
    """
    # إنشاء المجلدات إذا لم تكن موجودة
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # التحقق من وجود ffmpeg
    if shutil.which("ffmpeg") is None:
        sg.popup_error('❌ خطأ حرج: "ffmpeg" غير مثبت أو غير موجود في مسار النظام.\n'
                      'يرجى تثبيت ffmpeg لمعالجة الفيديوهات.',
                      title='خطأ حرج')
    
    # تصميم الواجهة الرئيسية
    layout = [
        [sg.Text('مدير سير عمل Real-ESRGAN', font=('Arial', 16, 'bold'), 
                 justification='center', expand_x=True)],
        [sg.HorizontalSeparator()],
        [sg.Text('اختر العملية المطلوبة:', font=('Arial', 11))],
        [sg.Button('1. رفع جودة الصور', size=(35, 2), 
                   button_color=('white', '#2ecc71'), key='-UPSCALE_IMG-')],
        [sg.Button('2. رفع جودة الفيديوهات', size=(35, 2), 
                   button_color=('white', '#3498db'), key='-UPSCALE_VID-')],
        [sg.Button('3. المعالجة اللاحقة للصور', size=(35, 2), 
                   button_color=('white', '#f39c12'), key='-POST_IMG-')],
        [sg.Button('4. المعالجة اللاحقة للفيديوهات', size=(35, 2), 
                   button_color=('white', '#e67e22'), key='-POST_VID-')],
        [sg.HorizontalSeparator()],
        [sg.Push(), sg.Button('خروج', button_color=('white', '#e74c3c'), size=(10, 1))]
    ]
    
    window = sg.Window('Real-ESRGAN Workflow Manager', layout, 
                      element_justification='center')
    
    while True:
        event, values = window.read()
        
        if event in (sg.WIN_CLOSED, 'خروج'):
            break
        
        if event == '-UPSCALE_IMG-':
            upscale_images_gui()
        elif event == '-UPSCALE_VID-':
            upscale_videos_gui()
        elif event == '-POST_IMG-':
            post_process_gui('الصور')
        elif event == '-POST_VID-':
            post_process_gui('الفيديوهات')
    
    window.close()


if __name__ == "__main__":
    main()

# END: FULL SCRIPT
