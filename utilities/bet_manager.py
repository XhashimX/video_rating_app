import os
import json
from .data_manager import load_data

BETS_FILE = os.path.join('utilities', 'bets.json')

def load_bets():
    """تحميل الرهانات النشطة"""
    if not os.path.exists(BETS_FILE):
        return {}
    try:
        with open(BETS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_bets(bets):
    """حفظ الرهانات"""
    try:
        with open(BETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bets, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving bets: {e}")
        return False

def add_bet(challenger_video, target_rank):
    """
    إضافة رهان جديد.
    """
    bets = load_bets()
    data = load_data()
    
    sorted_videos = sorted(
        data.items(),
        key=lambda item: item[1].get('rating', 1000),
        reverse=True
    )
    
    if target_rank < 1 or target_rank > len(sorted_videos):
        return False, "الترتيب المستهدف غير صالح."

    # نحفظ الخصم الحالي كمرجع فقط
    defender_video = sorted_videos[target_rank - 1][0]
    
    if challenger_video == defender_video:
        return False, "الفيديو بالفعل في هذا المركز!"

    bets[challenger_video] = {
        'target_rank': target_rank,
        'defender_video': defender_video, 
        'status': 'active',
        'timestamp': None
    }
    
    save_bets(bets)
    return True, f"تم وضع الرهان: {challenger_video} للوصول للمركز {target_rank}"

def check_bet_status(challenger_video, current_data=None):
    """
    التحقق مما إذا كان الرهان قد تحقق (بناءً على الترتيب العام).
    """
    bets = load_bets()
    if challenger_video not in bets:
        return None

    bet = bets[challenger_video]
    if bet['status'] != 'active':
        return bet

    if current_data is None:
        current_data = load_data()

    sorted_videos = sorted(
        current_data.items(),
        key=lambda item: item[1].get('rating', 1000),
        reverse=True
    )
    
    current_rank = -1
    for rank, (v_name, _) in enumerate(sorted_videos, start=1):
        if v_name == challenger_video:
            current_rank = rank
            break
            
    target = bet['target_rank']
    if current_rank != -1 and current_rank <= target:
        bet['status'] = 'completed'
        save_bets(bets)
    
    return bet


# في ملف utilities/bet_manager.py

def get_proposed_match(challenger_video):
    """
    تجهيز بيانات المنافسة وتحديث الخصم في ملف الرهانات ليطابق الواقع الحالي.
    """
    bets = load_bets()
    if challenger_video not in bets:
        return None
        
    bet = bets[challenger_video]
    target_rank = bet.get('target_rank')
    
    # تحميل البيانات لمعرفة من يجلس في المركز حالياً
    data = load_data()
    sorted_videos = sorted(
        data.items(),
        key=lambda item: item[1].get('rating', 1000),
        reverse=True
    )
    
    # تحديد الخصم الحالي
    current_defender = None
    if target_rank < 1 or target_rank > len(sorted_videos):
        # في حال وجود خطأ في الترتيب، نستخدم الخصم القديم
        current_defender = bet.get('defender_video')
    else:
        # جلب اسم الفيديو الذي يحتل المركز المستهدف حالياً
        current_defender = sorted_videos[target_rank - 1][0]
    
    # --- التعديل الجوهري: تحديث ملف الرهانات الآن ---
    # إذا كان الخصم الحالي مختلفاً عن المسجل، نقوم بتحديث السجل
    if current_defender != bet.get('defender_video'):
        bets[challenger_video]['defender_video'] = current_defender
        save_bets(bets) # حفظ التغيير فوراً لضمان التطابق
    # -----------------------------------------------

    # إنشاء هيكل المنافسة
    match_data = [{
        "videos": [challenger_video, current_defender],
        "rating": [0, 0], 
        "file_size": [0, 0],
        "mode": 1,
        "num_videos": 2,
        "ranking_type": "winner_only",
        "competition_type": "betting_match"
    }]
    
    return match_data


def remove_bet(challenger_video):
    """حذف الرهان"""
    bets = load_bets()
    if challenger_video in bets:
        del bets[challenger_video]
        save_bets(bets)
        return True
    return False

def clear_bets_by_status(status_to_delete):
    """حذف الرهانات حسب الحالة"""
    bets = load_bets()
    keys_to_delete = []
    
    for video, info in bets.items():
        if status_to_delete == 'all':
            keys_to_delete.append(video)
        elif info.get('status') == status_to_delete:
            keys_to_delete.append(video)
            
    for key in keys_to_delete:
        del bets[key]
        
    if keys_to_delete:
        save_bets(bets)
        return True, len(keys_to_delete)
    return False, 0

# في ملف utilities/bet_manager.py

def process_bet_match_completion(videos_in_match):
    """
    إنهاء الرهان إذا كان المتحدي والخصم المسجل موجودين في المباراة.
    """
    if not videos_in_match:
        return

    bets = load_bets()
    updated = False
    
    # نحول القائمة إلى set للبحث السريع
    videos_set = set(videos_in_match)
    
    for challenger, bet_info in bets.items():
        # نفحص فقط الرهانات النشطة
        if bet_info.get('status') == 'active':
            # هل المتحدي موجود في هذه المباراة؟
            if challenger in videos_set:
                # هل الخصم المسجل (الذي قمنا بتحديثه للتو) موجود أيضاً؟
                defender = bet_info.get('defender_video')
                
                if defender in videos_set:
                    # تطابق كامل -> إنهاء الرهان
                    bets[challenger]['status'] = 'completed'
                    bets[challenger]['completion_reason'] = 'match_played'
                    updated = True
                
    if updated:
        save_bets(bets)
    """
    تفحص المباراة الحالية وتنهي الرهان إذا:
    1. واجه المتحدي الخصم المسجل باسمه.
    2. أو واجه المتحدي صاحب المركز المستهدف حالياً (في حال تغيرت المراكز).
    """
    if not videos_in_match:
        return

    bets = load_bets()
    data = load_data() 
    updated = False
    
    videos_set = set(videos_in_match)
    
    # خريطة الترتيب الحالية
    sorted_videos = sorted(
        data.items(),
        key=lambda item: item[1].get('rating', 1000),
        reverse=True
    )
    rank_map = {name: i+1 for i, (name, _) in enumerate(sorted_videos)}

    for challenger, bet_info in bets.items():
        if bet_info.get('status') == 'active' and challenger in videos_set:
            
            # تحديد اسم الخصم
            opponent_name = None
            for vid in videos_in_match:
                if vid != challenger:
                    opponent_name = vid
                    break
            
            if opponent_name:
                # الشرط 1: الخصم الأصلي
                is_original_defender = (opponent_name == bet_info.get('defender_video'))
                
                # الشرط 2: صاحب المركز المستهدف حالياً
                target_rank = bet_info.get('target_rank')
                current_opponent_rank = rank_map.get(opponent_name)
                is_rank_target = (current_opponent_rank == target_rank)

                if is_original_defender or is_rank_target:
                    bets[challenger]['status'] = 'completed'
                    bets[challenger]['completion_reason'] = 'match_played'
                    updated = True
                
    if updated:
        save_bets(bets)