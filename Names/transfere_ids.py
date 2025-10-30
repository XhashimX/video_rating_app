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
id_to_name_map = {}

try:
    with open(ids_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if ' : ' in line:
                video_id, name = line.split(' : ', 1)
                id_to_name_map[video_id.strip()] = name.strip()

    print(f"تم تحميل {len(id_to_name_map)} معرف (ID) واسم من ملف الأسماء.")

except FileNotFoundError:
    print(f"خطأ: لم يتم العثور على ملف الأسماء في المسار: {ids_file_path}")
    exit()


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
# قائمة لتخزين أسماء الملفات التي لم يتم العثور على ID لها (اختياري، للتحقق)
unmatched_files = []

print("جاري تحديث ملف JSON بالمنطق الجديد...")

# START: MODIFIED SECTION
# المرور على كل عنصر في ملف JSON
for filename, details in video_data.items():
    
    match_found = False # متغير لتتبع إذا وجدنا تطابقاً لهذا الملف

    # الآن، لكل ملف، سنمر على كل ID معروف لدينا في القاموس
    for video_id, name in id_to_name_map.items():
        
        # الشرط الذكي: هل الـ ID (كنص) موجود داخل اسم الملف (كنص)؟
        # مثال: هل "7518842441148009735" موجودة في "somePrefix_7518842441148009735.mp4"؟ -> نعم
        if video_id in filename:
            # إذا وجدنا تطابقاً
            details['name'] = name   # نحدث الاسم
            updated_count += 1       # نزيد العداد
            match_found = True       # نعيّن المتغير إلى True
            break # نوقف البحث عن IDs أخرى لهذا الملف وننتقل للملف التالي لأنه تم العثور على المطلوب

    # إذا انتهت الحلقة الداخلية ولم يتم العثور على أي تطابق
    if not match_found:
        unmatched_files.append(filename)

# END: MODIFIED SECTION

# الخطوة 3: حفظ التغييرات مرة أخرى في ملف JSON
with open(json_file_path, 'w', encoding='utf-8') as f:
    json.dump(video_data, f, indent=4, ensure_ascii=False)

print(f"\nاكتملت العملية. تم تحديث {updated_count} سجل في ملف JSON.")

# طباعة تقرير عن الملفات التي لم يتم العثور على تطابق لها
if unmatched_files:
    print(f"\nتنبيه: لم يتم العثور على ID مطابق لـ {len(unmatched_files)} ملف. إليك بعض الأمثلة:")
    # نطبع أول 5 أمثلة فقط لتجنب إغراق الشاشة
    for f in unmatched_files[:5]:
        print(f" - {f}")