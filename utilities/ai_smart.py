import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import json
import os
import random
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

# ==========================================
# 1. CONFIGURATION
# ==========================================
BASE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
ELO_FILE_PATH = os.path.join(BASE_DIR, "elo_videos_A1000 elo tik.json")
PROCESSED_FILE_PATH = os.path.join(BASE_DIR, "processed_videos.json")
ARCHIVE_FILE_PATH = os.path.join(BASE_DIR, "tournamentarchive.json")
USED_CANDIDATES_PATH = os.path.join(BASE_DIR, "used_candidates_log.json") # ملف الذاكرة
MODEL_PATH = "production_sniper_agent.zip"

OUTPUT_PREFIX = "topcut_elo_videos_A1000 elo tik_"

CREATOR_BONUSES = {
    "hajar0220": 3428.30, "ibu2b": 1584.00, "rahma_ghorbel7": 1115.05,
    "camvred1": 843.05, "naaghaamm": 748.30, "Ellv": 506.25,
    "its.assil0": 69.20
}

# ==========================================
# 2. THE SNIPER ENVIRONMENT (Must match training)
# ==========================================
class VideoSniperEnv(gym.Env):
    def __init__(self, df, is_training=True):
        super(VideoSniperEnv, self).__init__()
        self.df = df
        self.is_training = is_training
        self.current_step = 0
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(low=-5.0, high=5.0, shape=(7,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if self.is_training:
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
        is_winner = row['TARGET_WEIGHT'] > 0
        reward = 0
        if action == 1: 
            if is_winner: reward = 5.0
            else: reward = -5.0
        else:
            if is_winner: reward = -5.0
            else: reward = 1.0
        self.current_step += 1
        terminated = (self.current_step >= len(self.df))
        return self._next_observation() if not terminated else np.zeros(7, dtype=np.float32), reward, terminated, False, {}

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def load_json(filepath):
    if not os.path.exists(filepath): return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_json(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
    except Exception as e: print(f"Error saving: {e}")

def load_and_prep_data():
    if not os.path.exists(ELO_FILE_PATH): return None
    elo_data = load_json(ELO_FILE_PATH)
    processed_data = load_json(PROCESSED_FILE_PATH)
    
    size_to_weight = {}
    if isinstance(processed_data, list):
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
            'filename': filename,
            'rating': rating,
            'shows': shows,
            'TARGET_WEIGHT': weight,
            'norm_net_wins': net_wins / 50.0,
            'norm_creator': creator_val / 3500.0,
            'win_rate': win_rate,
            'has_re': has_re,
            'rocket_factor': rocket_factor,
            'file_size': f_size
        }
        data_list.append(row)
    return pd.DataFrame(data_list)

# ==========================================
# 4. MAIN LOGIC
# ==========================================
def main():
    print("--- 🏆 AI TOURNAMENT MANAGER (CONTROLLED) 🏆 ---")
    
    # A. Load Data
    df = load_and_prep_data()
    if df is None: return

    train_df = df.copy()
    candidates_df = df[df['TARGET_WEIGHT'] == 0].copy() # Non-winners only

    # B. Load Model (Assume it exists from previous run, or train if missing)
    if not os.path.exists(MODEL_PATH):
        print("Training Brain (First Time)...")
        env = DummyVecEnv([lambda: VideoSniperEnv(train_df, is_training=True)])
        model = PPO("MlpPolicy", env, verbose=0, learning_rate=0.0002, policy_kwargs=dict(net_arch=[128, 128]))
        model.learn(total_timesteps=200000)
        model.save(MODEL_PATH)
    else:
        model = PPO.load(MODEL_PATH)
    
    # C. AI Scouting
    print(f"AI is scanning {len(candidates_df)} videos...")
    eval_env = VideoSniperEnv(candidates_df, is_training=False)
    obs, _ = eval_env.reset()
    
    ai_approved_list = []
    
    for i in range(len(candidates_df)):
        action, _ = model.predict(obs, deterministic=True)
        if action == 1:
            ai_approved_list.append(candidates_df.iloc[i])
        obs, _, dones, _, _ = eval_env.step(action)
        if dones: break

    # Convert approved list to DataFrame for filtering/sorting
    if not ai_approved_list:
        print("AI found nothing. Try retraining.")
        return
        
    approved_df = pd.DataFrame(ai_approved_list)
    
    # --- D. FILTERING (THE MANUAL CONTROL) ---
    print(f"\nAI approved {len(approved_df)} Elite Candidates.")
    
    # 1. Used Log Check
    used_log = load_json(USED_CANDIDATES_PATH)
    used_files = set(used_log.get("used_files", []))
    
    print(f"Log contains {len(used_files)} previously used candidates.")
    if input("Exclude used candidates? (y/n): ").strip().lower() == 'y':
        approved_df = approved_df[~approved_df['filename'].isin(used_files)]
        print(f"Filtered down to {len(approved_df)} fresh elites.")
    
    # 2. Sorting
    # نرتب المرشحين حسب التقييم لكي يكون "أعلى المرشحين" هم الأقوى فعلاً
    approved_df = approved_df.sort_values(by='rating', ascending=False).reset_index(drop=True)
    
    # 3. Selection Range (The requested feature)
    print("\n--- Selection Options ---")
    try:
        num_to_pick = int(input(f"How many to pick? (Max {len(approved_df)}): "))
        print(f"Available Range: 1 to {len(approved_df)}")
        start_rank = int(input("Start from Rank # (e.g. 1): ")) - 1
        end_rank = int(input(f"End at Rank # (e.g. {min(50, len(approved_df))}): "))
        
        # Validation
        start_rank = max(0, start_rank)
        end_rank = min(len(approved_df), end_rank)
        
        subset = approved_df.iloc[start_rank:end_rank]
        
        if len(subset) == 0:
            print("Range is empty! Taking top available.")
            subset = approved_df.head(num_to_pick)
            
        # Random sample from the user-defined range
        selected_rows = subset.sample(n=min(num_to_pick, len(subset)))
        selected_elites = selected_rows['filename'].tolist()
        
    except ValueError:
        print("Invalid input. Selecting top 4 by default.")
        selected_elites = approved_df.head(4)['filename'].tolist()

    # --- PRINT NAMES (VISIBILITY) ---
    print("\n✅ SELECTED ELITES:")
    for vid in selected_elites:
        # Fetch stats to display
        stats = df[df['filename'] == vid].iloc[0]
        print(f"   - {vid} (Rating: {stats['rating']:.0f})")

    # E. Tournament Generation (Fillers + Seeding)
    print("\n--- Creating Tournament ---")
    try:
        total_participants = int(input("Total participants? (e.g. 32): "))
        videos_per_match = int(input("Videos per match? (e.g. 2): "))
    except:
        total_participants = 32
        videos_per_match = 2

    # Fillers
    candidates_pool = candidates_df[~candidates_df['filename'].isin(selected_elites)]
    filler_pool = candidates_pool['filename'].tolist()
    
    needed = total_participants - len(selected_elites)
    final_roster = selected_elites.copy()
    
    if needed > 0:
        fillers = random.sample(filler_pool, min(len(filler_pool), needed))
        final_roster.extend(fillers)
    
    # Smart Seeding
    random.shuffle(selected_elites)
    current_fillers = [v for v in final_roster if v not in selected_elites]
    random.shuffle(current_fillers)
    
    num_matches = total_participants // videos_per_match
    matches = [[] for _ in range(num_matches)]
    
    # Distribute Elites
    for i, elite in enumerate(selected_elites):
        matches[i % num_matches].append(elite)
        
    # Distribute Fillers
    idx = 0
    for filler in current_fillers:
        while len(matches[idx]) >= videos_per_match:
            idx = (idx + 1) % num_matches
        matches[idx].append(filler)
        idx = (idx + 1) % num_matches

    # JSON Construction
    final_matches_data = []
    elo_source = load_json(ELO_FILE_PATH) # Reload for details
    
    for batch in matches:
        if not batch: continue
        rts = []
        szs = []
        for v in batch:
            s = elo_source.get(v, {})
            rts.append(s.get('rating', 1000))
            szs.append(s.get('file_size', 0))
            
        final_matches_data.append({
            "videos": batch,
            "rating": rts,
            "file_size": szs,
            "mode": 1,
            "num_videos": len(batch),
            "ranking_type": "winner_only",
            "competition_type": "AI_Sniper_Seeded"
        })

    # Save
    rnd = random.randint(1000, 9999)
    fname = f"{OUTPUT_PREFIX}{rnd}.json"
    full_path = os.path.join(BASE_DIR, fname)
    save_json(full_path, final_matches_data)
    
    # Update Archive
    arch = load_json(ARCHIVE_FILE_PATH)
    arch[fname.replace('.json','')] = {"initial_participants": len(final_roster)}
    save_json(ARCHIVE_FILE_PATH, arch)
    
    # Update Used Log
    current_used = set(used_log.get("used_files", []))
    current_used.update(selected_elites)
    used_log["used_files"] = list(current_used)
    save_json(USED_CANDIDATES_PATH, used_log)
    
    print(f"\n🎉 Done! Tournament: {fname}")
    print("   Archive and Used-Log updated.")

if __name__ == "__main__":
    main()