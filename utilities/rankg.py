import json
import math

# -----------------------------
# 1. إعداد المسارات والثوابت
# -----------------------------
INPUT_PATH  = "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json"
OUTPUT_PATH = "sorted_videos.json"

# أوزان الاقتراح الأوّل (Linear Index)
w1, w2, w3, w4, w5 = 0.4, 0.2, 0.2, 0.1, 0.1

# ثوابت المتوسط البايزي (Bayesian Average)
m      = 10.0   # عدد المشاهدات المرجعي
alpha, beta = 0.05, 0.05  # وزن سلاسل الفوز والخسارة

# ثوابت الاقتراح الثالث (Uncertainty Boost)
gamma, delta, epsilon, zeta = 100.0, 0.5, 0.1, 0.1

# -----------------------------
# 2. تحميل بيانات الفيديوهات
# -----------------------------
with open(INPUT_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

videos = list(data.keys())
N = len(videos)

# استخراج القوائم اللازمة لحساب الـ min/max و المتوسط العام
ratings     = [ data[v]['rating']      for v in videos ]
win_rates   = [ data[v]['win_rate']    for v in videos ]
logs_shown  = [ math.log(data[v]['times_shown']+1) for v in videos ]
win_strs    = [ data[v]['win_streak']  for v in videos ]
loss_strs   = [ data[v]['loss_streak'] for v in videos ]

# القيم الحدّية للتطبيع
min_r, max_r = min(ratings),     max(ratings)
min_w, max_w = min(win_rates),   max(win_rates)
min_lg, max_lg = min(logs_shown), max(logs_shown)
min_ws, max_ws = min(win_strs),   max(win_strs)
min_ls, max_ls = min(loss_strs),  max(loss_strs)

# المتوسط العام للتقييمات (Bayesian C)
C = sum(ratings) / N

# -----------------------------
# 3. حساب الدرجات الثلاث
# -----------------------------
score1 = {}  # الاقتراح الأوّل
score2 = {}  # المتوسط البايزي
score3 = {}  # الاقتراح الثالث

for v in videos:
    info = data[v]
    R = info['rating']
    W = info['win_rate']
    v_i = info['times_shown']
    s = info['win_streak']
    l = info['loss_streak']
    lg = math.log(v_i + 1)

    # 3.1 الصيغة الخطية المركّبة (Normalization + Weighted Sum)
    def norm(x, mn, mx):
        return (x - mn) / (mx - mn) if mx > mn else 0.0

    Rn  = norm(R,    min_r,  max_r)
    Wn  = norm(W,    min_w,  max_w)
    Lgn = norm(lg,   min_lg, max_lg)
    Ssn = norm(s,    min_ws, max_ws)
    Lsn = norm(l,    min_ls, max_ls)

    score1[v] = (w1*Rn + w2*Wn + w3*Lgn + w4*Ssn - w5*Lsn)

    # 3.2 المتوسط البايزي مع سلاسل الفوز/الخسارة
    score2[v] = ( v_i/(v_i+m)*R + m/(v_i+m)*C ) + alpha*s - beta*l

    # 3.3 التعزيز بناءً على عدم اليقين + win_rate + سلاسل
    score3[v] = R + gamma*(R/math.sqrt(v_i+1)) + delta*W + epsilon*s - zeta*l

# -----------------------------
# 4. تحويل الدرجات إلى مراكز ترتيب
# -----------------------------
def compute_ranks(score_map):
    """يرجّح أعلى الدرجات في المركز 1 ثم 2 ..."""
    sorted_vs = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
    ranks = {}
    for idx, (v, _) in enumerate(sorted_vs, start=1):
        ranks[v] = idx
    return ranks

rank1 = compute_ranks(score1)
rank2 = compute_ranks(score2)
rank3 = compute_ranks(score3)

# -----------------------------
# 5. حساب متوسط الترتيب النهائي لكل فيديو
# -----------------------------
avg_rank = {}
for v in videos:
    avg_rank[v] = (rank1[v] + rank2[v] + rank3[v]) / 3.0

# -----------------------------
# 6. بناء القائمة النهائية وترتيبها
# -----------------------------
final_list = sorted(videos, key=lambda v: avg_rank[v])
sorted_data = { v: data[v] for v in final_list }

# -----------------------------
# 7. كتابة الملف الجديد
# -----------------------------
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(sorted_data, f, ensure_ascii=False, indent=4)

print(f"Done! تم حفظ الترتيب النهائي في: {OUTPUT_PATH}")
