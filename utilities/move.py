import json
import sys
import os
import shutil
from collections import OrderedDict

# المسارات الثابتة
VIDEO_SOURCE_BASE_DIR = "/storage/emulated/0/Download/NS/TikTok/Elo tik/A1000 elo tik"
VIDEO_DEST_DIR = "/storage/emulated/0/Download/NS/TikTok/Elo tik/rank"

def load_json_data(filepath):
    """تحميل بيانات JSON من ملف."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # استخدام OrderedDict للحفاظ على ترتيب العناصر كما هي في الملف الأصلي
            # هذا مهم لخيارات "أول X" و "آخر X"
            data = json.load(f, object_pairs_hook=OrderedDict)
        return data
    except FileNotFoundError:
        print(f"خطأ: لم يتم العثور على الملف: {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"خطأ: تنسيق JSON غير صالح في الملف: {filepath}")
        return None

def select_first_x(data, count):
    """اختيار أول X عنصر من البيانات."""
    if not isinstance(data, OrderedDict):
        print("تحذير: البيانات ليست OrderedDict، قد لا يكون الترتيب مضمونًا لاختيار 'الأول'.")
    items = list(data.items())
    return OrderedDict(items[:count])

def select_last_x(data, count):
    """اختيار آخر X عنصر من البيانات."""
    if not isinstance(data, OrderedDict):
        print("تحذير: البيانات ليست OrderedDict، قد لا يكون الترتيب مضمونًا لاختيار 'الأخير'.")
    items = list(data.items())
    return OrderedDict(items[-count:])

def advanced_filter_videos(data):
    """فلترة بيانات الفيديو بناءً على معايير متعددة يحددها المستخدم."""
    filtered_data = data.copy()

    # فلترة بناءً على rating
    rating_filter_input = input("أدخل فلتر التقييم (rating) (none, قيمة_محددة, min-max, min1-max1,min2-max2): ").strip().lower()
    if rating_filter_input != "none":
        try:
            temp_filtered = OrderedDict()
            if "," in rating_filter_input:  # نطاقات متعددة
                ranges_str = rating_filter_input.split(",")
                valid_ranges = []
                for r_str in ranges_str:
                    min_val, max_val = map(float, r_str.split("-"))
                    valid_ranges.append((min_val, max_val))
                for k, v in filtered_data.items():
                    if 'rating' in v and any(min_r <= v['rating'] <= max_r for min_r, max_r in valid_ranges):
                        temp_filtered[k] = v
            elif "-" in rating_filter_input:  # نطاق واحد
                min_val, max_val = map(float, rating_filter_input.split("-"))
                for k, v in filtered_data.items():
                    if 'rating' in v and min_val <= v['rating'] <= max_val:
                        temp_filtered[k] = v
            else:  # قيمة محددة
                exact_rating = float(rating_filter_input)
                for k, v in filtered_data.items():
                    if 'rating' in v and v['rating'] == exact_rating:
                        temp_filtered[k] = v
            filtered_data = temp_filtered
        except (ValueError, TypeError):
            print("خطأ: تنسيق فلتر التقييم غير صالح.")
            return data # إرجاع البيانات الأصلية في حالة الخطأ

    # فلترة بناءً على times_shown
    times_shown_filter_input = input("أدخل فلتر عدد مرات العرض (times_shown) (none, قيمة_محددة, أو قيم مفصولة بفاصلة): ").strip().lower()
    if times_shown_filter_input != "none":
        try:
            temp_filtered = OrderedDict()
            if "," in times_shown_filter_input:  # قيم متعددة
                allowed_times = set(map(int, times_shown_filter_input.split(",")))
                for k, v in filtered_data.items():
                    if 'times_shown' in v and v['times_shown'] in allowed_times:
                        temp_filtered[k] = v
            else:  # قيمة واحدة
                exact_times_shown = int(times_shown_filter_input)
                for k, v in filtered_data.items():
                    if 'times_shown' in v and v["times_shown"] == exact_times_shown:
                        temp_filtered[k] = v
            filtered_data = temp_filtered
        except (ValueError, TypeError):
            print("خطأ: تنسيق فلتر عدد مرات العرض غير صالح.")
            return data

    # فلترة بناءً على tags
    tag_filter_input = input("أدخل فلتر الوسوم (tags) (none, وسم_محدد, أو وسوم مفصولة بفاصلة): ").strip()
    if tag_filter_input.lower() != "none":
        temp_filtered = OrderedDict()
        input_tags = {tag.strip().lower() for tag in tag_filter_input.split(",") if tag.strip()}
        if input_tags: # تأكد أن هناك وسوم للفلترة بها
            for k, v in filtered_data.items():
                video_tags_str = v.get("tags", "")
                if isinstance(video_tags_str, str):
                    video_tags = {t.strip().lower() for t in video_tags_str.split(",") if t.strip()}
                    if not input_tags.isdisjoint(video_tags): # تحقق من وجود أي وسم مشترك
                        temp_filtered[k] = v
            filtered_data = temp_filtered
        elif tag_filter_input: # إذا أدخل المستخدم شيئًا ولكنه أصبح فارغًا بعد المعالجة
            print("ملاحظة: لم يتم تحديد وسوم صالحة للفلترة.")


    # فلترة بناءً على win_rate
    win_rate_filter_input = input("أدخل فلتر معدل الفوز (win_rate) (none, قيمة_محددة, min-max, min1-max1,min2-max2): ").strip().lower()
    if win_rate_filter_input != "none":
        try:
            temp_filtered = OrderedDict()
            if "," in win_rate_filter_input:  # نطاقات متعددة
                ranges_str = win_rate_filter_input.split(",")
                valid_ranges = []
                for r_str in ranges_str:
                    min_val, max_val = map(float, r_str.split("-"))
                    valid_ranges.append((min_val, max_val))
                for k, v in filtered_data.items():
                    if 'win_rate' in v and any(min_r <= v['win_rate'] <= max_r for min_r, max_r in valid_ranges):
                        temp_filtered[k] = v
            elif "-" in win_rate_filter_input:  # نطاق واحد
                min_val, max_val = map(float, win_rate_filter_input.split("-"))
                for k, v in filtered_data.items():
                    if 'win_rate' in v and min_val <= v['win_rate'] <= max_val:
                        temp_filtered[k] = v
            else:  # قيمة محددة
                exact_win_rate = float(win_rate_filter_input)
                for k, v in filtered_data.items():
                    if 'win_rate' in v and v['win_rate'] == exact_win_rate:
                        temp_filtered[k] = v
            filtered_data = temp_filtered
        except (ValueError, TypeError):
            print("خطأ: تنسيق فلتر معدل الفوز غير صالح.")
            return data
            
    return filtered_data

def export_to_json(selected_data, original_filepath):
    """تصدير البيانات المختارة إلى ملف JSON جديد."""
    if not selected_data:
        print("لا توجد بيانات لتصديرها.")
        return

    base, ext = os.path.splitext(original_filepath)
    output_file = f"{base}_filtered{ext}"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            json.dump(selected_data, outfile, indent=4, ensure_ascii=False)
        print(f"تم حفظ البيانات المفلترة في: {output_file}")
    except IOError:
        print(f"خطأ: لم يتمكن من الكتابة إلى الملف: {output_file}")

def copy_video_files(selected_data, source_base_dir, dest_dir):
    """نسخ ملفات الفيديو المختارة."""
    if not selected_data:
        print("لا توجد فيديوهات لنسخها.")
        return

    os.makedirs(dest_dir, exist_ok=True)
    copied_count = 0
    skipped_count = 0
    for filename in selected_data.keys():
        source_path = os.path.join(source_base_dir, filename)
        dest_path = os.path.join(dest_dir, filename)
        try:
            if os.path.exists(source_path):
                shutil.copy2(source_path, dest_path)
                print(f"تم نسخ: {filename} إلى {dest_dir}")
                copied_count += 1
            else:
                print(f"تنبيه: الملف المصدر غير موجود، تم تخطي النسخ: {source_path}")
                skipped_count +=1
        except Exception as e:
            print(f"خطأ أثناء نسخ {filename}: {e}")
            skipped_count +=1
    print(f"\nاكتمل النسخ. {copied_count} ملفات تم نسخها, {skipped_count} ملفات تم تخطيها.")

def move_video_files(selected_data, source_base_dir, dest_dir):
    """نقل ملفات الفيديو المختارة."""
    if not selected_data:
        print("لا توجد فيديوهات لنقلها.")
        return

    os.makedirs(dest_dir, exist_ok=True)
    moved_count = 0
    skipped_count = 0
    for filename in selected_data.keys():
        source_path = os.path.join(source_base_dir, filename)
        dest_path = os.path.join(dest_dir, filename)
        try:
            if os.path.exists(source_path):
                shutil.move(source_path, dest_path)
                print(f"تم نقل: {filename} إلى {dest_dir}")
                moved_count += 1
            else:
                print(f"تنبيه: الملف المصدر غير موجود، تم تخطي النقل: {source_path}")
                skipped_count += 1
        except Exception as e:
            print(f"خطأ أثناء نقل {filename}: {e}")
            skipped_count += 1
    print(f"\nاكتمل النقل. {moved_count} ملفات تم نقلها, {skipped_count} ملفات تم تخطيها.")


def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python script_name.py <مسار_ملف_json>")
        sys.exit(1)

    json_filepath = sys.argv[1]
    video_data = load_json_data(json_filepath)

    if not video_data:
        sys.exit(1)

    print(f"تم تحميل {len(video_data)} فيديو من {json_filepath}")

    selected_videos = OrderedDict() # استخدام OrderedDict هنا أيضًا

    while True:
        print("\nاختر طريقة تحديد الفيديوهات:")
        print("1. أول X فيديو")
        print("2. آخر X فيديو")
        print("3. فلاتر متقدمة")
        choice = input("أدخل اختيارك (1-3): ")

        if choice == '1':
            try:
                count = int(input(f"كم عدد الفيديوهات الأولى التي تريد اختيارها (من أصل {len(video_data)})؟ "))
                if 0 < count <= len(video_data):
                    selected_videos = select_first_x(video_data, count)
                    break
                else:
                    print("العدد المدخل غير صالح.")
            except ValueError:
                print("إدخال غير صالح. الرجاء إدخال رقم.")
        elif choice == '2':
            try:
                count = int(input(f"كم عدد الفيديوهات الأخيرة التي تريد اختيارها (من أصل {len(video_data)})؟ "))
                if 0 < count <= len(video_data):
                    selected_videos = select_last_x(video_data, count)
                    break
                else:
                    print("العدد المدخل غير صالح.")
            except ValueError:
                print("إدخال غير صالح. الرجاء إدخال رقم.")
        elif choice == '3':
            selected_videos = advanced_filter_videos(video_data)
            break
        else:
            print("خيار غير صالح. الرجاء المحاولة مرة أخرى.")

    if not selected_videos:
        print("\nلم يتم اختيار أي فيديوهات بناءً على المعايير المحددة.")
        sys.exit(0)

    print(f"\nتم اختيار {len(selected_videos)} فيديو.")
    if len(selected_videos) <= 10: # طباعة أسماء الملفات إذا كان العدد قليلًا
        print("الفيديوهات المختارة:")
        for name in selected_videos.keys():
            print(f"- {name}")
    
    while True:
        print("\nاختر الإجراء المطلوب على الفيديوهات المختارة:")
        print("1. نسخ معلوماتهم إلى ملف JSON جديد")
        print("2. نسخ ملفات الفيديو إلى مجلد 'rank'")
        print("3. نقل ملفات الفيديو إلى مجلد 'rank'")
        print("4. خروج")
        action_choice = input("أدخل اختيارك (1-4): ")

        if action_choice == '1':
            export_to_json(selected_videos, json_filepath)
            break
        elif action_choice == '2':
            copy_video_files(selected_videos, VIDEO_SOURCE_BASE_DIR, VIDEO_DEST_DIR)
            break
        elif action_choice == '3':
            move_video_files(selected_videos, VIDEO_SOURCE_BASE_DIR, VIDEO_DEST_DIR)
            break
        elif action_choice == '4':
            print("الخروج من البرنامج.")
            break
        else:
            print("خيار غير صالح. الرجاء المحاولة مرة أخرى.")

if __name__ == '__main__':
    # التأكد من أن مسارات المجلدات موجودة (اختياري، يمكن إنشاؤها عند الحاجة)
    # if not os.path.exists(VIDEO_SOURCE_BASE_DIR):
    # print(f"تحذير: مجلد مصدر الفيديوهات '{VIDEO_SOURCE_BASE_DIR}' غير موجود.")
    # os.makedirs(VIDEO_DEST_DIR, exist_ok=True) # يتم إنشاؤه عند النسخ/النقل إذا لم يكن موجودًا
    
    main()
