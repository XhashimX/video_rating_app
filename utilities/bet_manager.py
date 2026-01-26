
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

    # نحفظ الخصم الحالي كمرجع فقط، لكن التحدي سيعتمد على المركز لاحقاً
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
    التحقق مما إذا كان الرهان قد تحقق.
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

# START: MODIFIED SECTION - جعل اختيار الخصم ديناميكياً
def get_proposed_match(challenger_video):
    """
    تجهيز بيانات المنافسة (JSON) بين المتحدي وصاحب المركز المستهدف *حالياً*.
    """
    bets = load_bets()
    if challenger_video not in bets:
        return None
        
    bet = bets[challenger_video]
    target_rank = bet.get('target_rank')
    
    # تحميل البيانات الحالية لتحديد من يجلس في المركز المستهدف الآن
    data = load_data()
    sorted_videos = sorted(
        data.items(),
        key=lambda item: item[1].get('rating', 1000),
        reverse=True
    )
    
    # التأكد من أن الترتيب صالح
    if target_rank < 1 or target_rank > len(sorted_videos):
        # إذا كان الترتيب خارج النطاق، نعود لاستخدام الخصم المسجل قديماً كإجراء احتياطي
        defender = bet.get('defender_video')
    else:
        # جلب اسم الفيديو الذي يحتل المركز المستهدف حالياً
        # (target_rank - 1) لأن القائمة تبدأ من 0
        defender = sorted_videos[target_rank - 1][0]
    
    # التأكد من أن المتحدي لا يواجه نفسه (إذا وصل للمركز بالفعل)
    if defender == challenger_video:
        # إذا كان المتحدي هو صاحب المركز، نجعله يواجه المركز الذي قبله (الأصعب) أو بعده
        # هنا سنختار المركز الذي قبله (target_rank - 2) لزيادة التحدي، أو نلغي المباراة
        # للتبسيط، سنبقيها كما هي، أو يمكنك إرجاع None
        pass 

    # إنشاء هيكل المنافسة
    match_data = [{
        "videos": [challenger_video, defender],
        "rating": [0, 0], 
        "file_size": [0, 0],
        "mode": 1,
        "num_videos": 2,
        "ranking_type": "winner_only",
        "competition_type": "betting_match"
    }]
    
    return match_data
# END: MODIFIED SECTION

def remove_bet(challenger_video):
    """حذف الرهان"""
    bets = load_bets()
    if challenger_video in bets:
        del bets[challenger_video]
        save_bets(bets)
        return True
    return False


# أضف هذا في نهاية ملف utilities/bet_manager.py

def clear_bets_by_status(status_to_delete):
    """
    حذف جميع الرهانات التي تحمل حالة معينة.
    status_to_delete: 'active' أو 'completed' أو 'all'
    """
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