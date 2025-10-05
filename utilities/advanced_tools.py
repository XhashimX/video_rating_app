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
# START: MODIFIED SECTION
def function_make_competition(input_json_path, base_output_path, settings):
    """
    تنشئ ملف مسابقات مخصص بناءً على الإعدادات المقدمة.
    تدعم الآن الفلتر المتقدم "التقييم المتوازن".
    """
    try:
        if not os.path.exists(input_json_path):
            return {'success': False, 'message': f"ملف البيانات الأساسي غير موجود: {os.path.basename(input_json_path)}"}
        
        videos_data = _load_json_file(input_json_path)
        if not videos_data or not isinstance(videos_data, dict):
            return {'success': False, 'message': 'ملف البيانات الأساسي فارغ أو بتنسيق غير صحيح.'}

        filters = settings.get('filters', {})
        # الخطوة 1: تطبيق الفلاتر العامة أولاً (rating, times_shown, tags)
        initial_filtered_videos = _filter_videos_non_interactive(videos_data, filters)

        if not initial_filtered_videos:
            return {'success': False, 'message': 'لم يتم العثور على أي فيديوهات تطابق الفلاتر العامة المحددة.'}

        num_videos = settings.get('num_videos', 2)
        competitions = []
        
        # --- المنطق الجديد: التحقق من وجود فلتر التقييم المتوازن ---
        balanced_rating_filter = filters.get('balanced_rating', '').strip()

        if balanced_rating_filter:
            # الخطوة 2: تحليل فلتر التقييم المتوازن
            parts = [p.strip() for p in balanced_rating_filter.split(',') if p.strip()]
            if len(parts) != 2:
                return {'success': False, 'message': 'فلتر التقييم المتوازن يجب أن يحتوي على قسمين مفصولين بفاصلة. مثال: 1000, 1200-1400'}

            group_a_ranges = _parse_range_list(parts[0], int)
            group_b_ranges = _parse_range_list(parts[1], int)

            # الخطوة 3: تقسيم الفيديوهات المفلترة إلى مجموعتين
            videos_group_a = []
            videos_group_b = []
            for name, details in initial_filtered_videos.items():
                rating = details.get('rating')
                if rating is not None:
                    if any(low <= rating <= high for low, high in group_a_ranges):
                        videos_group_a.append(name)
                    elif any(low <= rating <= high for low, high in group_b_ranges):
                        videos_group_b.append(name)
            
            # الخطوة 4: التحقق من وجود عدد كافٍ من الفيديوهات في كل مجموعة
            num_from_each = num_videos // 2
            if len(videos_group_a) < num_from_each or len(videos_group_b) < num_from_each:
                 return {'success': False, 'message': f"لا يوجد عدد كاف من الفيديوهات في المجموعتين لإنشاء مسابقات. المجموعة الأولى: {len(videos_group_a)} فيديو، المجموعة الثانية: {len(videos_group_b)} فيديو. المطلوب على الأقل {num_from_each} من كل مجموعة."}

            random.shuffle(videos_group_a)
            random.shuffle(videos_group_b)

            # الخطوة 5: بناء المسابقات بشكل متوازن
            while len(videos_group_a) >= num_from_each and len(videos_group_b) >= num_from_each:
                chunk = []
                # أخذ العدد المطلوب من كل مجموعة
                chunk.extend(videos_group_a.pop(0) for _ in range(num_from_each))
                chunk.extend(videos_group_b.pop(0) for _ in range(num_from_each))
                
                # التعامل مع العدد الفردي
                if num_videos % 2 != 0:
                    remaining_pool = videos_group_a + videos_group_b
                    if remaining_pool:
                        extra_vid = random.choice(remaining_pool)
                        chunk.append(extra_vid)
                        # إزالة الفيديو الإضافي من قائمته الأصلية
                        if extra_vid in videos_group_a: videos_group_a.remove(extra_vid)
                        else: videos_group_b.remove(extra_vid)

                random.shuffle(chunk) # خلط الفيديوهات داخل المسابقة
                
                if len(chunk) == num_videos:
                    competition_entry = {
                        "videos": chunk,
                        "rating": [videos_data[name].get("rating", 1000) for name in chunk],
                        "file_size": [videos_data[name].get("file_size", 0) for name in chunk],
                        "mode": 1, "num_videos": num_videos, "ranking_type": "winner_only", "competition_type": "balanced_random"
                    }
                    competitions.append(competition_entry)
        else:
            # --- المنطق القديم: في حال عدم استخدام الفلتر المتوازن ---
            video_names = list(initial_filtered_videos.keys())
            random.shuffle(video_names)
            for i in range(0, len(video_names), num_videos):
                chunk = video_names[i:i + num_videos]
                if len(chunk) == num_videos:
                    competition_entry = {
                        "videos": chunk,
                        "rating": [initial_filtered_videos[name].get("rating", 1000) for name in chunk],
                        "file_size": [initial_filtered_videos[name].get("file_size", 0) for name in chunk],
                        "mode": 1, "num_videos": num_videos, "ranking_type": "winner_only", "competition_type": "random"
                    }
                    competitions.append(competition_entry)
        
        # تطبيق الحد الأقصى للمسابقات وحفظ الملف (هذا الجزء لم يتغير)
        limit = settings.get('limit')
        if limit and limit > 0 and len(competitions) > limit:
            competitions = competitions[:limit]

        if not competitions:
            return {'success': False, 'message': 'لم يتمكن من إنشاء أي مسابقات. قد يكون عدد الفيديوهات المفلترة غير كافٍ.'}

        random_suffix = random.randint(100, 999)
        input_basename = _sanitize_filename(os.path.splitext(os.path.basename(input_json_path))[0])
        output_filename = f"topcut_{input_basename}_{random_suffix}.json"
        output_filepath = os.path.join(base_output_path, output_filename)

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



# START: MODIFIED SECTION
# استبدل الدالة الحالية function_make_competition بالكامل بهذه النسخة
def function_make_competition(input_json_path, base_output_path, settings):
    """
    تنشئ ملف مسابقات مخصص بناءً على الإعدادات المقدمة.
    تدعم الآن الفلاتر المتوازنة للتقييم، مرات الظهور، الوسوم، والأسماء.
    """
    try:
        if not os.path.exists(input_json_path):
            return {'success': False, 'message': f"ملف البيانات الأساسي غير موجود: {os.path.basename(input_json_path)}"}
        
        videos_data = _load_json_file(input_json_path)
        if not videos_data or not isinstance(videos_data, dict):
            return {'success': False, 'message': 'ملف البيانات الأساسي فارغ أو بتنسيق غير صحيح.'}

        filters = settings.get('filters', {})
        # الخطوة 1: تطبيق الفلاتر العامة أولاً (rating, times_shown, tags)
        initial_filtered_videos = _filter_videos_non_interactive(videos_data, filters)

        if not initial_filtered_videos:
            return {'success': False, 'message': 'لم يتم العثور على أي فيديوهات تطابق الفلاتر العامة المحددة.'}

        num_videos = settings.get('num_videos', 2)
        competitions = []
        
        # --- المنطق الجديد: التحقق من وجود فلاتر متوازنة وتحديد أيها نشط ---
        active_balanced_filters = {
            'rating': filters.get('balanced_rating', '').strip(),
            'times_shown': filters.get('balanced_times_shown', '').strip(),
            'tags': filters.get('balanced_tags', '').strip(),
            'name': filters.get('balanced_names', '').strip()
        }
        
        active_filters_list = [k for k, v in active_balanced_filters.items() if v]

        if len(active_filters_list) > 1:
            return {'success': False, 'message': f"خطأ: تم تحديد عدة فلاتر متوازنة ({', '.join(active_filters_list)}). الرجاء استخدام فلتر متوازن واحد فقط في كل مرة."}

        # إذا كان هناك فلتر متوازن واحد نشط
        if len(active_filters_list) == 1:
            filter_type = active_filters_list[0]
            filter_value = active_balanced_filters[filter_type]
            
            # الخطوة 2: تقسيم الفيديوهات إلى مجموعات بناءً على نوع الفلتر
            groups_defs = [p.strip() for p in filter_value.split(',') if p.strip()]
            
            if filter_type in ['rating', 'times_shown', 'tags'] and len(groups_defs) != 2:
                return {'success': False, 'message': f"الفلتر المتوازن لـ '{filter_type}' يجب أن يحتوي على قسمين مفصولين بفاصلة. مثال: '1000, 1200-1400'"}
            
            if filter_type == 'name' and len(groups_defs) < 2:
                return {'success': False, 'message': f"الفلتر المتوازن للأسماء يجب أن يحتوي على اسمين على الأقل مفصولين بفاصلة."}

            video_groups = [[] for _ in groups_defs]
            
            # منطق التقسيم
            if filter_type == 'rating' or filter_type == 'times_shown':
                group_ranges = [_parse_range_list(part, int) for part in groups_defs]
                key_name = 'rating' if filter_type == 'rating' else 'times_shown'
                for name, details in initial_filtered_videos.items():
                    value = details.get(key_name)
                    if value is not None:
                        for i, ranges in enumerate(group_ranges):
                            if any(low <= value <= high for low, high in ranges):
                                video_groups[i].append(name)
                                break
            
            elif filter_type == 'tags':
                group_tags_list = [_parse_string_list(part) for part in groups_defs]
                for name, details in initial_filtered_videos.items():
                    vid_tags_set = {t.strip() for t in details.get('tags', '').lower().split(',')}
                    for i, required_tags in enumerate(group_tags_list):
                        if any(req_tag in vid_tags_set for req_tag in required_tags):
                             video_groups[i].append(name)
                             break
            
            elif filter_type == 'name':
                group_names = [name.lower() for name in groups_defs]
                for vid_name, details in initial_filtered_videos.items():
                    name_field = details.get('name', '').lower()
                    if name_field in group_names:
                        idx = group_names.index(name_field)
                        video_groups[idx].append(vid_name)

            # الخطوة 3: التحقق من وجود عدد كافٍ من الفيديوهات
            num_groups = len(video_groups)
            if num_groups == 0:
                 return {'success': False, 'message': 'لم يتم تعريف أي مجموعات للفلتر المتوازن.'}

            num_from_each = num_videos // num_groups
            
            if num_from_each == 0:
                return {'success': False, 'message': f"عدد الفيديوهات لكل مسابقة ({num_videos}) أصغر من عدد المجموعات المتوازنة ({num_groups})."}

            min_videos_in_any_group = min(len(g) for g in video_groups)
            if min_videos_in_any_group < num_from_each:
                group_counts = ", ".join([f"المجموعة {i+1}: {len(g)} فيديو" for i, g in enumerate(video_groups)])
                return {'success': False, 'message': f"لا يوجد عدد كاف من الفيديوهات في كل المجموعات. ({group_counts}). المطلوب على الأقل {num_from_each} من كل مجموعة."}

            for group in video_groups:
                random.shuffle(group)

            # الخطوة 4: بناء المسابقات بشكل متوازن
            while all(len(g) >= num_from_each for g in video_groups):
                chunk = []
                for group in video_groups:
                    chunk.extend(group.pop(0) for _ in range(num_from_each))
                
                remainder = num_videos % num_groups
                if remainder > 0:
                    remaining_pool = [vid for group in video_groups for vid in group]
                    if len(remaining_pool) >= remainder:
                        extra_vids = random.sample(remaining_pool, remainder)
                        chunk.extend(extra_vids)
                        for vid in extra_vids:
                            for group in video_groups:
                                if vid in group:
                                    group.remove(vid)
                                    break
                
                random.shuffle(chunk)
                
                if len(chunk) == num_videos:
                    competition_entry = {
                        "videos": chunk,
                        "rating": [initial_filtered_videos[name].get("rating", 1000) for name in chunk],
                        "file_size": [initial_filtered_videos[name].get("file_size", 0) for name in chunk],
                        "mode": 1, "num_videos": num_videos, "ranking_type": "winner_only", "competition_type": "balanced_random"
                    }
                    competitions.append(competition_entry)
        
        else: # لا يوجد فلاتر متوازنة، استخدم المنطق العشوائي القديم
            video_names = list(initial_filtered_videos.keys())
            random.shuffle(video_names)
            for i in range(0, len(video_names), num_videos):
                chunk = video_names[i:i + num_videos]
                if len(chunk) == num_videos:
                    competition_entry = {
                        "videos": chunk,
                        "rating": [initial_filtered_videos[name].get("rating", 1000) for name in chunk],
                        "file_size": [initial_filtered_videos[name].get("file_size", 0) for name in chunk],
                        "mode": 1, "num_videos": num_videos, "ranking_type": "winner_only", "competition_type": "random"
                    }
                    competitions.append(competition_entry)
        
        # الجزء المتبقي من الدالة لم يتغير
        limit = settings.get('limit')
        if limit and limit > 0 and len(competitions) > limit:
            competitions = competitions[:limit]

        if not competitions:
            return {'success': False, 'message': 'لم يتمكن من إنشاء أي مسابقات. قد يكون عدد الفيديوهات المفلترة غير كافٍ.'}

        random_suffix = random.randint(100, 999)
        input_basename = _sanitize_filename(os.path.splitext(os.path.basename(input_json_path))[0])
        output_filename = f"topcut_{input_basename}_{random_suffix}.json"
        output_filepath = os.path.join(base_output_path, output_filename)

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

# START: MODIFIED SECTION
# أضف هذه الدالة المساعدة الجديدة في ملف utilities/advanced_tools.py
def _parse_string_list(input_str):
    """
    تحلل سلسلة نصية مفصولة بفواصل مثل 'face, body' إلى قائمة.
    """
    if not input_str or not input_str.strip():
        return []
    return [item.strip().lower() for item in input_str.split(',') if item.strip()]
# END: MODIFIED SECTION