# START: NEW FILE utilities/video_filter.py
import os
import json
from flask import session

# المسار إلى ملف تخزين الفيديوهات التي تم تخطيها
# سيتم إنشاؤه تلقائيًا في مجلد 'utilities'
SKIPPED_VIDEOS_FILE = os.path.join(os.path.dirname(__file__), 'skipped_videos.json')

def load_skipped_videos():
    """
    تقوم بتحميل قائمة أحجام الملفات للفيديوهات التي تم تخطيها.
    ترجع set للبحث السريع.
    """
    if not os.path.exists(SKIPPED_VIDEOS_FILE):
        return set()
    try:
        with open(SKIPPED_VIDEOS_FILE, 'r', encoding='utf-8') as f:
            # نتوقع أن الملف يحتوي على قائمة من أحجام الملفات (أرقام)
            data = json.load(f)
            return set(data)
    except (json.JSONDecodeError, TypeError):
        # إذا كان الملف فارغًا أو تالفًا، أو ليس قائمة
        return set()

def save_skipped_videos(skipped_set):
    """
    تقوم بحفظ قائمة أحجام الملفات المحدثة في ملف JSON.
    """
    try:
        with open(SKIPPED_VIDEOS_FILE, 'w', encoding='utf-8') as f:
            # نحول الـ set إلى list قبل الحفظ
            json.dump(list(skipped_set), f, indent=4)
    except Exception as e:
        print(f"Error saving skipped videos file: {e}")


def calculate_deletion_score(video_info):
    """
    تحسب "نقاط الحذف" لفيديو معين بناءً على القواعد المحددة.
    كلما زادت النقاط، كان الفيديو مرشحًا أكثر للحذف.
    """
    score = 0
    tags = video_info.get('tags', '').upper().split(',')
    rating = video_info.get('rating', 1000)
    times_shown = video_info.get('times_shown', 0)
    win_rate = video_info.get('win_rate', 0.5)

    # القاعدة 1: الأولوية القصوى لوسم "L"
    if 'L' in tags:
        score += 1000  # إضافة عدد كبير من النقاط لجعله في المقدمة دائمًا

    # القاعدة 2: التقييم الأقل من 973
    # لا يتم النظر في هذه القاعدة إذا كان التقييم أعلى ووسم L غير موجود
    if rating < 973:
        # كلما قل التقييم عن 973، زادت النقاط
        score += (973 - rating) * 2  # مضاعفة التأثير

    # القاعدة 3: عدد مرات الظهور (تؤثر فقط على الفيديوهات ذات التقييم المنخفض)
    if rating < 973 and times_shown > 1:
        # كلما زاد عدد مرات الظهور لفيديو سيء، زادت النقاط
        score += times_shown * 5

    # القاعدة 4: معدل الفوز المنخفض والخسارات (تأثير أقل)
    if win_rate < 0.4: # تأثير فقط إذا كان معدل الفوز منخفضًا جدًا
        score += (1 - win_rate) * 50 # فيديو بمعدل فوز 0% يحصل على 50 نقطة إضافية

    return score


def get_deletion_candidates(all_videos_data):
    """
    الدالة الرئيسية التي تقوم بفلترة وترتيب جميع الفيديوهات المرشحة للحذف.
    """
    # 1. تحميل قائمة أحجام الملفات التي تم تخطيها
    skipped_videos_sizes = load_skipped_videos()

    candidates = []
    for video_name, video_info in all_videos_data.items():
        # 2. تجاهل الفيديوهات التي تم تخطيها سابقًا
        if video_info.get('file_size') in skipped_videos_sizes:
            continue

        rating = video_info.get('rating', 1000)
        tags = video_info.get('tags', '').upper().split(',')

        # 3. تحديد ما إذا كان الفيديو مرشحًا أساسًا
        # الشرط: يجب أن يكون التقييم أقل من 973 أو يجب أن يحتوي على الوسم 'L'
        if rating < 973 or 'L' in tags:
            # 4. حساب نقاط الحذف للفيديو المرشح
            score = calculate_deletion_score(video_info)
            if score > 0: # نضيف فقط الفيديوهات التي لديها سبب للحذف
                # نستخدم قاموس لتسهيل الوصول للبيانات في الواجهة
                candidate_data = {
                    'filename': video_name,
                    'info': video_info,
                    'score': score
                }
                candidates.append(candidate_data)

    # 5. ترتيب القائمة النهائية: من الأعلى نقاطًا إلى الأقل
    candidates.sort(key=lambda x: x['score'], reverse=True)

    return candidates
# END: NEW FILE utilities/video_filter.py