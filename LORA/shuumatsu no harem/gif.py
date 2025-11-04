# -*- coding: utf-8 -*-
import os
import subprocess

def extract_frames_for_gif(gif_path):
    """
    يأخذ مسار ملف GIF، وينشئ مجلدًا، ويستخرج إطاراته كصور PNG.
    """
    print(f"   - 🖼️  جاري معالجة (استخراج إطارات): {os.path.basename(gif_path)}")
    
    # إنشاء اسم ومسار المجلد الجديد
    folder_name = os.path.splitext(os.path.basename(gif_path))[0]
    output_folder_path = os.path.join(os.path.dirname(gif_path), folder_name)

    # إنشاء المجلد
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    # بناء وتشغيل أمر FFmpeg
    output_frames_pattern = os.path.join(output_folder_path, 'frame%04d.png')
    command = ['ffmpeg', '-i', gif_path, output_frames_pattern]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   - ✅ نجحت عملية استخراج الإطارات.")
    except FileNotFoundError:
        raise # سيتم التقاط هذا الخطأ في الدالة الرئيسية
    except subprocess.CalledProcessError as e:
        print(f"   - ❌ فشلت عملية FFmpeg. قد يكون الملف تالفًا. الخطأ: {e}")

def convert_gif_to_mp4(gif_path):
    """
    يأخذ مسار ملف GIF ويقوم بتحويله إلى فيديو MP4 بنفس الاسم.
    """
    print(f"   - 🎬 جاري معالجة (تحويل إلى MP4): {os.path.basename(gif_path)}")

    # إنشاء اسم ومسار ملف الفيديو الناتج
    mp4_filename = os.path.splitext(os.path.basename(gif_path))[0] + '.mp4'
    output_mp4_path = os.path.join(os.path.dirname(gif_path), mp4_filename)
    
    # بناء أمر FFmpeg (مع تحسينات للجودة والتوافق)
    command = [
        'ffmpeg',
        '-i', gif_path,
        '-movflags', '+faststart',
        '-pix_fmt', 'yuv420p',
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
        '-y', # للكتابة فوق الملف إذا كان موجودًا
        output_mp4_path
    ]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   - ✅ نجحت عملية التحويل إلى MP4.")
    except FileNotFoundError:
        raise # سيتم التقاط هذا الخطأ في الدالة الرئيسية
    except subprocess.CalledProcessError as e:
        print(f"   - ❌ فشلت عملية FFmpeg. قد يكون الملف تالفًا. الخطأ: {e}")


def main():
    """
    الدالة الرئيسية التي تعرض القائمة وتنفذ العملية المختارة.
    """
    # --- عرض قائمة الاختيار ---
    print("=" * 60)
    print("اختر العملية التي تريد تنفيذها على جميع ملفات GIF:")
    print("  [1] استخراج الإطارات إلى صور (PNG)")
    print("  [2] تحويل الملفات إلى فيديو (MP4)")
    print("=" * 60)

    user_choice = ''
    while user_choice not in ['1', '2']:
        user_choice = input("الرجاء إدخال رقم الخيار (1 أو 2): ").strip()
        if user_choice not in ['1', '2']:
            print("إدخال غير صالح. الرجاء المحاولة مرة أخرى.")
    
    # --- بدء العملية ---
    start_directory = os.getcwd()
    print("\n" + "🚀 بدء البحث الشامل عن ملفات GIF في:", start_directory)
    
    found_gifs_count = 0

    try:
        for root, dirs, files in os.walk(start_directory):
            # تجنب البحث في المجلدات التي تم إنشاؤها (إذا كانت العملية هي استخراج الإطارات)
            if user_choice == '1':
                generated_folders = [os.path.splitext(f)[0] for f in files if f.lower().endswith('.gif')]
                dirs[:] = [d for d in dirs if d not in generated_folders]

            for filename in files:
                if filename.lower().endswith('.gif'):
                    found_gifs_count += 1
                    print("-" * 60)
                    
                    gif_full_path = os.path.join(root, filename)
                    
                    if user_choice == '1':
                        extract_frames_for_gif(gif_full_path)
                    elif user_choice == '2':
                        convert_gif_to_mp4(gif_full_path)
                        
    except FileNotFoundError:
        print("\n❌ خطأ فادح: لم يتم العثور على أمر 'ffmpeg'.")
        print("   يرجى التأكد من أن FFmpeg مثبت ومضاف إلى متغيرات البيئة (PATH).")
        return

    # --- عرض النتيجة النهائية ---
    print("=" * 60)
    if found_gifs_count == 0:
        print("🤷 لم يتم العثور على أي ملفات .gif في هذا المجلد أو مجلداته الفرعية.")
    else:
        print(f"🎉 اكتملت العملية بنجاح! تمت معالجة {found_gifs_count} ملف GIF.")

# تشغيل الدالة الرئيسية
if __name__ == "__main__":
    main()