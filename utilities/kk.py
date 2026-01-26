import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import json
import os
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, accuracy_score

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
ELO_FILE_PATH = os.path.join(BASE_DIR, "elo_videos_A1000 elo tik.json")
PROCESSED_FILE_PATH = os.path.join(BASE_DIR, "processed_videos.json")

CREATOR_BONUSES = {
    "hajar0220": 3428.30, "ibu2b": 1584.00, "rahma_ghorbel7": 1115.05,
    "camvred1": 843.05, "naaghaamm": 748.30, "Ellv": 506.25,
    "its.assil0": 69.20
}

# ==========================================
# THE SNIPER ENVIRONMENT (بيئة التدريب الصارمة)
# ==========================================
class VideoSniperJudgeEnv(gym.Env):
    def __init__(self, df):
        super(VideoSniperJudgeEnv, self).__init__()
        self.df = df
        self.current_step = 0
        self.action_space = spaces.Discrete(2)
        # 7 Features
        self.observation_space = spaces.Box(low=-5.0, high=5.0, shape=(7,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        # خلط البيانات في كل دورة تدريب
        self.df = self.df.sample(frac=1).reset_index(drop=True)
        self.current_step = 0
        return self._next_observation(), {}

    def _next_observation(self):
        row = self.df.iloc[self.current_step]
        obs = np.array([
            (row['rating'] - 1000) / 1000.0,
            row['norm_net_wins'],
            row['win_rate'] * 2 - 1,
            (row['shows'] - 10) / 20.0,
            row['norm_creator'],
            row['has_re'],
            row['rocket_factor']
        ], dtype=np.float32)
        return obs

    def step(self, action):
        row = self.df.iloc[self.current_step]
        is_winner = row['IS_WINNER'] == 1
        
        reward = 0
        
        # --- نظام الثواب والعقاب الجديد ---
        if action == 1: # Pick
            if is_winner:
                reward = 5.0 # مكافأة كبيرة
            else:
                reward = -5.0 # عقوبة مساوية (لتقليل التفاؤل)
        else: # Skip
            if is_winner:
                reward = -5.0 # عقوبة لتفويت الفرصة
            else:
                reward = 1.0 # مكافأة بسيطة للتنظيف
        
        self.current_step += 1
        terminated = (self.current_step >= len(self.df))
        return self._next_observation() if not terminated else np.zeros(7, dtype=np.float32), reward, terminated, False, {}

# ==========================================
# DATA LOADING
# ==========================================
def load_data():
    if not os.path.exists(ELO_FILE_PATH): return None
    with open(ELO_FILE_PATH, 'r', encoding='utf-8') as f: elo_data = json.load(f)
    with open(PROCESSED_FILE_PATH, 'r', encoding='utf-8') as f: processed_data = json.load(f)

    # تحديد الفائزين
    size_to_weight = {}
    for v in processed_data:
        if v.get('file_size'): size_to_weight[v.get('file_size')] = v.get('total_weight', 0)

    data_list = []
    for filename, stats in elo_data.items():
        f_size = stats.get('file_size')
        weight = size_to_weight.get(f_size, 0.0)
        
        rating = stats.get('rating', 1000)
        wins = stats.get('total_wins', 0)
        losses = stats.get('total_losses', 0)
        shows = stats.get('times_shown', 0)
        win_rate = stats.get('win_rate', 0)
        tags = str(stats.get('tags', "")).lower()
        creator = stats.get('name', "unknown")
        
        has_re = 1.0 if 're' in tags else 0.0
        creator_val = CREATOR_BONUSES.get(creator, 0)
        net_wins = wins - losses
        rocket_factor = 1.0 if (shows < 5 and shows > 0 and win_rate > 0.8 and rating > 1000) else 0.0

        row = {
            'rating': rating,
            'shows': shows,
            'win_rate': win_rate,
            'norm_net_wins': net_wins / 50.0,
            'norm_creator': creator_val / 3500.0,
            'has_re': has_re,
            'rocket_factor': rocket_factor,
            'IS_WINNER': 1 if weight > 0 else 0
        }
        data_list.append(row)
    
    return pd.DataFrame(data_list)

# ==========================================
# MAIN JUDGE LOGIC
# ==========================================
def main():
    print("--- ⚖️ COURT SESSION: Sniper Agent vs Benchmark ⚖️ ---")
    
    df = load_data()
    if df is None: return

    # تجهيز نفس مجموعة البيانات المتوازنة (50% فائزين - 50% خاسرين) لعدم ظلم النموذج
    winners = df[df['IS_WINNER'] == 1]
    losers = df[df['IS_WINNER'] == 0].sample(n=len(winners), random_state=42)
    dataset = pd.concat([winners, losers]).sample(frac=1, random_state=42).reset_index(drop=True)
    
    # تقسيم البيانات (80% تدريب - 20% اختبار)
    train_df, test_df = train_test_split(dataset, test_size=0.2, random_state=42)
    
    print(f"Dataset: {len(dataset)} videos.")
    print(f"Training on {len(train_df)} videos...")
    print(f"Testing on {len(test_df)} hidden videos...")
    
    # 1. SETUP ENV & MODEL
    # نستخدم DummyVecEnv لتسريع التدريب
    train_env = DummyVecEnv([lambda: VideoSniperJudgeEnv(train_df)])
    
    # تعريف الشبكة العصبية العميقة (Deep Brain)
    # 128x128 neurons
    policy_kwargs = dict(net_arch=[128, 128])
    
    model = PPO("MlpPolicy", train_env, verbose=1, learning_rate=0.0002, policy_kwargs=policy_kwargs)
    
    # 2. TRAIN (HEAVY TRAINING)
    print("\n🏋️ Training 'The Sniper' (Deep Network)... Please wait...")
    # 100,000 خطوة كافية للاختبار القوي (تستغرق دقيقة أو دقيقتين)
    model.learn(total_timesteps=100000) 
    
    # 3. TEST (PREDICT)
    print("\n📝 Taking the Exam (Hidden Test Set)...")
    test_env = VideoSniperJudgeEnv(test_df)
    
    y_true = []
    y_pred = []
    
    obs, _ = test_env.reset()
    # يجب الحفاظ على ترتيب التست لنقارن صح
    # لذا سنمشي صفاً صفاً يدوياً بدون Env.step العشوائي
    for i in range(len(test_df)):
        # محاكاة الملاحظة يدوياً لضمان الترتيب
        row = test_df.iloc[i]
        obs_manual = np.array([
            (row['rating'] - 1000) / 1000.0,
            row['norm_net_wins'],
            row['win_rate'] * 2 - 1,
            (row['shows'] - 10) / 20.0,
            row['norm_creator'],
            row['has_re'],
            row['rocket_factor']
        ], dtype=np.float32)
        
        action, _ = model.predict(obs_manual, deterministic=True)
        
        y_true.append(row['IS_WINNER'])
        y_pred.append(action)

    # 4. RESULTS
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    accuracy = accuracy_score(y_true, y_pred)
    
    print("\n📊 === SNIPER AGENT REPORT === 📊")
    print(f"Precision (الدقة): {precision:.2%} (Target: >56%)")
    print(f"Recall (الاستدعاء): {recall:.2%} (Target: >60%)")
    print(f"Accuracy (النتيجة النهائية): {accuracy:.2%}")
    
    print("\n--- الحكم ---")
    baseline = 0.5829 # نتيجة الكود اليدوي السابقة
    if accuracy > baseline:
        print(f"✅ مبروك! الذكاء الاصطناعي تفوق على المعادلة اليدوية بفارق {(accuracy-baseline)*100:.2f}%")
        print("القرار: نعتمد هذا النموذج.")
    else:
        print(f"❌ للأسف. المعادلة اليدوية ما زالت أفضل بفارق {(baseline-accuracy)*100:.2f}%")
        print("القرار: نعود للكود اليدوي.")

if __name__ == "__main__":
    main()