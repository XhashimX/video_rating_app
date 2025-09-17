import json
import os

def load_video_data(file_path):
    """Loads video data from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None

def calculate_strength_score_1(video_data, bonuses, penalties):
    """Calculates Strength Score using the first proposed formula."""
    rating = video_data.get("rating", 0)
    win_rate = video_data.get("win_rate", 0)
    win_streak = video_data.get("win_streak", 0)
    loss_streak = video_data.get("loss_streak", 0)
    total_wins = video_data.get("total_wins", 0)
    total_losses = video_data.get("total_losses", 0)

    return rating + (win_rate * bonuses['bonus1']) + \
           (win_streak * bonuses['bonus2']) - (loss_streak * penalties['penalty1']) + \
           (total_wins * bonuses['bonus3']) - (total_losses * penalties['penalty2'])

def calculate_strength_score_2(video_data, bonus_values):
    """Calculates Strength Score using the second proposed formula."""
    rating = video_data.get("rating", 0)
    times_shown = video_data.get("times_shown", 0)
    total_wins = video_data.get("total_wins", 0)
    total_losses = video_data.get("total_losses", 0)
    win_streak = video_data.get("win_streak", 0)
    loss_streak = video_data.get("loss_streak", 0)

    # Avoid division by zero or very small numbers
    if times_shown == 0:
        average_performance = 0
    else:
        average_performance = (total_wins - total_losses) / times_shown

    return rating + (average_performance * bonus_values['bonus']) + \
           (win_streak * bonus_values['bonus_streak']) - (loss_streak * bonus_values['penalty_streak'])

def calculate_strength_score_3(video_data, max_times_shown, bonus_values, penalty_values):
    """Calculates Strength Score using the third proposed formula."""
    rating = video_data.get("rating", 0)
    times_shown = video_data.get("times_shown", 0)
    win_rate = video_data.get("win_rate", 0)
    loss_streak = video_data.get("loss_streak", 0)

    # Avoid division by zero for max_times_shown if no videos have been shown
    if max_times_shown == 0:
         rating_multiplier = 1
    else:
        rating_multiplier = 1 + (times_shown / max_times_shown) * bonus_values['bonus_times_shown']

    return (rating * rating_multiplier) + \
           (win_rate * bonus_values['bonus_win_rate']) - (loss_streak * penalty_values['penalty_loss_streak'])

def main():
    """Main function to load data, calculate scores, rank, and save results."""
    input_file_path = "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json"
    output_file_path = "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_ranked.json"

    video_data = load_video_data(input_file_path)

    if video_data is None:
        return

    # Define initial bonus and penalty values for each formula
    # These can be adjusted based on desired weighting
    bonuses_penalties_1 = {'bonus1': 100, 'bonus2': 20, 'penalty1': 15, 'bonus3': 10, 'penalty2': 5}
    bonus_values_2 = {'bonus': 100, 'bonus_streak': 20, 'penalty_streak': 15}
    bonus_penalty_values_3 = {'bonus_times_shown': 100, 'bonus_win_rate': 100, 'penalty_loss_streak': 15}

    # Calculate max_times_shown for formula 3
    max_times_shown = 0
    for data in video_data.values():
        max_times_shown = max(max_times_shown, data.get("times_shown", 0))

    video_strength_scores = {}
    for video_file, data in video_data.items():
        score1 = calculate_strength_score_1(data, bonuses_penalties_1, bonuses_penalties_1)
        score2 = calculate_strength_score_2(data, bonus_values_2)
        score3 = calculate_strength_score_3(data, max_times_shown, bonus_penalty_values_3, bonus_penalty_values_3)

        video_strength_scores[video_file] = {
            'score1': score1,
            'score2': score2,
            'score3': score3
        }

    # Calculate individual ranks for each formula
    ranked_videos_1 = sorted(video_strength_scores.keys(), key=lambda x: video_strength_scores[x]['score1'], reverse=True)
    ranked_videos_2 = sorted(video_strength_scores.keys(), key=lambda x: video_strength_scores[x]['score2'], reverse=True)
    ranked_videos_3 = sorted(video_strength_scores.keys(), key=lambda x: video_strength_scores[x]['score3'], reverse=True)

    # Store the rank of each video in each list
    video_ranks = {}
    for video_file in video_data.keys():
        rank1 = ranked_videos_1.index(video_file) + 1
        rank2 = ranked_videos_2.index(video_file) + 1
        rank3 = ranked_videos_3.index(video_file) + 1

        video_ranks[video_file] = {
            'rank1': rank1,
            'rank2': rank2,
            'rank3': rank3,
            'average_rank': (rank1 + rank2 + rank3) / 3
        }

    # Sort videos based on the average rank
    final_ranked_videos = sorted(video_ranks.keys(), key=lambda x: video_ranks[x]['average_rank'])

    # Create the final ordered dictionary with the original data and the average rank
    ordered_video_data = {}
    for video_file in final_ranked_videos:
        ordered_video_data[video_file] = video_data[video_file]
        # Optionally, add the calculated scores and ranks to the output data
        # ordered_video_data[video_file]['strength_scores'] = video_strength_scores[video_file]
        # ordered_video_data[video_file]['ranks'] = video_ranks[video_file]


    # Save the ranked data to a new JSON file
    try:
        with open(output_file_path, 'w') as f:
            json.dump(ordered_video_data, f, indent=4)
        print(f"Ranked video data saved to {output_file_path}")
    except IOError:
        print(f"Error: Could not write to file {output_file_path}")

if __name__ == "__main__":
    main()
