# START: MODIFIED SECTION
import json
import re
import os
import random
from datetime import datetime

# --- دوال مساعدة للتحميل والحفظ ---

def _load_json_file(filepath):
    """
    تحميل ملف JSON مع معالجة الأخطاء الأساسية.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # التعامل مع الملفات الفارغة
            content = f.read()
            if not content.strip():
                return {} # إرجاع قاموس فارغ إذا كان الملف فارغًا
            return json.loads(content)
    except FileNotFoundError:
        print(f"Error: File not found {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file {filepath}")
        return None
    except Exception as e:
        print(f"Unexpected error loading {filepath}: {e}")
        return None

def _save_json_file(data, filepath):
    """
    حفظ البيانات في ملف JSON.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True, f"Data successfully saved to: {os.path.basename(filepath)}"
    except Exception as e:
        print(f"Error saving file {filepath}: {e}")
        return False, f"Error saving file {os.path.basename(filepath)}: {e}"

def _sanitize_filename(name):
    """
    إزالة الأحرف غير الصالحة من اسم الملف.
    """
    return re.sub(r'[\\/*?:"<>|]', "", name)


# --- الدالة الأولى: الاستخراج حسب الحجم (مُعاد كتابتها بالكامل) ---

def _extract_sizes_from_content(content):
    """
    تستخرج أحجام الملفات من محتوى نصي.
    """
    sizes = set()
    # جميع الأنماط للعثور على الأحجام
    pattern1 = r'\(Size:\s*(\d+)\)'
    pattern2_block = r'"file_size":\s*\[(.*?)\]'
    pattern3 = r'"file_size":\s*(\d+)(?![\],])'

    for p in [pattern1, pattern3]:
        matches = re.findall(p, content)
        for size_str in matches:
            try:
                sizes.add(int(size_str))
            except ValueError:
                print(f"Warning: Found invalid size: {size_str}")

    block_matches = re.findall(pattern2_block, content, re.DOTALL)
    for block_content in block_matches:
        size_strs_in_block = re.findall(r'(\d+)', block_content)
        for size_str in size_strs_in_block:
            try:
                sizes.add(int(size_str))
            except ValueError:
                print(f"Warning: Found invalid size in block: {size_str}")
    
    return list(sizes)

def function_extract_by_size(input_content, database_files, base_output_path, original_filename="content"):
    """
    تبحث عن فيديوهات مطابقة للأحجام المستخرجة من المحتوى وتبني ملفًا جديدًا.
    هذه النسخة لا تستخدم input() وتقبل الوسائط مباشرة.
    """
    try:
        if not input_content or not input_content.strip():
            return {'success': False, 'message': 'المحتوى المدخل فارغ.'}

        sizes_to_find = _extract_sizes_from_content(input_content)
        if not sizes_to_find:
            return {'success': False, 'message': 'لم يتم العثور على أي أحجام ملفات صالحة في المحتوى المقدم. تأكد من أن التنسيق هو (Size: 123456).'}
        
        sizes_set = set(sizes_to_find)
        matched_entries = {}

        for db_path in database_files:
            db_data = _load_json_file(db_path)
            if db_data and isinstance(db_data, dict):
                for filename, details in db_data.items():
                    if "file_size" in details and details["file_size"] in sizes_set:
                        if filename not in matched_entries:
                            matched_entries[filename] = details
            elif db_data is None:
                 print(f"Warning: Could not load or find database file: {db_path}")

        if not matched_entries:
            return {'success': False, 'message': f"تم العثور على {len(sizes_to_find)} حجم، ولكن لم يتم العثور على أي فيديوهات مطابقة في قواعد البيانات المحددة."}

        # إنشاء اسم ملف فريد للناتج
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename_base = _sanitize_filename(os.path.splitext(original_filename)[0])
        output_filename = f"Extracted_from_{output_filename_base}_{timestamp}.json"
        output_filepath = os.path.join(base_output_path, output_filename)

        success, message = _save_json_file(matched_entries, output_filepath)

        if success:
            final_message = f"نجحت العملية! تم العثور على {len(matched_entries)} فيديو مطابق وحفظها في الملف: <strong>{output_filename}</strong>"
            return {'success': True, 'message': final_message}
        else:
            return {'success': False, 'message': f"فشل حفظ الملف: {message}"}

    except Exception as e:
        print(f"Error in function_extract_by_size: {e}")
        return {'success': False, 'message': f"حدث خطأ غير متوقع: {e}"}


# --- الدالة الثانية: صنع المسابقات (مُعاد كتابتها بالكامل) ---

def _parse_range_list(input_str, value_type=int):
    """
    تحلل سلسلة نصية مثل '1000, 1200-1400' إلى قائمة من النطاقات.
    """
    if not input_str or not input_str.strip():
        return []
    
    ranges = []
    parts = [p.strip() for p in input_str.split(',') if p.strip()]
    for part in parts:
        if '-' in part:
            try:
                low_str, high_str = part.split('-', 1)
                low = value_type(low_str.strip())
                high = value_type(high_str.strip())
                if low <= high:
                    ranges.append((low, high))
            except (ValueError, IndexError):
                continue
        else:
            try:
                val = value_type(part.strip())
                ranges.append((val, val)) # نطاق من قيمة واحدة
            except ValueError:
                continue
    return ranges

def _filter_videos_non_interactive(videos_data, filters):
    """
    تطبق الفلاتر على بيانات الفيديو بناءً على قاموس الفلاتر.
    هذه النسخة لا تستخدم input().
    """
    rating_ranges = _parse_range_list(filters.get('rating', ''), int)
    ts_ranges = _parse_range_list(filters.get('times_shown', ''), int)
    tag_list = [t.strip().lower() for t in filters.get('tags', '').split(',') if t.strip()]

    filtered_videos = {}
    for vid, details in videos_data.items():
        keep = True

        # فلتر التقييم
        if rating_ranges:
            vid_rating = details.get('rating')
            if vid_rating is None or not any(low <= vid_rating <= high for low, high in rating_ranges):
                keep = False
        if not keep: continue

        # فلتر مرات الظهور
        if ts_ranges:
            vid_ts = details.get('times_shown')
            if vid_ts is None or not any(low <= vid_ts <= high for low, high in ts_ranges):
                keep = False
        if not keep: continue
        
        # فلتر الوسوم
        if tag_list:
            vid_tags_str = details.get('tags', '').lower()
            vid_tags_set = {t.strip() for t in vid_tags_str.split(',')}
            # يجب أن تتطابق جميع الوسوم المطلوبة
            if not all(req_tag in vid_tags_set for req_tag in tag_list):
                keep = False
        if not keep: continue

        if keep:
            filtered_videos[vid] = details
    
    return filtered_videos

# START: MODIFIED SECTION
def function_make_competition(input_json_path, base_output_path, settings):
    """
    تنشئ ملف مسابقات مخصص بناءً على الإعدادات المقدمة.
    هذه النسخة لا تستخدم input() وتقبل الوسائط مباشرة.
    """
    try:
        if not os.path.exists(input_json_path):
            return {'success': False, 'message': f"ملف البيانات الأساسي غير موجود: {os.path.basename(input_json_path)}"}
        
        videos_data = _load_json_file(input_json_path)
        if not videos_data or not isinstance(videos_data, dict):
            return {'success': False, 'message': 'ملف البيانات الأساسي فارغ أو بتنسيق غير صحيح.'}

        # تطبيق الفلاتر
        filters = settings.get('filters', {})
        filtered_videos = _filter_videos_non_interactive(videos_data, filters)

        if not filtered_videos:
            return {'success': False, 'message': 'لم يتم العثور على أي فيديوهات تطابق الفلاتر المحددة.'}

        num_videos = settings.get('num_videos', 2)
        if len(filtered_videos) < num_videos:
            return {'success': False, 'message': f"عدد الفيديوهات بعد الفلترة ({len(filtered_videos)}) أقل من العدد المطلوب للمسابقة ({num_videos})."}
        
        video_names = list(filtered_videos.keys())
        random.shuffle(video_names) # خلط عشوائي للفيديوهات

        competitions = []
        for i in range(0, len(video_names), num_videos):
            chunk = video_names[i:i + num_videos]
            if len(chunk) == num_videos:
                competition_entry = {
                    "videos": chunk,
                    "rating": [filtered_videos[name].get("rating", 1000) for name in chunk],
                    "file_size": [filtered_videos[name].get("file_size", 0) for name in chunk],
                    "mode": 1,
                    "num_videos": num_videos,
                    "ranking_type": "winner_only",
                    "competition_type": "random" # يمكن تطوير هذا لاحقًا
                }
                competitions.append(competition_entry)
        
        # تطبيق الحد الأقصى لعدد المسابقات إذا تم تحديده
        limit = settings.get('limit')
        if limit and limit > 0 and len(competitions) > limit:
            competitions = competitions[:limit]

        if not competitions:
            return {'success': False, 'message': 'لم يتمكن من إنشاء أي مسابقات. قد يكون عدد الفيديوهات المفلترة غير كافٍ.'}

        # --- بداية الجزء المُعدل ---
        # إنشاء اسم ملف فريد للناتج بالنمط المطلوب
        random_suffix = random.randint(100, 999) # إنشاء 4 أرقام عشوائية
        input_basename = _sanitize_filename(os.path.splitext(os.path.basename(input_json_path))[0])
        output_filename = f"topcut_{input_basename}_{random_suffix}.json" # بناء الاسم الجديد
        output_filepath = os.path.join(base_output_path, output_filename)
        # --- نهاية الجزء المُعدل ---

        success, message = _save_json_file(competitions, output_filepath)

        if success:
            final_message = f"نجحت العملية! تم إنشاء {len(competitions)} مسابقة وحفظها في الملف: <strong>{output_filename}</strong>"
            return {'success': True, 'message': final_message}
        else:
            return {'success': False, 'message': f"فشل حفظ الملف: {message}"}

    except Exception as e:
        print(f"Error in function_make_competition: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f"حدث خطأ غير متوقع: {e}"}
# END: MODIFIED SECTION