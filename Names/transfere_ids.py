import json
import os

# -------------------------------------------------------------------------------------
# المسارات للملفات المستخدمة - تأكد من صحتها
# -------------------------------------------------------------------------------------
# الملف الذي يحتوي على "ID : name"
ids_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\video_ids_output.txt"

# ملف JSON الذي سيتم تحديثه
json_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"


# الخطوة 1: قراءة ملف الأسماء وتخزين البيانات في قاموس (dictionary) لسهولة البحث
# القاموس هو هيكل بيانات يخزن البيانات على شكل "مفتاح: قيمة" (key: value)
# هنا، المفتاح سيكون هو الـ ID والقيمة ستكون هو الـ name
id_to_name_map = {}

try:
    with open(ids_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # نتأكد أن السطر ليس فارغاً ويحتوي على الفاصل
            if ' : ' in line:
                # نقوم بتقسيم السطر إلى جزئين عند أول " : "
                video_id, name = line.split(' : ', 1)
                
                # .strip() تزيل أي مسافات فارغة غير مرغوبة في البداية أو النهاية
                id_to_name_map[video_id.strip()] = name.strip()

    print(f"تم تحميل {len(id_to_name_map)} معرف (ID) واسم من ملف الأسماء.")

except FileNotFoundError:
    print(f"خطأ: لم يتم العثور على ملف الأسماء في المسار: {ids_file_path}")
    exit() # إيقاف السكربت إذا لم يتم العثور على الملف


# الخطوة 2: قراءة ملف JSON وتحديث حقل "name"
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        video_data = json.load(f)

except FileNotFoundError:
    print(f"خطأ: لم يتم العثور على ملف JSON في المسار: {json_file_path}")
    exit()
except json.JSONDecodeError:
    print(f"خطأ: ملف JSON تالف أو صيغته غير صحيحة في المسار: {json_file_path}")
    exit()


# عداد لتتبع عدد السجلات التي تم تحديثها
updated_count = 0

print("جاري تحديث ملف JSON...")

# START: MODIFIED SECTION
# المرور على كل عنصر في ملف JSON
# .items() تسمح لنا بالوصول إلى المفتاح (filename) والقيمة (details) في نفس الوقت
for filename, details in video_data.items():
    try:
        # استخراج الـ ID من اسم الملف
        # المثال: "1000_7551808062286253319.mp4"
        # 1. نقسمه عند '_' ليصبح ['1000', '7551808062286253319.mp4']
        # 2. نأخذ الجزء الثاني [1] وهو '7551808062286253319.mp4'
        # 3. نقسمه عند '.' ليصبح ['7551808062286253319', 'mp4']
        # 4. نأخذ الجزء الأول [0] وهو الـ ID الذي نبحث عنه
        current_video_id = filename.split('_')[1].split('.')[0]

        # الآن نبحث عن هذا الـ ID في القاموس الذي أنشأناه
        if current_video_id in id_to_name_map:
            # إذا وجدنا الـ ID، نأخذ الاسم المقابل له
            name_to_add = id_to_name_map[current_video_id]
            
            # نقوم بتحديث حقل "name" في بيانات الفيديو الحالية
            details['name'] = name_to_add
            
            # زيادة العداد
            updated_count += 1

    except IndexError:
        # هذا سيحدث إذا كان اسم الملف في JSON لا يتبع النمط المتوقع "رقم_id.mp4"
        print(f"تنبيه: تم تجاهل اسم الملف '{filename}' لأنه لا يطابق النمط المتوقع.")
        continue # استمر للملف التالي

# END: MODIFIED SECTION

# الخطوة 3: حفظ التغييرات مرة أخرى في ملف JSON
# نفتح نفس الملف ولكن هذه المرة في وضع الكتابة 'w' لمسح المحتوى القديم وكتابة الجديد
with open(json_file_path, 'w', encoding='utf-8') as f:
    # json.dump تقوم بكتابة القاموس المحدث في الملف
    # indent=4 تجعل الملف منظم وسهل القراءة للإنسان
    # ensure_ascii=False مهمة جداً لضمان كتابة الأحرف العربية (إذا وجدت) بشكل صحيح
    json.dump(video_data, f, indent=4, ensure_ascii=False)

print(f"\nاكتملت العملية. تم تحديث {updated_count} سجل في ملف JSON.")