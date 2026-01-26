import json
import os
import pandas as pd
import random
import math

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
ELO_FILE_PATH = os.path.join(BASE_DIR, "elo_videos_A1000 elo tik.json")
PROCESSED_FILE_PATH = os.path.join(BASE_DIR, "processed_videos.json")
ARCHIVE_FILE_PATH = os.path.join(BASE_DIR, "tournamentarchive.json")
USED_CANDIDATES_PATH = os.path.join(BASE_DIR, "used_candidates_log.json")

OUTPUT_PREFIX = "topcut_elo_videos_A1000 elo tik_"

# Creator Bonuses Configuration
CREATOR_BONUSES = {
    "hajar0220": 3428.30,
    "ibu2b": 1584.00,
    "rahma_ghorbel7": 1115.05,
    "camvred1": 843.05,
    "naaghaamm": 748.30,
    "Ellv": 506.25,
    "dana.alerksousi8": 483.50,
    "vanistrimer": 389.00,
    "its.assil0": 69.20,
    "maramramadan2": 67.00
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_json(filepath):
    if not os.path.exists(filepath):
        return {} if filepath in [ARCHIVE_FILE_PATH, USED_CANDIDATES_PATH] else None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return {}

def save_json(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

def calculate_advanced_score(row):
    score = 0
    
    # 1. Expert Tag (Re) -> 1000 points
    if row['has_re']:
        score += 1000
        
    # 2. Rating -> Full Value
    score += row['rating']
    
    # 3. Efficiency Relationship (High Rating + Low Shows = Better)
    # المعادلة: التقييم تقسيم (عدد مرات الظهور + 1) مضروب في عامل تضخيم
    # هذا يعطي دفعة قوية للفيديوهات الجديدة ذات التقييم العالي
    efficiency_bonus = (row['rating'] / max(1, row['times_shown'])) * 5
    score += efficiency_bonus
    
    # 4. Creator Bonus (Fixed List)
    score += CREATOR_BONUSES.get(row['creator_name'], 0)
    
    # 5. Net Wins -> Wins - Losses * 500
    score += row['net_wins'] * 500
    
    # 6. Win Rate -> * 1000
    score += row['win_rate'] * 1000
    
    # 7. Streaks (Exponential)
    # Win Streak: Adds exponentially
    if row['win_streak'] > 0:
        score += (row['win_streak'] ** 2) * 50 # Example: Streak 3 = 9*50 = 450
        
    # Loss Streak: Subtracts exponentially (only if > 1)
    if row['loss_streak'] > 1:
        score -= (row['loss_streak'] ** 2) * 50 # Example: Streak 3 = 9*50 = 450 penalty

    return score

def get_candidates_analysis(elo_data, processed_data):
    size_to_weight = {}
    if isinstance(processed_data, list):
        for v in processed_data:
            if v.get('file_size'):
                size_to_weight[v.get('file_size')] = v.get('total_weight', 0)

    data_list = []
    
    for filename, stats in elo_data.items():
        f_size = stats.get('file_size')
        if size_to_weight.get(f_size, 0) > 0:
            continue # Skip winners

        row = {
            'filename': filename,
            'file_size': f_size,
            'rating': stats.get('rating', 0),
            'times_shown': stats.get('times_shown', 0),
            'win_rate': stats.get('win_rate', 0),
            'total_wins': stats.get('total_wins', 0),
            'total_losses': stats.get('total_losses', 0),
            'win_streak': stats.get('win_streak', 0),
            'loss_streak': stats.get('loss_streak', 0),
            'creator_name': stats.get('name', "unknown"),
            'has_re': 1 if 're' in str(stats.get('tags', "")).lower() else 0,
            'net_wins': stats.get('total_wins', 0) - stats.get('total_losses', 0)
        }
        data_list.append(row)

    df = pd.DataFrame(data_list)
    
    # Apply the new scoring formula
    df['POTENTIAL_SCORE'] = df.apply(calculate_advanced_score, axis=1)
    
    return df.sort_values(by='POTENTIAL_SCORE', ascending=False)

# ==========================================
# MAIN LOGIC
# ==========================================

def main():
    print("--- Advanced Tournament Generator ---")
    
    elo_data = load_json(ELO_FILE_PATH)
    processed_data = load_json(PROCESSED_FILE_PATH)
    used_log = load_json(USED_CANDIDATES_PATH)
    
    if not elo_data: return

    # 1. Analyze
    print("Calculating scores based on new formula...")
    candidates_df = get_candidates_analysis(elo_data, processed_data)
    
    # Filter Used
    previously_used = set(used_log.get("used_files", []))
    if input(f"Include {len(previously_used)} used candidates? (y/n): ").strip().lower() != 'y':
        candidates_df = candidates_df[~candidates_df['filename'].isin(previously_used)]
        candidates_df = candidates_df.reset_index(drop=True)

    # 2. Select Elite Candidates
    selected_elites = []
    try:
        count = int(input("How many candidates to pick? (e.g. 8): "))
        if count > 0:
            start = int(input("Start Rank (e.g. 1): ")) - 1
            end = int(input(f"End Rank (Max {len(candidates_df)}): "))
            subset = candidates_df.iloc[start:end]
            selected_elites = subset.sample(n=min(count, len(subset)))['filename'].tolist()
            print(f"Selected {len(selected_elites)} Elites.")
    except:
        selected_elites = []

    # 3. Setup Tournament
    try:
        total_participants = int(input("Total participants? (e.g. 32): "))
        videos_per_match = int(input("Videos per match? (e.g. 2): "))
    except:
        total_participants = 32
        videos_per_match = 2

    # 4. Fill with Randoms
    needed_fillers = total_participants - len(selected_elites)
    random_fillers = []
    
    if needed_fillers > 0:
        remaining_pool = candidates_df[~candidates_df['filename'].isin(selected_elites)]
        available = remaining_pool['filename'].tolist()
        random_fillers = random.sample(available, min(len(available), needed_fillers))
        
    print(f"Elites: {len(selected_elites)} | Random Fillers: {len(random_fillers)}")

    # 5. Smart Seeding (Distribute Elites to avoid clashes)
    num_matches = total_participants // videos_per_match
    matches_list = [[] for _ in range(num_matches)] # Create empty buckets
    
    all_videos_queue = []
    
    # Strategy: Place Elites into separate matches first
    # If we have 4 elites and 16 matches, matches 0,1,2,3 get one elite each.
    
    # Shuffle lists to randomize positions
    random.shuffle(selected_elites)
    random.shuffle(random_fillers)
    
    # A. Distribute Elites
    for i, elite_vid in enumerate(selected_elites):
        target_match_index = i % num_matches
        matches_list[target_match_index].append(elite_vid)
        
    # B. Distribute Fillers to complete the matches
    # Flatten the fillers and add them where space is needed
    current_match_idx = 0
    for filler_vid in random_fillers:
        # Find a match that isn't full
        while len(matches_list[current_match_idx]) >= videos_per_match:
            current_match_idx = (current_match_idx + 1) % num_matches
        
        matches_list[current_match_idx].append(filler_vid)
        current_match_idx = (current_match_idx + 1) % num_matches

    # 6. Build Final Match Objects
    final_matches_data = []
    for batch in matches_list:
        if not batch: continue
        
        batch_ratings = []
        batch_sizes = []
        
        for vid in batch:
            stats = elo_data.get(vid, {})
            batch_ratings.append(stats.get('rating', 1000))
            batch_sizes.append(stats.get('file_size', 0))

        final_matches_data.append({
            "videos": batch,
            "rating": batch_ratings,
            "file_size": batch_sizes,
            "mode": 1,
            "num_videos": len(batch),
            "ranking_type": "winner_only",
            "competition_type": "random_seeded" # Indicate seeding was used
        })

    # 7. Save
    random_id = f"{random.randint(1000, 9999)}"
    filename = f"{OUTPUT_PREFIX}{random_id}.json"
    full_path = os.path.join(BASE_DIR, filename)
    
    save_json(full_path, final_matches_data)
    print(f"Tournament Created: {filename}")
    
    # Archive & Log
    archive_data = load_json(ARCHIVE_FILE_PATH)
    archive_data[filename.replace('.json', '')] = {"initial_participants": total_participants}
    save_json(ARCHIVE_FILE_PATH, archive_data)
    
    used_log["used_files"] = list(set(used_log.get("used_files", []) + selected_elites))
    save_json(USED_CANDIDATES_PATH, used_log)

if __name__ == "__main__":
    main()