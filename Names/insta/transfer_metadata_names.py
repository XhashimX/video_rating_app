import json
import os

# 1. تحديد مسارات الملفات
names_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\insta\image_names_detailed.txt"
json_file_path = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo pic.json"

# --- الخطوة الأولى: قراءة وتحليل ملف الأسماء المفصل ---
print(f"جارٍ قراءة البيانات المفصلة من: {os.path.basename(names_file_path)}")
source_data = []
try:
    with open(names_file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            
            parts = [p.strip() for p in line.split(' : ', 2)]
            if len(parts) == 3:
                try:
                    # تخزين البيانات في قائمة قواميس لتسهيل الوصول إليها
                    source_data.append({
                        'original_line_index': i,
                        'filename': parts[0],
                        'size': int(parts[1]),
                        'name': parts[2]
                    })
                except ValueError:
                    print(f"تحذير: تم تجاهل السطر رقم {i+1} بسبب تنسيق الحجم غير الصحيح ← '{line}'")
            else:
                print(f"تحذير: تم تجاهل السطر رقم {i+1} بسبب التنسيق غير الصحيح ← '{line}'")
                
    print(f"تمت قراءة {len(source_data)} سجل صالح من ملف الأسماء.")

except FileNotFoundError:
    print(f"خطأ: لم يتم العثور على ملف الأسماء في المسار المحدد!\n{names_file_path}")
    exit()

# --- الخطوة الثانية: تحميل بيانات JSON ---
print(f"جارٍ تحميل ملف البيانات: {os.path.basename(json_file_path)}")
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        elo_data = json.load(f)
except FileNotFoundError:
    print(f"خطأ: لم يتم العثور على ملف JSON في المسار المحدد!\n{json_file_path}")
    exit()
except json.JSONDecodeError:
    print(f"خطأ: ملف JSON تالف ولا يمكن قراءته.")
    exit()

# --- الخطوة الثالثة: تنفيذ عملية المطابقة والتحديث ---
print("\n... بدء عملية المطابقة والتحديث ...")
# مجموعة (set) لتتبع فهارس الأسطر التي تم تطابقها بنجاح
matched_source_indices = set()
size_matches = 0
name_matches = 0

# المرحلة أ: المطابقة حسب حجم الملف (الأولوية)
print("المرحلة 1: البحث عن تطابق حسب حجم الملف...")
# إنشاء خريطة للأحجام من بيانات المصدر لتجنب البحث المتكرر
size_to_source_map = {}
for index, entry in enumerate(source_data):
    if entry['size'] not in size_to_source_map:
        size_to_source_map[entry['size']] = []
    size_to_source_map[entry['size']].append(index)

for image_info in elo_data.values():
    file_size = image_info.get('file_size')
    if file_size in size_to_source_map and size_to_source_map[file_size]:
        # خذ أول فهرس متاح لهذا الحجم
        source_index = size_to_source_map[file_size].pop(0)
        
        # تحديث الاسم في JSON
        image_info['name'] = source_data[source_index]['name']
        
        # تسجيل أن هذا السطر من المصدر قد تم استخدامه
        matched_source_indices.add(source_index)
        size_matches += 1

print(f"تم العثور على {size_matches} تطابق حسب الحجم.")

# المرحلة ب: المطابقة حسب اسم الملف (للبيانات المتبقية)
print("المرحلة 2: البحث عن تطابق حسب اسم الملف للإدخالات المتبقية...")
for index, entry in enumerate(source_data):
    # تخطى الإدخالات التي تمت مطابقتها بالفعل حسب الحجم
    if index in matched_source_indices:
        continue
    
    # البحث عن اسم الملف كمفتاح في بيانات JSON
    if entry['filename'] in elo_data:
        # تأكد من أننا لا نكتب فوق اسم تم تعيينه بالفعل من تطابق حجم مختلف
        if not elo_data[entry['filename']].get('name'):
            elo_data[entry['filename']]['name'] = entry['name']
            matched_source_indices.add(index)
            name_matches += 1

print(f"تم العثور على {name_matches} تطابق إضافي حسب اسم الملف.")

# --- الخطوة الرابعة: حفظ التغييرات في ملف JSON ---
total_updated = size_matches + name_matches
print(f"\nإجمالي السجلات المحدثة في ملف JSON: {total_updated}")
print("جارٍ حفظ التغييرات في ملف JSON...")
try:
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(elo_data, f, indent=4, ensure_ascii=False)
    print("تم حفظ ملف JSON بنجاح.")
except Exception as e:
    print(f"حدث خطأ أثناء حفظ ملف JSON: {e}")

# --- الخطوة الخامسة: تحديث ملف الأسماء الأصلي ---
print(f"\nجارٍ تحديث ملف '{os.path.basename(names_file_path)}' لإبقاء الإدخالات غير المتطابقة فقط...")
remaining_lines = []
with open(names_file_path, 'r', encoding='utf-8') as f:
    original_lines = f.readlines()

for index, entry in enumerate(source_data):
    if index not in matched_source_indices:
        # أضف السطر الأصلي من الملف إذا لم تتم مطابقته
        original_line_index = entry['original_line_index']
        remaining_lines.append(original_lines[original_line_index])

try:
    with open(names_file_path, 'w', encoding='utf-8') as f:
        f.writelines(remaining_lines)
        
    print(f"تمت إعادة كتابة ملف الأسماء بنجاح.")
    print(f" - تم حذف {len(matched_source_indices)} سطرًا متطابقًا.")
    print(f" - تم الإبقاء على {len(remaining_lines)} سطرًا غير متطابق للمراجعة.")
    print("\nاكتملت العملية بالكامل!")

except Exception as e:
    print(f"حدث خطأ أثناء تحديث ملف الأسماء: {e}")