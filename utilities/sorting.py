import json
import random
import sys


def select_videos_by_percentile(
        videos_data, lower_percentile, upper_percentile, num_videos, ranking_type):
    """
    Selects videos based on the given percentile range, groups them into competitions,
    and assigns the user-specified number of videos and ranking type.

    Args:
        videos_data (dict): Dictionary of videos with their associated data.
        lower_percentile (float): Lower bound of the percentile range (0-100).
        upper_percentile (float): Upper bound of the percentile range (0-100).
        num_videos (int): Number of videos per competition.
        ranking_type (str): Ranking type for the competition ("winner_only" or "Ranked_type").

    Returns:
        list: A list of competition dictionaries.
    """
    if not videos_data:
        return []

    for video, data in videos_data.items():
        score = (
            data.get("rating", 1000)
            + (10 * data.get("win_streak", 0))
            - (5 * data.get("loss_streak", 0))
            - (50 * data.get("times_shown", 0))
        )
        data["score"] = score

    sorted_videos = sorted(videos_data.items(), key=lambda x: x[1]["score"])
    total_videos = len(sorted_videos)
    start_index = int(total_videos * (lower_percentile / 100))
    end_index = int(total_videos * (upper_percentile / 100))

    start_index = max(0, start_index)
    end_index = min(total_videos, end_index)

    selected_videos = sorted_videos[start_index:end_index]
    if not selected_videos:
        return []

    random.shuffle(selected_videos)

    competitions = []
    num_groups = len(selected_videos) // num_videos

    for i in range(num_groups):
        group = selected_videos[i * num_videos:(i + 1) * num_videos]
        competition = {
            "videos": [video_id for video_id, data in group],
            "rating": [data.get("rating", 1000) for video_id, data in group],
            "file_size": [data.get("file_size", 0) for video_id, data in group],
            "mode": 1,
            "num_videos": num_videos,
            "ranking_type": ranking_type,
            "competition_type": "random"
        }
        competitions.append(competition)

    return competitions


def safe_json_dumps(obj, indent=None, ensure_ascii=False):
    """
    Safely converts an object to a JSON-formatted string by replacing problematic characters.
    """
    def replace_problematic_chars(o):
        if isinstance(o, str):
            return "".join(
                c if ord(c) < 0xD800 or ord(c) > 0xDFFF else f"\\u{ord(c):04x}"
                for c in o
            )
        elif isinstance(o, dict):
            return {replace_problematic_chars(
                k): replace_problematic_chars(v) for k, v in o.items()}
        elif isinstance(o, list):
            return [replace_problematic_chars(elem) for elem in o]
        else:
            return o

    return json.dumps(replace_problematic_chars(
        obj), indent=indent, ensure_ascii=ensure_ascii)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python sort.py data.json")
        sys.exit(1)

    json_file_path = sys.argv[1]

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            videos_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {json_file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in: {json_file_path}")
        sys.exit(1)

    lower_percentile = float(input("Enter the lower percentile (0-100): "))
    upper_percentile = float(input("Enter the upper percentile (0-100): "))

    try:
        num_videos = int(input("Enter the number of videos per competition: "))
    except ValueError:
        print("Invalid input for number of videos. Please enter an integer.")
        sys.exit(1)

    ranking_type = input(
        "Enter the ranking type ('winner_only' or 'Ranked_type'): ").strip()
    if ranking_type not in ["winner_only", "Ranked_type"]:
        print("Invalid ranking type. Please choose 'winner_only' or 'Ranked_type'.")
        sys.exit(1)

    competitions = select_videos_by_percentile(
        videos_data,
        lower_percentile,
        upper_percentile,
        num_videos,
        ranking_type)
    print(safe_json_dumps(competitions, indent=4, ensure_ascii=False))
