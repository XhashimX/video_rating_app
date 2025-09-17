import json
import os
from collections import defaultdict
from utilities.data_manager import load_data # سنحتاج لتحميل البيانات الرئيسية

# مسار ملف names.json
NAMES_FILE_PATH = os.path.join(os.path.dirname(__file__), 'names.json')

# عرف ثابت لاسم الفيديوهات المجهولة
UNKNOWN_VIDEO_NAME = "Unknown" # يمكنك تغيير هذا الاسم كما تحب

def load_names_data():
    """Loads the names.json data."""
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
    return {} # Return empty dict if file doesn't exist

def save_names_data(data):
    """Saves the names.json data."""
    try:
        with open(NAMES_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"ERROR: Could not save {NAMES_FILE_PATH}: {e}")

def get_video_display_name(video_id, data_store):
    """
    Helper to get the display name for a video.
    Returns UNKNOWN_VIDEO_NAME if the video has no custom 'name' field.
    """
    video_info = data_store.get(video_id, {})
    # الأولوية للحقل 'name' المخصص والتأكد من أنه ليس فارغًا بعد إزالة المسافات البيضاء
    if video_info.get('name') and len(video_info['name'].strip()) > 0:
        return video_info['name'].strip()
    
    # إذا لم يكن هناك اسم مخصص، أعد الاسم الموحد للمجهول
    return UNKNOWN_VIDEO_NAME

def update_names_analysis(
    winner_id,
    loser_ids,
    video_participants, # كل المشاركين في المسابقة (أسماء الملفات الأصلية)
    main_data # بيانات الـ Elo الرئيسية
):
    """
    Updates the names.json analysis data based on a competition result.
    This function should be called AFTER Elo ratings are updated.
    """
    print(f"\n--- Updating names analysis ---") # DEBUG
    names_analysis = load_names_data()
    all_video_ids_in_competition = set(video_participants) # كل الفيديوهات التي ظهرت في هذه المسابقة

    # استخلاص الأسماء المعروضة (باستخدام get_video_display_name التي ستعيد 'Unknown' للمجهولين)
    winner_display_name = get_video_display_name(winner_id, main_data)
    loser_display_names = [get_video_display_name(l_id, main_data) for l_id in loser_ids]
    # جمع جميع الأسماء المعروضة الفريدة من كل المشاركين في المسابقة
    all_participants_display_names = {get_video_display_name(vid_id, main_data) for vid_id in all_video_ids_in_competition}


    # تأكد من وجود إدخالات لجميع الأسماء المعروضة في names_analysis
    for display_name in all_participants_display_names:
        names_analysis.setdefault(display_name, {
            'total_wins': 0,
            'total_losses': 0,
            'total_competitions': 0,
            'competitors_stats': {}, # {competitor_name: {wins: X, losses: Y, total: Z}}
            'most_fought_against': [], # (competitor_name, count)
            'most_defeated': [],      # (competitor_name, count)
            'most_lost_to': []        # (competitor_name, count)
        })

    # تحديث إحصائيات الفائز
    if winner_display_name:
        winner_entry = names_analysis[winner_display_name]
        winner_entry['total_wins'] += 1
        # يتم تحديث 'total_competitions' لاحقًا لكل مشارك

        # تحديث إحصائيات المنافسين للفائز
        for loser_display_name in loser_display_names:
            # تحديث جانب الفائز
            winner_entry['competitors_stats'].setdefault(loser_display_name, {'wins': 0, 'losses': 0, 'total': 0})
            winner_entry['competitors_stats'][loser_display_name]['wins'] += 1
            winner_entry['competitors_stats'][loser_display_name]['total'] += 1
            print(f"  {winner_display_name} won against {loser_display_name}.") # DEBUG

            # تحديث جانب الخاسر (فقط إذا كان الخاسر هو نفسه الفائز - لمنع تحديث نفس الشخص)
            # هذا الشرط مهم إذا كان هناك وضع قد يكون فيه الفائز والخاسر لهما نفس الاسم (لا ينطبق هنا، لكن كحماية)
            if winner_display_name != loser_display_name:
                loser_entry = names_analysis[loser_display_name]
                loser_entry['total_losses'] += 1
                loser_entry['competitors_stats'].setdefault(winner_display_name, {'wins': 0, 'losses': 0, 'total': 0})
                loser_entry['competitors_stats'][winner_display_name]['losses'] += 1
                loser_entry['competitors_stats'][winner_display_name]['total'] += 1
                print(f"  {loser_display_name} lost to {winner_display_name}.") # DEBUG
            else:
                 print(f"  Skipping loser update for {loser_display_name} as it's the same as winner.") # DEBUG


    # تحديث عدد المسابقات لجميع المشاركين في هذه الجولة
    # (هذا يضمن أن كل من الفائز والخاسرين (وغيرهم في حالات خاصة) يزيد عددهم)
    for participant_display_name in all_participants_display_names:
        names_analysis[participant_display_name]['total_competitions'] += 1
        print(f"  {participant_display_name} total competitions incremented.") # DEBUG


    # إعادة حساب most_fought_against, most_defeated, most_lost_to لجميع الأسماء بعد التحديثات
    print(f"  Recalculating derived stats for all names.") # DEBUG
    for name, stats in names_analysis.items():
        # Most fought against
        stats['most_fought_against'] = sorted(
            [(comp_name, comp_stats['total']) for comp_name, comp_stats in stats['competitors_stats'].items()],
            key=lambda x: x[1], reverse=True
        )[:5] # أعلى 5، يمكن التعديل

        # Most defeated
        stats['most_defeated'] = sorted(
            [(comp_name, comp_stats['wins']) for comp_name, comp_stats in stats['competitors_stats'].items() if comp_stats['wins'] > 0],
            key=lambda x: x[1], reverse=True
        )[:5]

        # Most lost to
        stats['most_lost_to'] = sorted(
            [(comp_name, comp_stats['losses']) for comp_name, comp_stats in stats['competitors_stats'].items() if comp_stats['losses'] > 0],
            key=lambda x: x[1], reverse=True
        )[:5]

    save_names_data(names_analysis)
    print(f"--- Names analysis updated and saved. ---") # DEBUG


def analyze_names_data():
    """
    Analyzes the names.json data and returns a structured output for display.
    Ensures all unique display names from main_data are included.
    Calculates 'total_rating', 'video_count', and 'average_rating'.
    """
    names_analysis = load_names_data()
    main_data = load_data() # تحميل بيانات Elo الرئيسية هنا

    # قاموس لتخزين النتائج النهائية
    results = {}

    # قاموس مؤقت لتخزين مجموع التقييمات وعدد الفيديوهات لكل اسم مخصص
    total_ratings_by_display_name = defaultdict(float)
    video_counts_by_display_name = defaultdict(int) # جديد: لتتبع عدد الفيديوهات لكل اسم

    # الخطوة الجديدة: تحديد جميع الأسماء المعروضة الفريدة من main_data أولاً
    all_display_names_from_main_data = set()
    for video_id, video_info in main_data.items():
        display_name = get_video_display_name(video_id, main_data)
        all_display_names_from_main_data.add(display_name)
        
        rating = video_info.get('rating', 1000.0)
        total_ratings_by_display_name[display_name] += rating
        video_counts_by_display_name[display_name] += 1 # جديد: زيادة العدد


    # ادمج الأسماء من names_analysis مع الأسماء الجديدة من main_data
    # وهذا يضمن أن جميع الأسماء موجودة، مع أولوية للإحصائيات الموجودة في names_analysis
    all_unique_display_names = all_display_names_from_main_data.union(set(names_analysis.keys()))


    for display_name in all_unique_display_names:
        # تهيئة الإحصائيات الافتراضية إذا كان الاسم جديدًا في names_analysis
        stats = names_analysis.get(display_name, {
            'total_wins': 0,
            'total_losses': 0,
            'total_competitions': 0,
            'competitors_stats': {},
            'most_fought_against': [],
            'most_defeated': [],
            'most_lost_to': []
        })

        # حساب عدد الفيديوهات ومتوسط التقييم لهذا الاسم
        current_video_count = video_counts_by_display_name.get(display_name, 0)
        current_total_rating = total_ratings_by_display_name.get(display_name, 0.0)
        current_average_rating = (current_total_rating / current_video_count) if current_video_count > 0 else 0.0


        results[display_name] = {
            'total_wins': stats['total_wins'],
            'total_losses': stats['total_losses'],
            'total_competitions': stats['total_competitions'],
            'win_rate': (stats['total_wins'] / stats['total_competitions']) if stats['total_competitions'] > 0 else 0.0,
            'competitors_detail': {},
            'most_fought_against': stats['most_fought_against'],
            'most_defeated': stats['most_defeated'],
            'most_lost_to': stats['most_lost_to'],
            'total_rating': current_total_rating, # التقييم الكلي
            'video_count': current_video_count,   # جديد: عدد الفيديوهات
            'average_rating': current_average_rating # جديد: متوسط التقييم
        }

        # Detailed competitor stats (فقط إذا كانت موجودة في names_analysis)
        for comp_name, comp_stats in stats['competitors_stats'].items():
            results[display_name]['competitors_detail'][comp_name] = {
                'wins': comp_stats['wins'],
                'losses': comp_stats['losses'],
                'total': comp_stats['total'],
                'win_rate_vs': (comp_stats['wins'] / comp_stats['total']) if comp_stats['total'] > 0 else 0.0
            }
    return results

def get_names_for_competition(competition_videos_data, main_data_store):
    """
    Checks if any video in the current competition has a custom 'name' field.
    Returns a list of tuples (video_id, display_name) for all participants.
    This function هو للتحقق من وجود أسماء مخصصة للمشاركين، ولكن ليس لإضافة "Unknown"
    في هذه القائمة، بل لإظهار ما إذا كان أي فيديو لديه اسم مخصص فعلي
    """
    participants_with_custom_names = []
    # competition_videos_data هي قائمة من tuples (name, rating, times_shown, tags)
    for video_id, _, _, _ in competition_videos_data:
        video_info = main_data_store.get(video_id, {})
        # نتحقق من وجود اسم مخصص غير فارغ
        if video_info.get('name') and len(video_info['name'].strip()) > 0:
            participants_with_custom_names.append((video_id, video_info['name'].strip()))
    return participants_with_custom_names