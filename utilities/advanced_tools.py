# START OF FILE utilities/advanced_tools.py

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

def _parse_string_list(input_str):
    """
    تحلل سلسلة نصية مفصولة بفواصل مثل 'face, body' إلى قائمة.
    """
    if not input_str or not input_str.strip():
        return []
    return [item.strip().lower() for item in input_str.split(',') if item.strip()]

# START: MODIFIED FUNCTION in utilities/advanced_tools.py

def _extract_first_long_number(text):
    """
    يستخرج أول سلسلة أرقام متتالية مكونة من 10 خانات أو أكثر.
    """
    if not isinstance(text, str):
        return None
    match = re.search(r'(\d{10,})', text)
    if match:
        return match.group(1)
    return None

def function_compare_and_correct(target_file_paths, master_db_paths, output_option, base_output_path, update_ratings=False):
    """
    تقارن وتصحح قائمة من ملفات البطولات بناءً على قواعد البيانات الرئيسية.
    المميزات الجديدة:
    1. دعم تصحيح عدة ملفات دفعة واحدة.
    2. خيار لتحديث التقييم (اختياري).
    3. البحث عن طريق ID (10 أرقام متتالية) إذا فشل البحث بالحجم.
    """
    print(f"\n--- بدء عملية التصحيح المتقدمة ---")
    
    # التأكد من أن المدخل قائمة
    if isinstance(target_file_paths, str):
        target_file_paths = [target_file_paths]

    if not target_file_paths:
        return {'success': False, 'message': 'لم يتم تحديد أي ملفات للتصحيح.'}

    try:
        # 1. بناء قواميس البحث السريع من قواعد البيانات الرئيسية
        # سنحتاج قاموسين: واحد للحجم (الأدق)، وواحد للـ ID (الاحتياطي)
        master_lookup_size = {}
        master_lookup_id = {}
        loaded_dbs_count = 0
        
        print("جاري تحميل وبناء فهارس البحث...")
        for db_path in master_db_paths:
            db_data = _load_json_file(db_path)
            if db_data and isinstance(db_data, dict):
                loaded_dbs_count += 1
                for vid_name, details in db_data.items():
                    # فهرس الحجم
                    if 'file_size' in details and details['file_size'] is not None:
                        try:
                            f_size = int(details['file_size'])
                            entry_data = {
                                'name': vid_name,
                                'rating': details.get('rating', 1000),
                                'file_size': f_size
                            }
                            master_lookup_size[f_size] = entry_data
                        except ValueError:
                            pass
                    
                    # فهرس الـ ID (استخراج الـ ID من اسم الفيديو في القاعدة الموثوقة)
                    vid_id = _extract_first_long_number(vid_name)
                    if vid_id:
                        # ملاحظة: إذا تكرر الـ ID، سيتم اعتماد آخر واحد تمت قراءته
                        master_lookup_id[vid_id] = {
                            'name': vid_name,
                            'rating': details.get('rating', 1000),
                            'file_size': details.get('file_size', 0)
                        }

        print(f"تم تحميل {loaded_dbs_count} قاعدة بيانات.")
        print(f"- عناصر مفهرسة بالحجم: {len(master_lookup_size)}")
        print(f"- عناصر مفهرسة بالـ ID: {len(master_lookup_id)}")
        
        if not master_lookup_size:
            return {'success': False, 'message': 'فشل تحميل البيانات الرئيسية أو أنها فارغة.'}

        results_log = []
        total_files_processed = 0

        # 2. المرور على كل ملف هدف
        for target_path in target_file_paths:
            target_filename = os.path.basename(target_path)
            print(f"\nمعالجة الملف: {target_filename}...")
            
            target_data = _load_json_file(target_path)
            if not target_data or not isinstance(target_data, list):
                results_log.append(f"{target_filename}: فشل (الملف غير صالح)")
                continue

            # عدادات للملف الحالي
            stats = {'size_match': 0, 'id_match': 0, 'name_fixed': 0, 'rating_updated': 0, 'missing': 0}
            
            # نسخ البيانات للتعديل
            corrected_competitions = json.loads(json.dumps(target_data))

            for competition in corrected_competitions:
                if not all(k in competition for k in ['file_size', 'videos', 'rating']):
                    continue
                
                # المرور على الفيديوهات داخل المسابقة (عادة 2)
                for i in range(len(competition['file_size'])):
                    try:
                        current_size = int(competition['file_size'][i])
                    except (ValueError, TypeError):
                        current_size = 0
                    
                    current_name = competition['videos'][i]
                    master_entry = None
                    found_method = None # 'size' or 'id'

                    # أ) المحاولة الأولى: المطابقة بالحجم (الأدق)
                    if current_size in master_lookup_size:
                        master_entry = master_lookup_size[current_size]
                        found_method = 'size'
                        stats['size_match'] += 1
                    
                    # ب) المحاولة الثانية: المطابقة بالـ ID (إذا فشل الحجم)
                    else:
                        current_id = _extract_first_long_number(current_name)
                        if current_id and current_id in master_lookup_id:
                            master_entry = master_lookup_id[current_id]
                            found_method = 'id'
                            stats['id_match'] += 1
                    
                    # ج) تطبيق التصحيح إذا وجدنا تطابقاً
                    if master_entry:
                        # 1. تصحيح الاسم (دائماً)
                        if current_name != master_entry['name']:
                            competition['videos'][i] = master_entry['name']
                            stats['name_fixed'] += 1
                        
                        # 2. تصحيح التقييم (فقط إذا تم تفعيل الخيار)
                        # ملاحظة: للمطابقة بالـ ID، لن يتم تحديث الحجم كما طلبت، وسيتم تحديث التقييم فقط إذا كان الخيار مفعلاً
                        if update_ratings:
                            if abs(float(competition['rating'][i]) - float(master_entry['rating'])) > 0.01:
                                competition['rating'][i] = master_entry['rating']
                                stats['rating_updated'] += 1
                    else:
                        stats['missing'] += 1
                        print(f"   -> [MISSING] لم يتم العثور على: {current_name} (Size: {current_size})")

            # 3. حفظ الملف المصحح
            if output_option == 'overwrite':
                save_path = target_path
                save_msg = f"تم تحديث الملف الأصلي: {target_filename}"
            else:
                timestamp = datetime.now().strftime("%H%M%S")
                base_name = os.path.splitext(target_filename)[0]
                new_filename = f"{base_name}_corrected_{timestamp}.json"
                save_path = os.path.join(base_output_path, new_filename)
                save_msg = f"تم حفظ ملف جديد: {new_filename}"

            success, msg = _save_json_file(corrected_competitions, save_path)
            if success:
                total_files_processed += 1
                log_entry = (
                    f"<strong>{target_filename}</strong>:<br>"
                    f"&nbsp;&nbsp;- مطابقة بالحجم: {stats['size_match']}, بالـ ID: {stats['id_match']}<br>"
                    f"&nbsp;&nbsp;- تصحيح أسماء: {stats['name_fixed']}, تحديث تقييم: {stats['rating_updated']}<br>"
                    f"&nbsp;&nbsp;- غير موجود: {stats['missing']}"
                )
                results_log.append(log_entry)
            else:
                results_log.append(f"{target_filename}: فشل الحفظ ({msg})")

        final_message = "تقرير العملية:<br>" + "<br><hr>".join(results_log)
        return {'success': True, 'message': final_message}

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f"Critical Error: {e}"}

# END: MODIFIED FUNCTION
def _build_master_lookup(master_db_paths):
    """يبني قاموس بحث سريع من قواعد البيانات الموثوقة."""
    master_lookup = {}
    for db_path in master_db_paths:
        db_data = _load_json_file(db_path)
        if db_data and isinstance(db_data, dict):
            for vid_name, details in db_data.items():
                if 'file_size' in details:
                    master_lookup[details['file_size']] = {
                        'video_name': vid_name,
                        'name': details.get('name', ''), # اسم العرض
                        'rating': details.get('rating', 1000),
                        'file_size': details['file_size']
                    }
    return master_lookup

def _correct_and_load_processed_items(filepath, master_lookup):
    """
    يحمل ملف العناصر المعالجة ويصحح اسم وتقييم كل عنصر.
    """
    items_by_size = {}
    corrections_count = 0
    data = _load_json_file(filepath)
    if not data or not isinstance(data, list):
        return items_by_size, corrections_count
    
    for item in data:
        if 'file_size' not in item:
            continue
        
        file_size = item['file_size']
        if file_size in master_lookup:
            master_entry = master_lookup[file_size]
            # التحقق مما إذا كان هناك تغيير
            if item.get('video_name') != master_entry['video_name'] or abs(item.get('latest_rating', 0) - master_entry['rating']) > 0.01:
                corrections_count += 1
            # التحديث دائمًا لضمان التوافق
            item['video_name'] = master_entry['video_name']
            item['latest_rating'] = master_entry['rating']
        
        items_by_size[file_size] = item
        
    return items_by_size, corrections_count

def _filter_items_by_type(items_list, item_type):
    """فلترة العناصر بناءً على نوعها (فيديو أو صورة)."""
    if item_type == 'video':
        allowed_extensions = VIDEO_EXTENSIONS
    elif item_type == 'image':
        allowed_extensions = IMAGE_EXTENSIONS
    else:
        return items_list
    return [item for item in items_list if item.get('file_extension') in allowed_extensions]


def function_process_weights_and_create_tournament(settings, base_utilities_path):
    """
    الدالة الرئيسية التي تنفذ كل منطق معالجة الأوزان وتصحيح البيانات وإنشاء البطولات.
    """
    try:
        # --- 1. تحديد المسارات والملفات ---
        ARCHIVE_FILE = os.path.join(base_utilities_path, 'tournamentarchive.json')
        PROCESSED_ITEMS_FILE = os.path.join(base_utilities_path, 'processed_videos.json')
        
        master_db_names = [f for f in os.listdir(base_utilities_path) if f.startswith('elo_videos') and f.endswith('.json')]
        if not master_db_names:
            return {'success': False, 'message': "لم يتم العثور على ملفات قاعدة البيانات الموثوقة (elo_videos_*.json)."}
        master_db_paths = [os.path.join(base_utilities_path, f) for f in master_db_names]

        # --- 2. بناء قاموس البحث الموثوق وتصحيح البيانات الحالية ---
        master_lookup = _build_master_lookup(master_db_paths)
        if not master_lookup:
            return {'success': False, 'message': 'فشل بناء قاعدة البيانات الموثوقة.'}

        existing_items_by_size, corrections_in_processed = _correct_and_load_processed_items(PROCESSED_ITEMS_FILE, master_lookup)
        
        # --- 3. معالجة أرشيف البطولات وتصحيح بياناته ---
        archive_data = _load_json_file(ARCHIVE_FILE)
        if not archive_data:
            return {'success': False, 'message': 'ملف أرشيف البطولات (tournamentarchive.json) فارغ أو غير موجود.'}

        archive_items_by_size = {}
        corrections_in_archive = 0

        for tour_key, tour_data in archive_data.items():
            try:
                base_weight = float(tour_key.split('.', 1)[0])
            except (ValueError, IndexError):
                continue

            present_ranks = [r for r in RELEVANT_RANKS if r in tour_data]
            is_two_item = (len(present_ranks) == 2 and "top1" in present_ranks and "top2" in present_ranks)

            for rank_key in present_ranks:
                item_info = tour_data[rank_key]
                item_name_key = "video" if "video" in item_info else "image"
                item_name = item_info.get(item_name_key)
                file_size = item_info.get("file_size")

                if not item_name or not file_size:
                    continue
                
                # تصحيح الاسم والتقييم هنا
                if file_size in master_lookup:
                    master_entry = master_lookup[file_size]
                    if item_name != master_entry['video_name'] or abs(item_info.get("new_rating", 0) - master_entry['rating']) > 0.01:
                        corrections_in_archive += 1
                    item_name = master_entry['video_name']
                    latest_rating = master_entry['rating']
                else:
                    latest_rating = item_info.get("new_rating", item_info.get("old_rating", 0))

                _, ext = os.path.splitext(item_name)
                
                weight = 0
                if is_two_item and rank_key in TWO_ITEM_WEIGHT_RULES:
                    weight = TWO_ITEM_WEIGHT_RULES[rank_key] * base_weight
                elif rank_key in STANDARD_WEIGHT_RULES:
                    rule = STANDARD_WEIGHT_RULES[rank_key]
                    weight = (rule["base_percent"] + rule["bonus_percent"]) * base_weight

                if file_size not in archive_items_by_size:
                    archive_items_by_size[file_size] = {
                        "video_name": item_name,
                        "file_extension": ext.lower(),
                        "total_weight": weight,
                        "latest_rating": latest_rating,
                        "file_size": file_size
                    }
                else:
                    archive_items_by_size[file_size]["total_weight"] += weight
                    archive_items_by_size[file_size]["latest_rating"] = latest_rating # تحديث التقييم لآخر ظهور

        # --- 4. دمج البيانات وحفظها ---
        for fs, data in archive_items_by_size.items():
             existing_items_by_size[fs] = data # الكتابة فوق البيانات القديمة ببيانات الأرشيف المحدثة

        processed_list = sorted(existing_items_by_size.values(), key=lambda x: x.get('total_weight', 0), reverse=True)
        _save_json_file(processed_list, PROCESSED_ITEMS_FILE)
        
        # --- 5. فلترة وبناء قائمة المشاركين للبطولة الجديدة ---
        item_type = settings.get('item_type_filter', 'all')
        selection_method = settings.get('selection_method', 'random')
        num_participants = settings.get('num_participants', 16)
        
        items_with_weight = [item for item in processed_list if item.get("total_weight", 0) > 0]
        
        # فلترة أولية حسب النوع
        filtered_items_for_selection = _filter_items_by_type(items_with_weight, item_type)
        
        selected_items = []

        if selection_method in ['top', 'bottom', 'middle', 'middle_range', 'random']:
            if not filtered_items_for_selection:
                return {'success': False, 'message': f"لا توجد عناصر من نوع '{item_type}' بوزن أكبر من صفر."}
            
            if num_participants > len(filtered_items_for_selection):
                num_participants = len(filtered_items_for_selection)

            if selection_method == 'top':
                selected_items = filtered_items_for_selection[:num_participants]
            elif selection_method == 'bottom':
                selected_items = filtered_items_for_selection[-num_participants:]
            elif selection_method == 'middle':
                start = max(0, (len(filtered_items_for_selection) - num_participants) // 2)
                selected_items = filtered_items_for_selection[start : start + num_participants]
            elif selection_method == 'middle_range':
                total = len(filtered_items_for_selection)
                start = total // 4
                end = total * 3 // 4
                middle_pool = filtered_items_for_selection[start:end]
                if not middle_pool:
                     return {'success': False, 'message': "لا توجد عناصر كافية لتطبيق فلتر المجال الأوسط."}
                num_to_sample = min(num_participants, len(middle_pool))
                selected_items = random.sample(middle_pool, num_to_sample)
            elif selection_method == 'random':
                selected_items = random.sample(filtered_items_for_selection, num_participants)

        elif selection_method == 'weight_range_manual':
            min_w = settings.get('min_weight', 0)
            max_w = settings.get('max_weight', float('inf'))
            manual_sizes = settings.get('manual_sizes', [])
            
            range_pool = [item for item in filtered_items_for_selection if min_w <= item.get("total_weight", 0) <= max_w]
            
            manual_items = []
            manual_found_count = 0
            manual_not_found = []

            for size in manual_sizes:
                # البحث في القائمة المعالجة أولاً، ثم في قاعدة البيانات الموثوقة
                if size in existing_items_by_size:
                    manual_items.append(existing_items_by_size[size])
                    manual_found_count +=1
                elif size in master_lookup:
                    entry = master_lookup[size]
                    _, ext = os.path.splitext(entry['video_name'])
                    manual_items.append({
                        "video_name": entry['video_name'], "file_extension": ext.lower(),
                        "total_weight": 0, "latest_rating": entry['rating'], "file_size": size
                    })
                    manual_found_count +=1
                else:
                    manual_not_found.append(str(size))
            
            # إزالة العناصر المضافة يدوياً من المجمع لتجنب التكرار
            manual_sizes_set = set(manual_sizes)
            range_pool = [item for item in range_pool if item['file_size'] not in manual_sizes_set]
            
            needed_from_pool = max(0, num_participants - len(manual_items))
            if needed_from_pool > 0 and range_pool:
                num_to_sample = min(needed_from_pool, len(range_pool))
                selected_items = manual_items + random.sample(range_pool, num_to_sample)
            else:
                selected_items = manual_items
            
            if len(selected_items) > num_participants:
                selected_items = selected_items[:num_participants]

        if not selected_items:
            return {'success': False, 'message': "لم يتم اختيار أي عناصر لإنشاء البطولة."}
        
        # --- 6. بناء وحفظ ملف البطولة ---
        random.shuffle(selected_items)
        tournament = []
        for i in range(0, len(selected_items) -1, 2):
            item1 = selected_items[i]
            item2 = selected_items[i+1]
            tournament.append({
                "videos": [item1["video_name"], item2["video_name"]],
                "rating": [item1["latest_rating"], item2["latest_rating"]],
                "file_size": [item1["file_size"], item2["file_size"]],
                "mode": 1, "num_videos": 2, "ranking_type": "winner_only", "competition_type": "random"
            })

# START: MODIFIED SECTION
        # --- 7. حساب الوزن وتجهيز اسم الملف والرسالة النهائية ---

        # حساب الوزن الإجمالي للمشاركين في البطولة
        total_tournament_weight = sum(item.get('total_weight', 0) for item in selected_items)
        
        # إنشاء اسم الملف الجديد
        input_basename = "unknown_source"
        if master_db_names:
            # استخدام اسم أول ملف قاعدة بيانات موثوق كأساس
            input_basename = _sanitize_filename(os.path.splitext(master_db_names[0])[0])
            
        random_suffix = random.randint(100, 999)
        output_filename = f"topcut_{input_basename}_{random_suffix}.json"
        output_filepath = os.path.join(base_utilities_path, output_filename)
        
        _save_json_file(tournament, output_filepath)

        # إعداد رسالة النتيجة النهائية
        final_message = (
            f"اكتملت المعالجة بنجاح!<br>"
            f"- تم تحديث <strong>{corrections_in_processed}</strong> عنصر في `processed_videos.json`.<br>"
            f"- تم تصحيح <strong>{corrections_in_archive}</strong> إدخال أثناء قراءة الأرشيف.<br>"
            f"- تم إنشاء بطولة جديدة بـ <strong>{len(selected_items)}</strong> مشارك.<br>"
            f"- الوزن الإجمالي للبطولة: <strong>{total_tournament_weight:.2f}</strong>.<br>"
            f"- تم حفظ البطولة في الملف: <strong>{output_filename}</strong>."
        )
        if 'manual_not_found' in locals() and manual_not_found:
             final_message += f"<br>- <span class='text-danger'>تحذير: لم يتم العثور على الأحجام التالية: {', '.join(manual_not_found)}.</span>"

        return {'success': True, 'message': final_message}
# END: MODIFIED SECTION

    except Exception as e:
        print(f"Error in function_process_weights_and_create_tournament: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f"حدث خطأ غير متوقع: {e}"}