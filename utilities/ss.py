import os

# -------------------------------------------------------------------------------------
# هام: الرجاء تعديل هذا المسار ليتوافق مع المجلد الموجود على جهازك
# -------------------------------------------------------------------------------------
directory_path = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"

# التحقق من وجود المجلد لتجنب الأخطاء
if not os.path.isdir(directory_path):
    print(f"خطأ: المجلد المحدد غير موجود. الرجاء التحقق من المسار: {directory_path}")
else:
    print(f"جاري فحص الملفات في المجلد: {directory_path}\n")

    # الحصول على قائمة بجميع الملفات والمجلدات داخل المسار المحدد
    all_files = os.listdir(directory_path)

    # عداد لتتبع عدد الملفات التي تم تغيير اسمها
    renamed_count = 0

    # المرور على كل اسم ملف في القائمة
    for filename in all_files:
        # إنشاء المسار الكامل للملف القديم
        old_file_path = os.path.join(directory_path, filename)

        # التأكد من أننا نتعامل مع ملف وليس مجلد فرعي
        if os.path.isfile(old_file_path):
            
            # START: MODIFIED SECTION
            # الشرط الجديد: تحقق مما إذا كان اسم الملف يحتوي على النص المحدد
            if "filename=tikwm" in filename:
                try:
                    # 1. نقوم بتقسيم اسم الملف عند أول ظهور لعلامة '_'
                    video_id = filename.split('_')[0]

                    # 2. التحقق من أن الجزء الذي استخرجناه هو رقم بالفعل
                    if video_id.isdigit():
                        # 3. ننشئ اسم الملف الجديد بإضافة الامتداد ".mp4"
                        new_filename = f"{video_id}.mp4"

                        # إنشاء المسار الكامل للملف الجديد
                        new_file_path = os.path.join(directory_path, new_filename)

                        # إعادة تسمية الملف
                        os.rename(old_file_path, new_file_path)

                        # طباعة رسالة تأكيد للمستخدم
                        print(f"تم تغيير اسم: '{filename}'  إلى  '{new_filename}'")
                        renamed_count += 1
                    else:
                        # هذا سيحدث إذا كان الملف يحتوي على "filename=tikwm" لكنه لا يبدأ برقم
                        print(f"تجاهل الملف '{filename}' لأنه لا يبدأ برقم تعريفي صالح.")

                except IndexError:
                    # هذا الجزء سيعمل إذا كان اسم الملف لا يحتوي على علامة '_'
                    print(f"تجاهل الملف '{filename}' لأنه لا يطابق النمط المتوقع.")
                except Exception as e:
                    # للتعامل مع أي أخطاء أخرى قد تحدث (مثل مشاكل في الأذونات)
                    print(f"حدث خطأ أثناء معالجة الملف '{filename}': {e}")
            # END: MODIFIED SECTION


    print(f"\nاكتملت العملية. تم تغيير اسم {renamed_count} ملف بنجاح.")