import json
import os
import pandas as pd

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
ELO_FILE_PATH = os.path.join(BASE_DIR, "elo_videos_A1000 elo tik.json")
PROCESSED_FILE_PATH = os.path.join(BASE_DIR, "processed_videos.json")

# Creator Bonuses
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

def load_json(filepath):
    if not os.path.exists(filepath): return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    print("--- Loading Data for Advanced Scoring ---")
    elo_data = load_json(ELO_FILE_PATH)
    processed_data = load_json(PROCESSED_FILE_PATH)

    # Exclude winners
    winners = set()
    for v in processed_data:
        if v.get('file_size'): winners.add(v.get('file_size'))

    data_list = []
    for filename, stats in elo_data.items():
        if stats.get('file_size') in winners: continue

        # Stats
        rating = stats.get('rating', 0)
        wins = stats.get('total_wins', 0)
        losses = stats.get('total_losses', 0)
        shows = stats.get('times_shown', 0)
        win_rate = stats.get('win_rate', 0)
        win_streak = stats.get('win_streak', 0)
        loss_streak = stats.get('loss_streak', 0)
        creator = stats.get('name', "unknown")
        tags = str(stats.get('tags', "")).lower()
        net_wins = wins - losses

        # --- NEW FORMULA CALCULATION ---
        score = 0
        reasons = []

        # 1. Re Tag (1000)
        if 're' in tags:
            score += 1000
            reasons.append("RE_TAG")

        # 2. Rating (Full)
        score += rating

        # 3. Efficiency (Rocket Logic)
        # (Rating / Max(1, Shows)) * 5
        eff_score = (rating / max(1, shows)) * 5
        score += eff_score
        if eff_score > 1000: reasons.append("ROCKET_EFF")

        # 4. Creator Bonus
        c_bonus = CREATOR_BONUSES.get(creator, 0)
        if c_bonus > 0:
            score += c_bonus
            reasons.append(f"CREATOR({creator[:5]})")

        # 5. Net Wins (* 500)
        score += net_wins * 500
        if net_wins > 0: reasons.append("POS_NET")

        # 6. Win Rate (* 1000)
        score += win_rate * 1000

        # 7. Streaks
        if win_streak > 0:
            s_bonus = (win_streak ** 2) * 50
            score += s_bonus
            if win_streak > 2: reasons.append(f"W_STREAK({win_streak})")
            
        if loss_streak > 1:
            s_penalty = (loss_streak ** 2) * 50
            score -= s_penalty
            reasons.append(f"L_PENALTY({loss_streak})")

        row = {
            'Filename': filename,
            'Score': int(score),
            'Reason': "+".join(reasons) if reasons else "-",
            'Rating': int(rating),
            'NetWins': net_wins,
            'Shows': shows,
            'Creator': creator if creator in CREATOR_BONUSES else ""
        }
        data_list.append(row)

    df = pd.DataFrame(data_list)
    df = df.sort_values(by='Score', ascending=False).reset_index(drop=True)
    df.index += 1
    
    # Display
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    print("\n--- TOP 25 CANDIDATES (New Formula) ---")
    cols = ['Score', 'Reason', 'Rating', 'NetWins', 'Shows', 'Creator', 'Filename']
    print(df[cols].head(25))

if __name__ == "__main__":
    main()