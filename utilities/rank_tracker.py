# START OF FILE utilities/rank_tracker.py
import os
import json
from datetime import datetime
from .data_manager import load_data

HISTORY_FILE = os.path.join('utilities', 'rank_history.json')

def save_rank_snapshot(data=None):
    """
    يقوم بحفظ لقطة (Snapshot) للترتيب الحالي لجميع الفيديوهات.
    يستخدم هذا المرجع لمقارنة الترتيب لاحقاً.
    """
    if data is None:
        data = load_data()
    
    # تحويل البيانات إلى قائمة مرتبة حسب التقييم (الأعلى أولاً)
    sorted_videos = sorted(
        data.items(),
        key=lambda item: item[1].get('rating', 1000),
        reverse=True
    )
    
    # إنشاء قاموس يربط اسم الفيديو بترتيبه (1, 2, 3...)
    # مثال: {'video1.mp4': 1, 'video2.mp4': 2}
    snapshot = {}
    for rank, (video_name, _) in enumerate(sorted_videos, start=1):
        snapshot[video_name] = rank
        
    history_data = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'ranks': snapshot
    }
    
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=4)
        print(f"Rank snapshot saved at {history_data['timestamp']}")
        return True
    except Exception as e:
        print(f"Error saving rank snapshot: {e}")
        return False

def get_rank_changes(current_data):
    """
    تقارن الترتيب الحالي مع آخر لقطة محفوظة.
    تُرجع قاموساً يحتوي على التغيير في المراكز لكل فيديو.
    """
    # 1. حساب الترتيب الحالي اللحظي
    sorted_current = sorted(
        current_data.items(),
        key=lambda item: item[1].get('rating', 1000),
        reverse=True
    )
    
    current_ranks = {}
    for rank, (video_name, _) in enumerate(sorted_current, start=1):
        current_ranks[video_name] = rank

    # 2. تحميل الترتيب السابق من الملف
    previous_ranks = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                previous_ranks = history.get('ranks', {})
        except Exception:
            print("Could not load rank history.")

    # 3. حساب الفرق (Delta)
    # القيمة الموجبة تعني صعود (تحسن)، والسالبة تعني هبوط (تراجع)
    # ملاحظة: في الترتيب، الرقم الأقل هو الأفضل (المركز 1 أفضل من 5)
    # المعادلة: الترتيب_السابق - الترتيب_الحالي
    # مثال: كان 5 وأصبح 2 -> 5 - 2 = 3 (صعد 3 مراكز)
    changes = {}
    for video_name, current_rank in current_ranks.items():
        if video_name in previous_ranks:
            prev_rank = previous_ranks[video_name]
            change = prev_rank - current_rank
            changes[video_name] = {
                'change': change,      # الرقم (موجب أو سالب)
                'prev_rank': prev_rank, # المركز السابق
                'current_rank': current_rank # المركز الحالي
            }
        else:
            # فيديو جديد لم يكن موجوداً سابقاً
            changes[video_name] = {
                'change': 'new',
                'prev_rank': '-',
                'current_rank': current_rank
            }
            
    return changes, current_ranks

# END OF FILE