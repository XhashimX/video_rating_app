import os
import json
import random
import re
from .data_manager import create_backup
from flask import flash
from .video_selector import _select_unique_by_name # تم إضافة هذا السطر للاستيراد

def list_files(exclude_topcut=False):
    """
    يُرجع كافة أسماء الملفات في مجلد 'utilities' التي تنتهي بـ .json.
    """
    files = []
    for f in os.listdir('utilities'):
        if f.endswith('.json'):
            if exclude_topcut and f.startswith('topcut'):
                continue
            files.append(f)
    return files

def list_tournament_files():
    """يُرجع ملفات المسابقات التي تبدأ بـ 'topcut'."""
    return [f for f in os.listdir('utilities') if f.endswith('.json') and f.startswith('topcut')]

def create_tournament_web(selected_file, num_participants, num_videos, ranking_type):
    """
    تُنشئ قالب مسابقة بناءً على الملف المُحدد وعدد المشاركين وعدد الفيديوهات لكل مباراة
    ونوع التصنيف (يُفترض أن يكون 'winner_only' أو 'ranked_type').
    """
    try:
        with open(os.path.join('utilities', selected_file), 'r') as f:
            original_data = json.load(f)
    except Exception as e:
        return {'success': False, 'message': f"Error loading file: {e}"}

    if len(original_data) < num_participants:
        return {'success': False, 'message': "الملف المختار لا يحتوي على عدد كافٍ من الفيديوهات."}

    selected_keys = random.sample(list(original_data.keys()), num_participants)
    participants = []
    for key in selected_keys:
        details = original_data[key]
        participants.append((key, details.get("rating"), details.get("file_size")))

    matches = []
    i = 0
    while i < len(participants):
        group = participants[i:i+num_videos]
        # تعبئة المجموعة بالتكرار الفارغ إذا كانت أقل من num_videos
        while len(group) < num_videos:
            group.append(("", None, None))
        match = {
            "videos": [entry[0] for entry in group],
            "rating": [entry[1] for entry in group],
            "file_size": [entry[2] for entry in group],
            "mode": 1,
            "num_videos": num_videos,
            "ranking_type": ranking_type,
            "competition_type": "random"
        }
        matches.append(match)
        i += num_videos

    unique_id = random.randint(1000, 9999)
    base_name = os.path.splitext(selected_file)[0]
    new_filename = f"topcut_{base_name}_{unique_id}.json"

    try:
        create_backup(matches, is_topcut=True)
        with open(os.path.join('utilities', new_filename), 'w') as f:
            json.dump(matches, f, indent=4)
    except Exception as e:
        return {'success': False, 'message': f"Error saving tournament file: {e}"}

    update_tournament_archive(new_filename, initial_participants=num_participants, final_ranking=None)
    return {'success': True, 'message': f"تم إنشاء المسابقة وحفظها باسم {new_filename}"}



def continue_tournament_web(tournament_file):
    """
    تتم معالجة نتائج الجولة الحالية وإنشاء الجولة التالية.
    عندما يتبقى فائز واحد، يتم تحديد المراكز النهائية وتحديث الأرشيف.
    """
    print(f"\nالدخول إلى دالة continue_tournament_web لملف: {tournament_file}") # طباعة بداية الدالة
    pattern = r"^topcut_(.*)_(\d{4}).json$"
    m = re.match(pattern, tournament_file)
    if not m:
        print(f"خطأ: تنسيق اسم ملف المسابقة غير صالح لـ: {tournament_file}") # طباعة خطأ تنسيق الاسم
        return {'success': False, 'message': "تنسيق اسم ملف المسابقة غير صالح."}
    original_base = m.group(1)
    original_filename = f"{original_base}.json"

    try:
        with open(os.path.join('utilities', original_filename), 'r') as f:
            original_data = json.load(f)
        print(f"تم تحميل الملف الأصلي: {original_filename}") # أمر الطباعة الأول
    except Exception as e:
        print(f"خطأ في تحميل الملف الأصلي {original_filename}: {e}") # طباعة خطأ تحميل الملف الأصلي
        return {'success': False,
                'message': f"Error loading the original file: {e}"}

    try:
        with open(os.path.join('utilities', tournament_file), 'r') as f:
            tournament_matches = json.load(f)
        print(f"تم تحميل ملف المسابقة: {tournament_file}") # أمر الطباعة الثاني
        print(f"عدد المباريات في هذه الجولة: {len(tournament_matches)}") # أمر الطباعة الثالث
    except Exception as e:
        print(f"خطأ في تحميل ملف المسابقة {tournament_file}: {e}") # طباعة خطأ تحميل ملف المسابقة
        return {'success': False,
                'message': f"Error loading the tournament file: {e}"}

    # إذا كان ملف المسابقة فارغاً، فهذا يعني أنه تم الانتهاء منه في معالجة سابقة
    if not tournament_matches:
        msg = "المسابقة منتهية وتم تحديد المراكز النهائية في جولة سابقة."
        print(f"الملف فارغ بعد التحقق. {msg}") # طباعة حالة الملف الفارغ
        # يمكن هنا التحقق من الأرشيف للحصول على النتائج النهائية إذا لزم الأمر لعرضها للمستخدم
        return {'success': True, 'message': msg}


    # إضافة التحقق من تحديث جميع التقييمات قبل معالجة المباريات
    all_ratings_updated = True
    problematic_match_index = -1  # لتخزين المؤشر للمباراة التي تحتوي على فيديو لم يتغير تقييمه
    problematic_video_index = -1  # لتخزين المؤشر للفيديو الذي لم يتغير تقييمه

    print("\nالتحقق من تحديث التقييمات...") # طباعة بداية التحقق
    for match_index, match in enumerate(tournament_matches):
        videos = match.get("videos", [])
        old_ratings = match.get("rating", [])
        # file_sizes = match.get("file_size", []) # لم نعد نستخدمها للبحث

        for video_index in range(len(videos)):
            video = videos[video_index]
            if not video: # تخطي الأماكن الفارغة
                continue

            old_rating = old_ratings[video_index]

            # البحث عن التقييم المحدث باستخدام اسم الفيديو
            updated_rating = original_data.get(video, {}).get("rating")

            # إذا لم يتم العثور على التقييم المحدث في original_data، فهناك مشكلة خطيرة
            if updated_rating is None:
                 print(f"خطأ: لم يتم العثور على التقييم المحدّث للفيديو '{video}'. قد يكون الفيديو قد تم حذفه من الملف الأصلي.")
                 return {'success': False,
                         'message': f"لم يتم العثور على التقييم المحدّث للفيديو '{video}'. يرجى التحقق من الملف الأصلي."}

            # إذا كان التقييم القديم يساوي التقييم الجديد، فذلك يعني أن المباراة لم تكتمل
            if updated_rating == old_rating:
                print(f"التحذير: تقييم الفيديو '{video}' لم يتغير. التقييم القديم: {old_rating}, التقييم الجديد: {updated_rating}")
                # flash(f"تقييم الفيديو '{video}' لم يتغير. يرجى التأكد من إكمال جميع المباريات السابقة.", "warning")
                all_ratings_updated = False
                problematic_match_index = match_index
                problematic_video_index = video_index
                break  # لا حاجة للاستمرار في فحص بقية الفيديوهات في هذه المباراة

        if not all_ratings_updated:
            break  # لا حاجة للاستمرار في فحص بقية المباريات

    if not all_ratings_updated:
        print(f"بعض التقييمات لم تتغير. المباراة المشكلة: {problematic_match_index + 1}, الفيديو المشكل: {problematic_video_index + 1}")
        # إنشاء ملف جديد يحتوي فقط على المباريات التي لم تتم معالجتها بعد
        remaining_matches = []

        # إضافة المباراة التي تحتوي على الفيديو المشكل
        current_match = tournament_matches[problematic_match_index]
        remaining_matches.append(current_match)

        # إضافة جميع المباريات اللاحقة
        if problematic_match_index < len(tournament_matches) - 1:
            remaining_matches.extend(tournament_matches[problematic_match_index + 1:])

        # إنشاء اسم للملف الجديد (إذا لم يتم إنشاؤه بالفعل)
        partial_filename = tournament_file.replace('.json', '_partial.json')

        try:
            # حفظ المباريات المتبقية في ملف جديد
            with open(os.path.join('utilities', partial_filename), 'w') as f:
                json.dump(remaining_matches, f, indent=4)
            print(f"تم إنشاء ملف جزئي للمباريات المتبقية: {partial_filename}")
        except Exception as e:
            print(f"خطأ في إنشاء ملف المباريات المتبقية: {e}")

        flash(f"تقييم الفيديو '{tournament_matches[problematic_match_index]['videos'][problematic_video_index]}' لم يتغير. يرجى التأكد من إكمال جميع المباريات السابقة. المباريات غير المكتملة محفوظة في '{partial_filename}'.", "warning")

        return {'success': False,
                'message': "بعض التقييمات لم تتغير. يرجى التأكد من إكمال جميع المباريات السابقة."}


    # إذا تم تحديث جميع التقييمات، تابع معالجة نتائج الجولة
    print("جميع التقييمات محدّثة. معالجة نتائج الجولة...") # طباعة نجاح التحقق

    round_results = [] # قائمة لتخزين نتائج الجولة الحالية
    # نأخذ num_videos و ranking_type من أول مباراة (يجب أن تكون متسقة في الجولة)
    round_num_videos = tournament_matches[0].get("num_videos", 2)
    round_ranking_type = tournament_matches[0].get("ranking_type", "winner_only")


    # معالجة نتائج جميع مباريات الجولة الحالية
    for match_index, match in enumerate(tournament_matches):
        print(f"\nمعالجة المباراة رقم: {match_index + 1}") # طباعة قبل معالجة المباراة
        candidates = []
        videos = match.get("videos", [])
        old_ratings = match.get("rating", [])
        # file_sizes = match.get("file_size", []) # لم نعد نستخدمها

        for i in range(len(videos)):
            video = videos[i]
            if not video: # تخطي الأماكن الفارغة
                continue
            # في هذه المرحلة، التقييمات في original_data هي التقييمات *بعد* لعب هذه المباراة
            updated_rating = original_data.get(video, {}).get("rating")

            if updated_rating is None:
                 # هذا الخطأ كان يجب أن يتم التقاطه في مرحلة التحقق الأولية، ولكن نتركه هنا كتحقق إضافي
                 print(f"خطأ: لم يتم العثور على التقييم المحدّث للفيديو '{video}' أثناء معالجة النتائج.")
                 return {'success': False,
                         'message': "لم يتم العثور على التقييم المحدّث للفيديو أثناء معالجة النتائج."}

            candidates.append({
                "video": video,
                "old_rating": old_ratings[i],
                "new_rating": updated_rating,
                "file_size": match.get("file_size", [None]*len(videos))[i] # استعادة file_size إذا كان موجوداً في بيانات المباراة
            })

        # فرز المرشحين داخل المباراة الواحدة لتحديد الفائز والخاسر
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c["new_rating"] if c["new_rating"] is not None else -1, # تأكد من التعامل مع None في الترتيب
            reverse=True)

        match_result = {
            "winner": sorted_candidates[0] if len(sorted_candidates) > 0 else None,
            "losers": sorted_candidates[1:] if len(sorted_candidates) > 1 else [],
            "match_number": match_index + 1
        }
        round_results.append(match_result)
        print(f"  نتائج المباراة رقم {match_index + 1}:") # طباعة نتائج المباراة
        print(f"    الفائز: {match_result['winner']['video'] if match_result['winner'] and match_result['winner'].get('video') else 'لا يوجد'}") # طباعة الفائز
        print(f"    الخاسرون: {[l['video'] for l in match_result['losers']] if match_result['losers'] else 'لا يوجد'}") # طباعة الخاسرون

    # تجميع الفائزين والخاسرين من جميع مباريات الجولة
    winners = []
    for result in round_results:
        if result["winner"]:
            winners.append(result["winner"])

    losers = []
    for result in round_results:
        losers.extend(result["losers"])
    # فرز الخاسرين حسب التقييم الجديد لاختيار أفضل 2 للمركزين 3 و 4 لاحقاً إذا لزم الأمر
    losers = sorted(losers, key=lambda c: c["new_rating"] if c["new_rating"] is not None else -1, reverse=True)

    print(f"\nالفائزون في هذه الجولة ({len(winners)}): {[w['video'] for w in winners]}") # أمر الطباعة الثامن: قائمة الفائزين
    print(f"الخاسرون في هذه الجولة ({len(losers)}): {[l['video'] for l in losers]}") # أمر الطباعة التاسع: قائمة الخاسرين

    # حساب عدد المشاركين في الجولة التالية (هم الفائزون من الجولة الحالية)
    num_participants_next_round = len(winners)
    print(f"عدد المشاركين الذين سيتقدمون للجولة التالية: {num_participants_next_round}") # أمر الطباعة العاشر: عدد المشاركين في الجولة التالية

    # --- START: Check if Tournament is Finished (Only 1 Winner Left) ---
    if num_participants_next_round == 1:
        print("\nالمسابقة منتهية: فائز واحد متبقٍ.") # طباعة بداية منطق الفائز الواحد

        # الفائز هو Top 1
        top1_video_entry = winners[0]
        top1_video = top1_video_entry["video"]

        # البحث عن الخاسر من المباراة التي فاز بها Top 1 في round_results
        # (يفترض أن المباراة النهائية كانت ثنائية)
        loser_of_top1_match = None
        for result in round_results:
             if result["winner"] and result["winner"]["video"] == top1_video:
                 if result["losers"]: # يجب أن يكون هناك خاسر واحد في مباراة ثنائية
                      loser_of_top1_match = result["losers"][0]
                 break # Found the match

                # --- بداية التعديل الجذري ---

        # أولاً، نحدد الفائز والخاسر في المباراة النهائية (هذا صحيح بالفعل)
        # Top 1 هو الفائز.
        # Top 2 هو الخاسر.
        
        # ثانياً، بدلاً من إعادة حساب Top 3 و Top 4، نقوم باسترجاعهما من الأرشيف.
        # الأرشيف يحتوي على المراكز المؤقتة الصحيحة التي تم حفظها من جولة نصف النهائي.
        print("INFO: قراءة الأرشيف لاسترجاع المراكز 3 و 4 من الجولة السابقة.")
        archive = load_tournament_archive()
        tournament_id = os.path.splitext(tournament_file)[0]
        previous_round_data = archive.get(tournament_id, {})

        # استرجاع المراكز 3 و 4 الصحيحة. إذا لم تكن موجودة (كما في بطولة من شخصين)، ستكون فارغة.
        top3_entry = previous_round_data.get("top3", {"video": "", "old_rating": None, "new_rating": None, "file_size": None})
        top4_entry = previous_round_data.get("top4", {"video": "", "old_rating": None, "new_rating": None, "file_size": None})

        # الآن نقوم بتجميع القائمة النهائية الصحيحة
        final_ranking = {
            "top1": top1_video_entry,
            "top2": loser_of_top1_match if loser_of_top1_match else {"video": "", "old_rating": None, "new_rating": None, "file_size": None},
            "top3": top3_entry, # <-- القيمة الصحيحة من الأرشيف
            "top4": top4_entry  # <-- القيمة الصحيحة من الأرشيف
        }
        
        # --- نهاية التعديل الجذري ---

        print("  تم تحديد المراكز النهائية:") # أمر الطباعة التاسع عشر
        print(f"    الأول: {final_ranking.get('top1', {}).get('video')}") # أمر الطباعة العشرون
        print(f"    الثاني: {final_ranking.get('top2', {}).get('video')}") # أمر الطباعة الواحد والعشرون
        print(f"    الثالث: {final_ranking.get('top3', {}).get('video')}") # أمر الطباعة الثاني والعشرون
        print(f"    الرابع: {final_ranking.get('top4', {}).get('video')}") # أمر الطباعة الثالث والعشرون

        # تحديث الأرشيف بالنتائج النهائية
        update_tournament_archive(tournament_file, initial_participants=None, final_ranking=final_ranking)
        print("  تم تحديث الأرشيف بالنتائج النهائية.") # طباعة تحديث الأرشيف

        # لا يتم مسح ملف المسابقة

        msg = "المسابقة منتهية وتم تحديد المراكز النهائية."
        print(f"النتيجة: {msg}") # طباعة رسالة النتيجة
        return {'success': True, 'message': msg}

    # --- END: Check if Tournament is Finished ---


    # --- START: Standard Continuation Logic (If not Finished) ---
    # يتم تطبيق هذا المنطق إذا كان عدد المشاركين المتبقين (الفائزين) أكبر من 1
    elif num_participants_next_round >= 2: # نحتاج فيديوهين على الأقل للمتابعة بجولة جديدة
        print(f"\nالدخول إلى منطق الاستمرار القياسي (المتبقين {num_participants_next_round}).") # أمر الطباعة الرابع والعشرون

        # ------------------------------
        # تقسيم الفائزين لمباريات جديدة مع ضمان اختلاف 'names'
        remaining = winners[:]  # نسخة للعمل عليها
        new_matches = []

        while remaining:
            print("DEBUG [continue] remaining videos for next round:",
                  [item['video'] + "|" + str(item.get('new_rating')) for item in remaining])
            # نحول قائمة القواميس إلى tuples لتمريرها للدالة المساعدة
            candidates = [(item['video'], original_data[item['video']]) for item in remaining]
            picked = _select_unique_by_name(candidates, round_num_videos)
            print("DEBUG [continue] picked for this match:",
                  [(vid, original_data.get(vid, {}).get('names')) for vid, _ in picked])

            # نبني المباراة من العناصر المختارة
            match = {
                'videos': [vid for vid, info in picked],
                'rating': [original_data[vid]['rating'] for vid, info in picked], # استخدم التقييم المحدث من original_data
                'file_size': [original_data[vid].get('file_size') for vid, info in picked], # استعادة file_size من original_data
                'mode': 1,
                'num_videos': round_num_videos,
                'ranking_type': round_ranking_type,
                'competition_type': 'random'
            }
            new_matches.append(match)

            # نُزيل المختارين من قائمة الباقين
            picked_ids = {vid for vid, _ in picked}
            remaining = [item for item in remaining if item['video'] not in picked_ids]
        # ------------------------------

        # إذا لم يتم إنشاء مباريات جديدة (مثلاً، كان عدد الفائزين 0 أو 1، وتم التعامل مع حالة 1 أعلاه)
        if not new_matches:
            msg = "المسابقة منتهية أو لا يوجد فيديوهات كافية للجولة التالية."
            print(f"\nالرسالة النهائية (لا توجد مباريات جديدة): {msg}")
            return {'success': True, 'message': msg}


        try:
            create_backup(new_matches, is_topcut=True)
            with open(os.path.join('utilities', tournament_file), 'w') as f:
                json.dump(new_matches, f, indent=4)
        except Exception as e:
            print(f"خطأ في حفظ ملف المسابقة للجولة التالية: {e}") # طباعة خطأ الحفظ
            return {'success': False, 'message': f"Error saving the updated tournament file: {e}"}

        msg = f"تم تحديد المراكز لهذه الجولة. تم إنشاء الجولة التالية."
        # في الجولات القياسية، نقوم بتحديث الأرشيف بمعلومات المراكز المؤقتة (TOP1, TOP2, إلخ)
        # based on the current winners and losers
        ranking_list = winners # بداية الترتيب بالفائزين
        additional_ranks = 4 - len(ranking_list) # إيجاد المساحة المتبقية

        if additional_ranks > 0:
            # إضافة أفضل الخاسرين إلى قائمة الترتيب إذا كان هناك مكان
             # تأكد من أن قائمة losers مرتبة بالفعل حسب new_rating تنازلياً (تم ذلك سابقاً)
            ranking_list.extend(losers[:additional_ranks])

        # التأكد من أن القائمة تحتوي على 4 عناصر على الأقل (بإضافة عناصر فارغة إذا لزم الأمر)
        while len(ranking_list) < 4:
            ranking_list.append(
                {"video": "", "old_rating": None, "new_rating": None, "file_size": None})

        safe_ranking_list = []
        for item in ranking_list[:4]:
            # التأكد من أن العنصر قاموس ويحتوي على مفتاح "video" بقيمة غير فارغة
            if isinstance(item, dict) and item.get("video"):
                safe_ranking_list.append(item)
            else:
                 safe_ranking_list.append({"video": "", "old_rating": None, "new_rating": None, "file_size": None})


        current_round_ranking = {
            "top1": safe_ranking_list[0],
            "top2": safe_ranking_list[1] if len(safe_ranking_list) > 1 else {"video": "", "old_rating": None, "new_rating": None, "file_size": None},
            "top3": safe_ranking_list[2] if len(safe_ranking_list) > 2 else {"video": "", "old_rating": None, "new_rating": None, "file_size": None},
            "top4": safe_ranking_list[3] if len(safe_ranking_list) > 3 else {"video": "", "old_rating": None, "new_rating": None, "file_size": None}
        }
        update_tournament_archive(tournament_file, initial_participants=None, final_ranking=current_round_ranking)
        print("  تم تحديث الأرشيف بالمراكز المؤقتة.") # طباعة تحديث الأرشيف

        print(f"  تم إنشاء {len(new_matches)} مباراة للجولة التالية.") # أمر الطباعة الخامس والعشرون
        if new_matches:
            for i, match in enumerate(new_matches):
                 print(f"    المباراة رقم {i+1}: {match['videos']}") # أمر الطباعة السادس والعشرون

        print(f"  تم حفظ مباريات الجولة التالية في ملف المسابقة.") # أمر الطباعة السابع والعشرون
        print(f"النتيجة: {msg}") # طباعة رسالة النتيجة
        return {'success': True, 'message': msg}

    # --- END: Standard Continuation Logic ---

    # إذا لم يتحقق أي من الشروط (لم يتبقى فائز واحد ولم يتبقى فائزان أو أكثر)،
    # فهذا يعني أنه لم يتبقى أي فائزين (0 فائزين)
    else: # num_participants_next_round == 0
         msg = "المسابقة منتهية: لا يوجد فائزون."
         print(f"\nالرسالة النهائية (لا فائزون): {msg}")
         # يمكن هنا تحديث الأرشيف بنتائج فارغة للمراكز إذا لزم الأمر
         final_ranking_empty = {
             "top1": {"video": "", "old_rating": None, "new_rating": None, "file_size": None},
             "top2": {"video": "", "old_rating": None, "new_rating": None, "file_size": None},
             "top3": {"video": "", "old_rating": None, "new_rating": None, "file_size": None},
             "top4": {"video": "", "old_rating": None, "new_rating": None, "file_size": None}
         }
         update_tournament_archive(tournament_file, initial_participants=None, final_ranking=final_ranking_empty)
         print("  تم تحديث الأرشيف بمراكز فارغة.")
         return {'success': True, 'message': msg}


def update_tournament_archive(tournament_filename, initial_participants, final_ranking):
    """
    يقوم بتحديث (أو إنشاء) ملف أرشيف المسابقات "tournamentarchive.json" مع إزالة التكرارات.
    """
    print(f"بدء تحديث الأرشيف لـ: {tournament_filename}") # طباعة بداية تحديث الأرشيف
    archive_filename = "tournamentarchive.json"
    archive_path = os.path.join('utilities', archive_filename)

    if os.path.exists(archive_path):
        try:
            with open(archive_path, 'r') as f:
                archive = json.load(f)
            print(f"تم تحميل الأرشيف من {archive_path}") # طباعة تحميل الأرشيف
        except Exception as e:
            print(f"خطأ في تحميل الأرشيف، إنشاء أرشيف جديد: {e}") # طباعة خطأ تحميل الأرشيف
            archive = {}
    else:
        print("ملف الأرشيف غير موجود، إنشاء أرشيف جديد.") # طباعة عدم وجود الأرشيف
        archive = {}

    tournament_id = os.path.splitext(tournament_filename)[0]
    if tournament_id not in archive:
        archive[tournament_id] = {}
        if initial_participants is not None:
            archive[tournament_id]["initial_participants"] = initial_participants
            print(f"إضافة مسابقة جديدة إلى الأرشيف: {tournament_id} مع {initial_participants} مشارك مبدئي.") # طباعة إضافة مسابقة جديدة
    else:
        if initial_participants is not None:
            archive[tournament_id]["initial_participants"] = initial_participants
            print(f"تحديث عدد المشاركين المبدئي للمسابقة: {tournament_id} إلى {initial_participants}.") # طباعة تحديث المشاركين المبدئي

    # تحديث التصنيفات النهائية ثم إزالة التكرارات في الأرشيف
    if final_ranking is not None:
        print("تحديث التصنيفات في الأرشيف...") # طباعة تحديث التصنيفات

        # دمج التصنيفات الجديدة مع الموجودة إذا كانت موجودة
        # نفضل القيم الجديدة إذا كانت متوفرة
        for key, value in final_ranking.items():
             # فقط نحدث المراكز إذا كانت القيمة الجديدة ليست فارغة أو تحتوي على فيديو
             if isinstance(value, dict) and value.get("video"):
                 archive[tournament_id][key] = value
                 print(f"  تحديث {key} بـ: {value.get('video')}") # طباعة تحديث مركز
             # إذا كانت القيمة فارغة أو بدون فيديو، لا نحدثها للحفاظ على القيم السابقة إذا كانت موجودة
             elif key in archive[tournament_id] and isinstance(archive[tournament_id][key], dict) and archive[tournament_id][key].get("video"):
                 # إذا كان هناك قيمة سابقة غير فارغة، احتفظ بها ولا تستبدلها بالقيمة الفارغة الجديدة
                 print(f"  الاحتفاظ بالقيمة السابقة لـ {key}: {archive[tournament_id][key].get('video')}")
                 pass # احتفظ بالقيمة السابقة
             else:
                  # إذا لم يكن هناك قيمة سابقة أو كانت القيمة السابقة فارغة، ضع القيمة الجديدة (والتي قد تكون فارغة أيضاً)
                  archive[tournament_id][key] = value
                  print(f"  تحديث {key} بقيمة فارغة أو جديدة: {value.get('video') if isinstance(value, dict) else value}.")


        # تصحيح ترتيب الرتب بعد التحديث
        current_rank = 1
        ranked_keys = ["top1", "top2", "top3", "top4"]
        for key in ranked_keys:
             # التأكد من أن العنصر قاموس ويحتوي على مفتاح "video" بقيمة غير فارغة
             if key in archive[tournament_id] and isinstance(archive[tournament_id][key], dict) and archive[tournament_id][key].get("video"):
                  archive[tournament_id][key]["ranking"] = current_rank
                  print(f"  تعيين الترتيب {current_rank} لـ {key}: {archive[tournament_id][key].get('video')}") # طباعة تعيين الترتيب
                  current_rank += 1
             elif key in archive[tournament_id] and isinstance(archive[tournament_id][key], dict) and "ranking" in archive[tournament_id][key]:
                  # إذا كان العنصر فارغاً ولديه ترتيب من جولة سابقة، قم بإزالة الترتيب
                  del archive[tournament_id][key]["ranking"]
                  print(f"  إزالة الترتيب لـ {key} (عنصر فارغ).")
             elif key not in archive[tournament_id]:
                 # إذا لم يكن المفتاح موجوداً، يمكن إضافته كعنصر فارغ لضمان وجود جميع المفاتيح
                 archive[tournament_id][key] = {"video": "", "old_rating": None, "new_rating": None, "file_size": None}
                 print(f"  إضافة {key} كعنصر فارغ للأرشيف.")

    try:
        # عمل باكاب لملف الأرشيف عند إكمال المسابقة
        # يتم عمل باكاب بعد كل تحديث لضمان عدم فقدان البيانات
        print(f"عمل نسخة احتياطية للأرشيف...") # طباعة عمل باكاب
        create_backup(archive, is_archive=True) # إضافة باكاب هنا
        with open(archive_path, 'w') as f:
            json.dump(archive, f, indent=4)
        print("تم تحديث الأرشيف بنجاح.") # طباعة نجاح التحديث
    except Exception as e:
        print("خطأ في تحديث الأرشيف:", e) # طباعة خطأ التحديث


def load_tournament_archive():
    """Loads the tournament archive from JSON file."""
    archive_filename = "tournamentarchive.json"
    archive_path = os.path.join('utilities', archive_filename)
    try:
        with open(archive_path, 'r') as f:
            archive = json.load(f)
        print(f"تم تحميل ملف الأرشيف من {archive_path}.") # طباعة عند التحميل الناجح
        return archive
    except FileNotFoundError:
        print(f"ملف الأرشيف {archive_path} غير موجود.") # طباعة عند عدم وجود الملف
        return {}
    except Exception as e:
        print(f"خطأ في تحميل أرشيف المسابقات: {e}") # طباعة خطأ عام عند التحميل
        return {}


def get_tournament_weight(tournament_name):
    """استخراج وزن البطولة من اسمها"""
    import re
    # إزالة .json من النهاية
    name = tournament_name.replace('.json', '')
    
    # التحقق من وجود رقم في البداية
    match = re.match(r'^(\d+)\.', name)
    if match:
        return int(match.group(1))
    return 0  # إذا لم يبدأ برقم

def sort_tournaments_by_weight(tournament_archive, sort_type="recent"):
    """ترتيب البطولات حسب نوع الترتيب"""
    items = list(tournament_archive.items())
    
    if sort_type == "asc_weight":
        return sorted(items, key=lambda x: get_tournament_weight(x[0]))
    elif sort_type == "desc_weight":
        return sorted(items, key=lambda x: get_tournament_weight(x[0]), reverse=True)
    else:  # recent (default)
        return list(reversed(items))

def get_individual_videos(tournament_archive):
    """استخراج الفيديوهات بشكل فردي مع حساب أوزانها"""
    # قواعد حساب الوزن
    WEIGHT_RULES = {
        "top1": {"base_percent": 0.50, "bonus_percent": 0.10},
        "top2": {"base_percent": 0.30, "bonus_percent": 0.05},
        "top3": {"base_percent": 0.10, "bonus_percent": 0.00},
        "top4": {"base_percent": 0.10, "bonus_percent": 0.00}
    }
    
    video_weights = {}
    video_counts = {}  # عدد مرات الظهور
    
    for tournament_id, tournament_data in tournament_archive.items():
        base_weight = get_tournament_weight(tournament_id)
        
        # عدد العناصر المرتبة في هذه البطولة
        ranked_count = sum(1 for pos in ["top1", "top2", "top3", "top4"] 
                          if tournament_data.get(pos, {}).get("video"))
        
        # إذا كان عدد العناصر 2 (مباراة فردية)، قم بتعديل الأوزان
        if ranked_count == 2:
            current_rules = {
                "top1": 0.60, # 60% للفائز
                "top2": 0.40  # 40% للخاسر
            }
        else: # بطولة عادية
            current_rules = {
                "top1": WEIGHT_RULES["top1"]["base_percent"] + WEIGHT_RULES["top1"]["bonus_percent"],
                "top2": WEIGHT_RULES["top2"]["base_percent"] + WEIGHT_RULES["top2"]["bonus_percent"],
                "top3": WEIGHT_RULES["top3"]["base_percent"] + WEIGHT_RULES["top3"]["bonus_percent"],
                "top4": WEIGHT_RULES["top4"]["base_percent"] + WEIGHT_RULES["top4"]["bonus_percent"]
            }
        
        for position in ["top1", "top2", "top3", "top4"]:
            video_data = tournament_data.get(position, {})
            video_name = video_data.get("video", "")
            
            if video_name:  # إذا كان هناك فيديو في هذا المركز
                if video_name not in video_weights:
                    video_weights[video_name] = 0
                    video_counts[video_name] = 0
                
                # حساب الوزن باستخدام القواعد المحددة (سواء لـ 2 أو عادي)
                weight = base_weight * current_rules.get(position, 0)
                
                video_weights[video_name] += weight
                video_counts[video_name] += 1
    
    return video_weights, video_counts


# --- أضف هذه الدالة الجديدة في نهاية الملف ---

def filter_unplayed_matches(tournament_file):
    """
    يفحص ملف بطولة ويُرجع فقط المباريات التي لم تُلعب بعد.
    يستخدم نفس منطق مقارنة التقييمات مثل continue_tournament_web.
    """
    print(f"\n[FILTER] بدء فلترة المباريات غير الملعوبة لـ: {tournament_file}")
    
    # 1. تحميل البيانات الأساسية (مثل continue_tournament_web)
    pattern = r"^topcut_(.*)_(\d{4}).json$"
    m = re.match(pattern, tournament_file)
    if not m:
        return {'success': False, 'message': "تنسيق اسم ملف المسابقة غير صالح."}
    
    original_base = m.group(1)
    original_filename = f"{original_base}.json"

    try:
        with open(os.path.join('utilities', original_filename), 'r') as f:
            original_data = json.load(f)
        print(f"[FILTER] تم تحميل الملف الأصلي: {original_filename}")
    except Exception as e:
        return {'success': False, 'message': f"خطأ في تحميل الملف الأصلي: {e}"}

    try:
        with open(os.path.join('utilities', tournament_file), 'r') as f:
            tournament_matches = json.load(f)
        print(f"[FILTER] تم تحميل ملف المسابقة: {tournament_file}")
    except Exception as e:
        return {'success': False, 'message': f"خطأ في تحميل ملف المسابقة: {e}"}

    if not tournament_matches:
        return {'success': True, 'data': [], 'message': 'المسابقة فارغة بالفعل.'}

    # 2. منطق التحقق من التقييمات (منسوخ ومعدل من continue_tournament_web)
    first_unplayed_match_index = -1

    for match_index, match in enumerate(tournament_matches):
        videos = match.get("videos", [])
        old_ratings = match.get("rating", [])
        
        is_played = True
        for video_index in range(len(videos)):
            video = videos[video_index]
            if not video: continue

            old_rating = old_ratings[video_index]
            updated_rating = original_data.get(video, {}).get("rating")

            if updated_rating is None:
                return {'success': False, 'message': f"لم يتم العثور على الفيديو '{video}' في الملف الأصلي."}

            if updated_rating == old_rating:
                # وجدنا أول مباراة لم تكتمل
                is_played = False
                break
        
        if not is_played:
            first_unplayed_match_index = match_index
            print(f"[FILTER] تم العثور على أول مباراة غير ملعوبة في المؤشر: {first_unplayed_match_index}")
            break

    # 3. إرجاع النتائج
    if first_unplayed_match_index != -1:
        # إذا وجدنا مباريات غير ملعوبة، نرجعها هي وما بعدها
        remaining_matches = tournament_matches[first_unplayed_match_index:]
        return {'success': True, 'data': remaining_matches, 'message': f"تم العثور على {len(remaining_matches)} مباراة متبقية."}
    else:
        # إذا كانت كل المباريات قد لُعبت، نرجع قائمة فارغة
        print("[FILTER] كل المباريات قد لُعبت.")
        return {'success': True, 'data': [], 'message': 'كل المباريات في هذه الجولة قد اكتملت.'}
