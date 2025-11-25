# START: FULL SCRIPT
import os

# --- الإعدادات ---
# المسار الذي يحتوي على الصور المصغرة
thumbnails_dir = r"C:\Users\Stark\Download\myhome\video_rating_app\tikmon\gen 2\thumbnails"

# المسار إلى ملف قاعدة البيانات الذي سيتم تحديثه
output_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\video_ids_output.txt"

# المسارات لملفات السجلات الجديدة
matched_log_path = r"C:\Users\Stark\Download\myhome\video_rating_app\tikmon\gen 2\matched_thumbnails.txt"
# START: MODIFIED SECTION
# تم تغيير الغرض من هذا الملف ليحتوي على أسماء الملفات ذات الصيغة غير الصحيحة
malformed_log_path = r"C:\Users\Stark\Download\myhome\video_rating_app\tikmon\gen 2\none_matched_thumbnails.txt"
# END: MODIFIED SECTION


def update_video_ids():
    """
    تقوم هذه الدالة بتحديث ملف video_ids_output.txt بمعرفات جديدة من مجلد الصور
    وتسجل الملفات المتطابقة والملفات ذات الصيغة غير الصحيحة.
    """
    print("... بدء عملية تحديث قائمة المعرفات ...")

    # 1. قراءة المعرفات الموجودة حالياً في الملف لتجنب التكرار
    existing_ids = set()
    try:
        with open(output_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if ' : ' in line:
                    video_id = line.split(' : ')[0].strip()
                    existing_ids.add(video_id)
        print(f"تم العثور على {len(existing_ids)} معرف موجود مسبقاً.")
    except FileNotFoundError:
        print("ملف 'video_ids_output.txt' غير موجود، سيتم إنشاؤه.")
    except Exception as e:
        print(f"حدث خطأ أثناء قراءة الملف: {e}")
        return

    # 2. تجهيز القوائم لتخزين النتائج
    new_entries = []
    matched_filenames = []
    # START: MODIFIED SECTION
    # قائمة جديدة لتخزين أسماء الملفات التي لا تتبع النمط الصحيح
    malformed_filenames = []
    # END: MODIFIED SECTION

    try:
        filenames = os.listdir(thumbnails_dir)
    except FileNotFoundError:
        print(f"خطأ: لم يتم العثور على مجلد الصور في المسار: {thumbnails_dir}")
        return

    print(f"جاري فحص {len(filenames)} صورة في المجلد...")

    for filename in filenames:
        try:
            base_name = os.path.splitext(filename)[0]
            username, video_id = base_name.rsplit('_', 1)

            # 3. التحقق مما إذا كان المعرف جديداً أو موجوداً مسبقاً
            if video_id in existing_ids:
                # إذا كان المعرف موجوداً مسبقاً، نضيف اسم الملف إلى قائمة المتطابقين
                matched_filenames.append(filename)
            else:
                # إذا كان المعرف جديداً، نجهزه للإضافة إلى قاعدة البيانات الرئيسية
                new_line = f"{video_id} : {username}\n"
                new_entries.append(new_line)
                existing_ids.add(video_id) # نضيفه هنا لتجنب إضافته مرتين

        # START: MODIFIED SECTION
        except ValueError:
            # إذا فشلت عملية rsplit، فهذا يعني أن اسم الملف لا يتبع النمط المطلوب
            print(f"تنبيه: تم العثور على ملف بصيغة غير صحيحة '{filename}'، سيتم تسجيله.")
            # نضيف اسم الملف إلى قائمة الملفات ذات الصيغة غير الصحيحة
            malformed_filenames.append(filename)
            continue
        # END: MODIFIED SECTION

    # 4. إضافة البيانات الجديدة إلى ملف قاعدة البيانات الرئيسي
    if new_entries:
        print(f"تم العثور على {len(new_entries)} معرف جديد. جاري إضافتهم إلى الملف '{os.path.basename(output_file_path)}'...")
        try:
            with open(output_file_path, 'a', encoding='utf-8') as f:
                f.writelines(new_entries)
            print("... تمت إضافة المعرفات الجديدة بنجاح! ...")
        except Exception as e:
            print(f"حدث خطأ أثناء الكتابة في الملف: {e}")
    else:
        print("... لا توجد معرفات جديدة لإضافتها. الملف محدّث بالفعل. ...")

    # 5. كتابة أسماء الملفات المتطابقة (القديمة) في ملف السجل الخاص بها
    if matched_filenames:
        print(f"جاري كتابة {len(matched_filenames)} اسم ملف متطابق في '{os.path.basename(matched_log_path)}'...")
        try:
            with open(matched_log_path, 'a', encoding='utf-8') as f:
                f.write("start now\n")
                for name in matched_filenames:
                    f.write(f"{name}\n")
            print("... تمت الكتابة بنجاح.")
        except Exception as e:
            print(f"حدث خطأ أثناء الكتابة في ملف المتطابقين: {e}")

    # START: MODIFIED SECTION
    # 6. كتابة أسماء الملفات ذات الصيغة غير الصحيحة في ملف السجل الخاص بها
    if malformed_filenames:
        print(f"جاري كتابة {len(malformed_filenames)} اسم ملف بصيغة غير صحيحة في '{os.path.basename(malformed_log_path)}'...")
        try:
            with open(malformed_log_path, 'a', encoding='utf-8') as f:
                f.write("start now\n")
                for name in malformed_filenames:
                    f.write(f"{name}\n")
            print("... تمت الكتابة بنجاح.")
        except Exception as e:
            print(f"حدث خطأ أثناء الكتابة في ملف غير المتطابقين: {e}")
    # END: MODIFIED SECTION

    print("... انتهت العملية. ...")


# تشغيل الدالة الرئيسية
if __name__ == "__main__":
    update_video_ids()

# END: FULL SCRIPT