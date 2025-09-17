import json
import math
import os
from collections import OrderedDict # للحفاظ على ترتيب الإدخال عند الكتابة لـ JSON (اختياري لـ Python 3.7+)

# --- تعريف المسارات ---
BASE_PATH = "C:/Users/Stark/Download/myhome/video_rating_app/utilities/"
INPUT_FILENAME = "elo_videos_A1000 elo tik.json"
OUTPUT_FILENAME = "elo_videos_A1000_smart_ranked.json"

INPUT_FILE_PATH = os.path.join(BASE_PATH, INPUT_FILENAME)
OUTPUT_FILE_PATH = os.path.join(BASE_PATH, OUTPUT_FILENAME)

# --- تعريف الأوزان والثوابت (يمكنك تعديل هذه القيم) ---

# === الطريقة الأولى: Weighted Win Rate with Confidence ===
W1_RATING = 1.0
W1_WIN_RATE_BASE = 150  # لزيادة تأثير معدل الفوز
C1_1 = math.e  # ثابت للوغاريتم (لتجنب log(0) أو log(1) إذا كان times_shown=0)
W1_WIN_STREAK = 15
W1_LOSS_STREAK = 20 # العقوبة أكبر قليلاً

# === الطريقة الثانية: Relative Performance Adjustment ===
# W2_RATING_BASE_CONTRIBUTION = 0.7 # التقييم يبدأ بـ 70% من قيمته
# W2_RATING_CONFIDENCE_CONTRIBUTION = 0.3 # ويزداد مع الثقة
W2_PERFORMANCE_FACTOR_WEIGHT = 200 # وزن لعامل الأداء (win_rate - 0.5)
W2_CONFIDENCE_PERFORMANCE_WEIGHT = 1.2
W2_WIN_STREAK = 12
W2_LOSS_STREAK = 18

# === الطريقة الثالثة: Promising Videos Boost (تعديل على الطريقة الأولى) ===
# تستخدم نفس أوزان W1_RATING, W1_WIN_RATE_BASE, C1_1, W1_WIN_STREAK, W1_LOSS_STREAK
M3_THRESHOLD_LOW_SHOWINGS = 5
M3_THRESHOLD_HIGH_WIN_RATE_EARLY = 0.80
M3_BONUS_PROMISING = 75 # مكافأة كبيرة نسبياً
M3_THRESHOLD_LOW_WIN_RATE_EARLY = 0.20
M3_PENALTY_STRUGGLING = 60
M3_PENALTY_UNSEEN = 30 # عقوبة بسيطة لغير المعروضة

# --- دوال حساب النقاط الذكية ---

def calculate_smart_score_method1(video_data):
    rating = video_data.get('rating', 1000)
    win_rate = video_data.get('win_rate', 0)
    times_shown = video_data.get('times_shown', 0)
    win_streak = video_data.get('win_streak', 0)
    loss_streak = video_data.get('loss_streak', 0)

    # استخدام log(times_shown + C1_1) لتجنب مشاكل log(0) أو log(1) = 0
    # إذا كان times_shown = 0, log(C1_1) = log(e) = 1
    # إذا كان times_shown = 1, log(1+e)
    log_times_shown_factor = math.log(times_shown + C1_1) if times_shown >= 0 else 0
    
    score = (rating * W1_RATING) + \
            (win_rate * W1_WIN_RATE_BASE * log_times_shown_factor) + \
            (win_streak * W1_WIN_STREAK) - \
            (loss_streak * W1_LOSS_STREAK)
    return score

def calculate_smart_score_method2(video_data):
    rating = video_data.get('rating', 1000)
    win_rate = video_data.get('win_rate', 0)
    times_shown = video_data.get('times_shown', 0)
    win_streak = video_data.get('win_streak', 0)
    loss_streak = video_data.get('loss_streak', 0)

    confidence = 1 - (1 / (times_shown + 1)) # يقترب من 1 كلما زاد times_shown
    
    performance_factor_val = (win_rate - 0.5) * W2_PERFORMANCE_FACTOR_WEIGHT
    
    # تعديل التقييم بناءً على الثقة
    # يبدأ التقييم بـ 70% من قيمته ويزداد تأثيره الكامل (100%) مع زيادة الثقة
    adjusted_rating = rating * (0.7 + 0.3 * confidence)

    score = adjusted_rating + \
            (performance_factor_val * W2_CONFIDENCE_PERFORMANCE_WEIGHT * confidence) + \
            (win_streak * W2_WIN_STREAK) - \
            (loss_streak * W2_LOSS_STREAK)
    return score

def calculate_smart_score_method3(video_data):
    # تبدأ بنفس الطريقة الأولى
    score = calculate_smart_score_method1(video_data) # إعادة استخدام منطق الطريقة الأولى

    times_shown = video_data.get('times_shown', 0)
    win_rate = video_data.get('win_rate', 0)

    if times_shown == 0:
        score -= M3_PENALTY_UNSEEN
    elif 0 < times_shown < M3_THRESHOLD_LOW_SHOWINGS:
        factor = (M3_THRESHOLD_LOW_SHOWINGS - times_shown) # المكافأة/العقوبة أكبر كلما كان الظهور أقل
        if win_rate > M3_THRESHOLD_HIGH_WIN_RATE_EARLY:
            score += M3_BONUS_PROMISING * factor
        elif win_rate < M3_THRESHOLD_LOW_WIN_RATE_EARLY:
            score -= M3_PENALTY_STRUGGLING * factor
    return score

# --- البرنامج الرئيسي ---
def main():
    try:
        with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
            videos_data = json.load(f)
    except FileNotFoundError:
        print(f"خطأ: لم يتم العثور على الملف: {INPUT_FILE_PATH}")
        return
    except json.JSONDecodeError:
        print(f"خطأ: الملف {INPUT_FILE_PATH} ليس ملف JSON صالحًا.")
        return

    processed_videos = []

    # 1. حساب النقاط لكل فيديو وإضافتها
    for filename, data in videos_data.items():
        # ضمان وجود القيم الافتراضية إذا كانت مفقودة
        data.setdefault('rating', 1000)
        data.setdefault('win_rate', 0.0)
        data.setdefault('times_shown', 0)
        data.setdefault('win_streak', 0)
        data.setdefault('loss_streak', 0)
        data.setdefault('total_wins', 0)
        data.setdefault('total_losses', 0)
        
        data['smart_score_m1'] = calculate_smart_score_method1(data)
        data['smart_score_m2'] = calculate_smart_score_method2(data)
        data['smart_score_m3'] = calculate_smart_score_method3(data)
        processed_videos.append({'filename': filename, **data}) # نحتفظ باسم الملف مع البيانات

    # 2. تحديد الترتيب لكل طريقة
    # الترتيب تنازلي (الأعلى هو الأفضل)، لذا rank 1 هو الأعلى نقاطاً
    
    # الطريقة الأولى
    processed_videos.sort(key=lambda x: x['smart_score_m1'], reverse=True)
    for i, video in enumerate(processed_videos):
        video['rank_m1'] = i + 1

    # الطريقة الثانية
    processed_videos.sort(key=lambda x: x['smart_score_m2'], reverse=True)
    for i, video in enumerate(processed_videos):
        video['rank_m2'] = i + 1

    # الطريقة الثالثة
    processed_videos.sort(key=lambda x: x['smart_score_m3'], reverse=True)
    for i, video in enumerate(processed_videos):
        video['rank_m3'] = i + 1
        
    # 3. حساب متوسط الترتيب وإضافته
    for video in processed_videos:
        video['average_rank'] = (video['rank_m1'] + video['rank_m2'] + video['rank_m3']) / 3.0

    # 4. الترتيب النهائي بناءً على متوسط الترتيب (تصاعدي، الأقل هو الأفضل)
    processed_videos.sort(key=lambda x: x['average_rank'])

    # 5. بناء قاموس الإخراج بالترتيب الجديد
    # OrderedDict يحافظ على ترتيب الإدخال، وهو مفيد هنا للحفاظ على الترتيب بعد الفرز
    # في Python 3.7+، القواميس العادية تحفظ ترتيب الإدخال، لكن OrderedDict أكثر وضوحًا للنية.
    final_ranked_data = OrderedDict()
    for video in processed_videos:
        filename = video.pop('filename') # استخراج اسم الملف مرة أخرى
        final_ranked_data[filename] = video

    # 6. كتابة الملف الجديد
    try:
        with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_ranked_data, f, ensure_ascii=False, indent=4)
        print(f"تم إنشاء الملف المرتب بنجاح: {OUTPUT_FILE_PATH}")
    except IOError:
        print(f"خطأ: لم يتمكن من كتابة الملف: {OUTPUT_FILE_PATH}")

if __name__ == "__main__":
    main()
