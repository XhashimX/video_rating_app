import json
import os
import difflib # مكتبة مدمجة في بايثون لحساب تشابه النصوص

# 1. تحديد مسارات الملفات
# تأكد من أن هذا المسار يشير إلى الملف الذي يحتوي على الـ 11 سطراً المتبقية
names_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\insta\image_names_detailed.txt"
json_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo pic.json"

# --- الخطوة الأولى: قراءة وتحليل الأسطر المتبقية ---
unmatched_data = []
try:
    with open(names_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ' : ' in line:
                parts = [p.strip() for p in line.split(' : ', 2)]
                if len(parts) == 3:
                    try:
                        unmatched_data.append({
                            'filename': parts[0],
                            'size': int(parts[1]),
                            'name': parts[2]
                        })
                    except ValueError:
                        continue # تجاهل الأسطر ذات التنسيق الخاطئ
except FileNotFoundError:
    print(f"خطأ: لم يتم العثور على ملف الأسماء في المسار: {names_file_path}")
    exit()

# --- الخطوة الثانية: تحميل بيانات JSON التي لا تزال بدون اسم ---
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        elo_data = json.load(f)
        
    # فلترة بيانات JSON لإبقاء فقط الإدخالات التي ليس لها اسم بعد
    # هذا يجعل البحث أسرع وأكثر صلة
    json_targets = {
        filename: data for filename, data in elo_data.items()
        if not data.get('name') and data.get('file_size') is not None
    }
    if not json_targets:
        print("لا توجد صور بدون اسم في ملف JSON للمقارنة بها.")
        exit()

except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"خطأ في قراءة ملف JSON: {e}")
    exit()


# --- الخطوة الثالثة: تحليل كل إدخال غير متطابق وطباعة تقرير ---

print("--- بدء تحليل التطابقات المحتملة ---\n")

if not unmatched_data:
    print("ملف الأسماء فارغ. لا يوجد شيء لتحليله.")
    exit()

# المرور على كل سطر من الأسطر الـ 11 المتبقية
for entry in unmatched_data:
    source_filename = entry['filename']
    source_size = entry['size']
    source_name = entry['name']
    
    print("======================================================================")
    print(f"🔎 تحليل الإدخال: [الاسم: {source_name}] [الحجم: {source_size}]")
    print(f"   [اسم الملف المصدر: {source_filename}]")
    print("----------------------------------------------------------------------")
    
    size_suggestions = []
    name_suggestions = []

    # مقارنة الإدخال الحالي مع كل هدف متاح في ملف JSON
    for target_filename, target_data in json_targets.items():
        target_size = target_data['file_size']
        
        # 1. حساب فرق الحجم
        size_diff = abs(source_size - target_size)
        size_suggestions.append((size_diff, target_filename, target_size))
        
        # 2. حساب تشابه الاسم
        similarity = difflib.SequenceMatcher(None, source_filename, target_filename).ratio()
        name_suggestions.append((similarity, target_filename))

    # --- فرز النتائج واختيار أفضل 3 لكل فئة ---
    size_suggestions.sort(key=lambda x: x[0]) # الفرز حسب فرق الحجم (الأصغر أولاً)
    name_suggestions.sort(key=lambda x: x[0], reverse=True) # الفرز حسب التشابه (الأكبر أولاً)
    
    # --- طباعة أفضل التطابقات المحتملة حسب الحجم ---
    print("\n💡 أفضل 3 تطابقات محتملة (حسب أقرب حجم ملف):")
    if not size_suggestions:
        print("   - لا توجد اقتراحات.")
    else:
        for diff, filename, size in size_suggestions[:3]:
            print(f"   - فرق الحجم: {diff} بايت | الحجم: {size} | الملف: {filename}")

    # --- طباعة أفضل التطابقات المحتملة حسب تشابه الاسم ---
    print("\n💡 أفضل 3 تطابقات محتملة (حسب تشابه اسم الملف):")
    if not name_suggestions:
        print("   - لا توجد اقتراحات.")
    else:
        for score, filename in name_suggestions[:3]:
            # تحويل درجة التشابه إلى نسبة مئوية
            percentage = score * 100
            print(f"   - نسبة التشابه: {percentage:.1f}% | الملف: {filename}")
            
    print("\n======================================================================\n")

print("--- انتهى التحليل ---")