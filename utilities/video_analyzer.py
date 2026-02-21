
import json
import os
import math
import itertools
from collections import defaultdict
from utilities.data_manager import load_data

NAMES_FILE_PATH = os.path.join(os.path.dirname(__file__), 'names.json')

UNKNOWN_VIDEO_NAME = "Unknown"

def load_names_data():
    if os.path.exists(NAMES_FILE_PATH):
        try:
            with open(NAMES_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: Could not decode JSON from {NAMES_FILE_PATH}: {e}")
            return {}
        except Exception as e:
            print(f"ERROR: Could not load {NAMES_FILE_PATH}: {e}")
            return {}
    return {}

def save_names_data(data):
    try:
        with open(NAMES_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"ERROR: Could not save {NAMES_FILE_PATH}: {e}")

def get_video_display_name(video_id, data_store):
    video_info = data_store.get(video_id, {})
    if video_info.get('name') and len(video_info['name'].strip()) > 0:
        return video_info['name'].strip()
    return UNKNOWN_VIDEO_NAME

def update_names_analysis(winner_id, loser_ids, video_participants, main_data):
    print(f"\n--- Updating names analysis ---")
    names_analysis = load_names_data()
    all_video_ids_in_competition = set(video_participants)

    winner_display_name = get_video_display_name(winner_id, main_data)
    loser_display_names = [get_video_display_name(l_id, main_data) for l_id in loser_ids]
    all_participants_display_names = {get_video_display_name(vid_id, main_data) for vid_id in all_video_ids_in_competition}

    for display_name in all_participants_display_names:
        names_analysis.setdefault(display_name, {
            'total_wins': 0,
            'total_losses': 0,
            'total_competitions': 0,
            'competitors_stats': {},
            'most_fought_against': [],
            'most_defeated': [],
            'most_lost_to': []
        })

    if winner_display_name:
        winner_entry = names_analysis[winner_display_name]
        winner_entry['total_wins'] += 1

        for loser_display_name in loser_display_names:
            winner_entry['competitors_stats'].setdefault(loser_display_name, {'wins': 0, 'losses': 0, 'total': 0})
            winner_entry['competitors_stats'][loser_display_name]['wins'] += 1
            winner_entry['competitors_stats'][loser_display_name]['total'] += 1
            print(f"  {winner_display_name} won against {loser_display_name}.")

            if winner_display_name != loser_display_name:
                loser_entry = names_analysis[loser_display_name]
                loser_entry['total_losses'] += 1
                loser_entry['competitors_stats'].setdefault(winner_display_name, {'wins': 0, 'losses': 0, 'total': 0})
                loser_entry['competitors_stats'][winner_display_name]['losses'] += 1
                loser_entry['competitors_stats'][winner_display_name]['total'] += 1
                print(f"  {loser_display_name} lost to {winner_display_name}.")
            else:
                 print(f"  Skipping loser update for {loser_display_name} as it's the same as winner.")

    for participant_display_name in all_participants_display_names:
        names_analysis[participant_display_name]['total_competitions'] += 1
        print(f"  {participant_display_name} total competitions incremented.")

    print(f"  Recalculating derived stats for all names.")
    for name, stats in names_analysis.items():
        stats['most_fought_against'] = sorted(
            [(comp_name, comp_stats['total']) for comp_name, comp_stats in stats['competitors_stats'].items()],
            key=lambda x: x[1], reverse=True
        )[:5]

        stats['most_defeated'] = sorted(
            [(comp_name, comp_stats['wins']) for comp_name, comp_stats in stats['competitors_stats'].items() if comp_stats['wins'] > 0],
            key=lambda x: x[1], reverse=True
        )[:5]

        stats['most_lost_to'] = sorted(
            [(comp_name, comp_stats['losses']) for comp_name, comp_stats in stats['competitors_stats'].items() if comp_stats['losses'] > 0],
            key=lambda x: x[1], reverse=True
        )[:5]

    save_names_data(names_analysis)
    print(f"--- Names analysis updated and saved. ---")

def calculate_rival_pairs(stats_results):
    """
    تحدد الأزواج المتنافسة بناءً على تقارب النقاط وتاريخ المواجهات.
    تتجاهل الأسماء التي لديها أقل من 10 فيديوهات.
    """
    # 1. تصفية الأسماء المؤهلة (أكثر من 10 فيديوهات)
    qualified_names = [
        name for name, data in stats_results.items() 
        if data.get('video_count', 0) >= 10
    ]
    
    pairs = []
    
    # استخدام itertools لإنشاء كل الاحتمالات الممكنة للأزواج (A vs B, A vs C...)
    for name1, name2 in itertools.combinations(qualified_names, 2):
        data1 = stats_results[name1]
        data2 = stats_results[name2]
        
        # --- العامل الأول: فرق النقاط الذكية ---
        score1 = data1.get('smart_score', 0)
        score2 = data2.get('smart_score', 0)
        score_gap = abs(score1 - score2)
        
        # --- العامل الثاني: تاريخ المواجهات (الاحتدام) ---
        # نبحث في سجل name1 لنرى إذا واجه name2
        details = data1.get('competitors_detail', {}).get(name2)
        
        history_bonus = 0
        match_details_str = "لا توجد مواجهات مباشرة"
        
        if details:
            total_battles = details['total']
            wins1 = details['wins']
            # حساب نسبة الفوز (من منظور name1)
            win_rate = wins1 / total_battles
            
            # حساب "شدة المنافسة" (Intensity)
            # الرقم 1 يعني منافسة كاملة (50% فوز لكل طرف)
            # الرقم 0 يعني هيمنة طرف واحد (100% فوز لطرف)
            intensity = 1.0 - (abs(win_rate - 0.5) * 2)
            
            # المكافأة: كل معركة محتدمة تقلل الفجوة بينهما بمقدار 5 نقاط
            # هذا يجعل النظام يقربهم لبعضهم أكثر من مجرد تقييمهم
            history_bonus = total_battles * intensity * 5
            
            match_details_str = f"{total_battles} مواجهة (نسبة الفوز {win_rate*100:.0f}%)"
        
        # --- المؤشر النهائي (كلما قل كان التنافس أقوى وأقرب) ---
        rivalry_index = score_gap - history_bonus
        
        # نقبل الزوج فقط إذا كان المؤشر منطقياً (مثلاً أقل من حد معين)
        # أو نأخذ أفضل النتائج لاحقاً. هنا سنخزن كل النتائج ونرتبها.
        
        # سبب الاختيار (النص التوضيحي)
        reason_parts = []
        reason_parts.append(f"تقارب في النقاط (الفرق {score_gap:.1f})")
        if history_bonus > 0:
            reason_parts.append(f"تاريخ تنافسي قوي: {match_details_str}")
        elif details:
            reason_parts.append(f"يوجد تاريخ مواجهات: {match_details_str}")
        
        pairs.append({
            'name1': name1,
            'name2': name2,
            'score1': score1,
            'score2': score2,
            'rivalry_index': rivalry_index, # للترتيب
            'reason': " + ".join(reason_parts)
        })

    # ترتيب الأزواج حسب المؤشر (الأقل هو الأقرب والأشرس)
    sorted_pairs = sorted(pairs, key=lambda x: x['rivalry_index'])
    
    # إرجاع أفضل 30 زوج مثلاً
    return sorted_pairs[:30]


def analyze_names_data():
    """
    Analyzes names data, calculates Smart Score, and finds Rival Pairs.
    Returns a DICTIONARY with two main keys: 'stats' and 'rival_pairs'.
    """
    names_analysis = load_names_data()
    main_data = load_data()

    results = {}

    total_ratings_by_display_name = defaultdict(float)
    video_counts_by_display_name = defaultdict(int)

    all_display_names_from_main_data = set()
    for video_id, video_info in main_data.items():
        display_name = get_video_display_name(video_id, main_data)
        all_display_names_from_main_data.add(display_name)
        
        rating = video_info.get('rating', 1000.0)
        total_ratings_by_display_name[display_name] += rating
        video_counts_by_display_name[display_name] += 1

    all_unique_display_names = all_display_names_from_main_data.union(set(names_analysis.keys()))

    GLOBAL_MEAN = 1100.0
    MIN_VIDEOS_FOR_TRUST = 5.0

    for display_name in all_unique_display_names:
        stats = names_analysis.get(display_name, {
            'total_wins': 0,
            'total_losses': 0,
            'total_competitions': 0,
            'competitors_stats': {},
            'most_fought_against': [],
            'most_defeated': [],
            'most_lost_to': []
        })

        current_video_count = video_counts_by_display_name.get(display_name, 0)
        current_total_rating = total_ratings_by_display_name.get(display_name, 0.0)
        current_average_rating = (current_total_rating / current_video_count) if current_video_count > 0 else 0.0
        
        total_competitions = stats['total_competitions']
        current_win_rate = (stats['total_wins'] / total_competitions) if total_competitions > 0 else 0.0

        v = current_video_count
        R = current_average_rating
        bayesian_rating = ((v * R) + (MIN_VIDEOS_FOR_TRUST * GLOBAL_MEAN)) / (v + MIN_VIDEOS_FOR_TRUST)

        activity_bonus = 100 * math.log10(total_competitions + 1)
        win_rate_bonus = (current_win_rate - 0.5) * 100
        smart_score = bayesian_rating + activity_bonus + win_rate_bonus

        results[display_name] = {
            'total_wins': stats['total_wins'],
            'total_losses': stats['total_losses'],
            'total_competitions': total_competitions,
            'win_rate': current_win_rate,
            'competitors_detail': {}, # Important for pairing logic
            'most_fought_against': stats['most_fought_against'],
            'most_defeated': stats['most_defeated'],
            'most_lost_to': stats['most_lost_to'],
            'total_rating': current_total_rating,
            'video_count': current_video_count,
            'average_rating': current_average_rating,
            'smart_score': smart_score
        }

        # نقل تفاصيل المنافسين (مهم جداً لحساب الأزواج)
        for comp_name, comp_stats in stats['competitors_stats'].items():
            results[display_name]['competitors_detail'][comp_name] = {
                'wins': comp_stats['wins'],
                'losses': comp_stats['losses'],
                'total': comp_stats['total'],
                'win_rate_vs': (comp_stats['wins'] / comp_stats['total']) if comp_stats['total'] > 0 else 0.0
            }
            
    # --- الجديد: حساب الأزواج المتنافسة ---
    rival_pairs = calculate_rival_pairs(results)

    # إرجاع هيكل بيانات يحتوي على الإحصائيات والأزواج
    return {
        'stats': results,
        'rival_pairs': rival_pairs
    }

def get_names_for_competition(competition_videos_data, main_data_store):
    participants_with_custom_names = []
    for video_id, _, _, _ in competition_videos_data:
        video_info = main_data_store.get(video_id, {})
        if video_info.get('name') and len(video_info['name'].strip()) > 0:
            participants_with_custom_names.append((video_id, video_info['name'].strip()))
    return participants_with_custom_names

# --- ADD THIS TO THE END OF utilities/video_analyzer.py ---

def find_lone_wolves():
    """
    تكتشف الفيديوهات التي تعتبر 'ذئاب وحيدة'.
    الشرط: الاسم لديه 10 فيديوهات على الأقل.
    الغالبية العظمى (90%) تقييمها منخفض (حول 1000)، بينما القلة (10%) تقييمها مرتفع جداً (فارق كبير).
    """
    main_data = load_data()
    
    # 1. تجميع الفيديوهات حسب الاسم
    videos_by_name = defaultdict(list)
    for vid, info in main_data.items():
        name = info.get('name', '').strip()
        if name: # تجاهل الفيديوهات بدون اسم
            videos_by_name[name].append((vid, info))
            
    lone_wolves_list = []
    
    # إعدادات الحساسية (يمكنك تعديلها)
    MIN_VIDEOS = 10         # الحد الأدنى للفيديوهات
    WEAK_PERCENTAGE = 0.90  # نسبة الفيديوهات الضعيفة
    WEAK_AVG_THRESHOLD = 1300 # السقف الأعلى لمتوسط الفيديوهات الضعيفة (يجب أن يكونوا ضعافاً)
    STRONG_THRESHOLD = 2000   # الحد الأدنى لكي يعتبر الفيديو قوياً (الذئب)
    
    for name, videos in videos_by_name.items():
        total_count = len(videos)
        if total_count < MIN_VIDEOS:
            continue
            
        # ترتيب الفيديوهات تصاعدياً حسب التقييم (من الأضعف للأقوى)
        sorted_videos = sorted(videos, key=lambda x: x[1].get('rating', 1000))
        
        # تقسيم القائمة
        split_index = int(total_count * WEAK_PERCENTAGE)
        
        # نأخذ الشريحة الضعيفة (أول 90%)
        weak_videos = sorted_videos[:split_index]
        # نأخذ الشريحة القوية المحتملة (آخر 10%)
        potential_wolves = sorted_videos[split_index:]
        
        if not weak_videos or not potential_wolves:
            continue
            
        # حساب متوسط الضعفاء
        weak_sum = sum(v[1].get('rating', 1000) for v in weak_videos)
        weak_avg = weak_sum / len(weak_videos)
        
        # الشرط الجوهري: هل متوسط البقية منخفض؟
        if weak_avg < WEAK_AVG_THRESHOLD:
            # الآن نفحص المرشحين الأقوياء
            for vid_name, info in potential_wolves:
                rating = info.get('rating', 1000)
                
                # الشرط الثاني: هل هذا الفيديو قوي جداً؟
                if rating > STRONG_THRESHOLD:
                    # تم العثور على ذئب وحيد!
                    lone_wolves_list.append({
                        'video_name': vid_name,
                        'owner_name': name,
                        'rating': rating,
                        'weak_avg': weak_avg, # للاطلاع المقارن
                        'file_size': info.get('file_size', 0),
                        'tags': info.get('tags', '')
                    })
    
    # ترتيب النتائج حسب التقييم (الأقوى أولاً)
    return sorted(lone_wolves_list, key=lambda x: x['rating'], reverse=True)