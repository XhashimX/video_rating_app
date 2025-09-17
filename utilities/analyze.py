import json
import numpy as np
import os
from datetime import datetime



class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def convert_bytes_to_mb(bytes_val):
    return bytes_val / (1024 * 1024)


def analyze_data(data):
    ratings = [item['rating'] for item in data.values()]
    file_sizes = [item['file_size'] for item in data.values()]
    win_streaks = [item['win_streak'] for item in data.values()]
    loss_streaks = [item['loss_streak'] for item in data.values()]
    times_shown_list = [item.get('times_shown', 0) for item in data.values()]

    print(
        f"Analyzing data: ratings={ratings}, file_sizes={file_sizes}, win_streaks={win_streaks}, loss_streaks={loss_streaks}, times_shown={times_shown_list}")

    output = {}

    average_file_size = convert_bytes_to_mb(np.mean(file_sizes))
    average_rating_mean = np.mean(ratings)
    average_rating_median = np.median(ratings)
    highest_rating = max(ratings)
    lowest_rating = min(ratings)
    output["general"] = {
        "average_file_size": f"{average_file_size:.2f} MB",
        "average_rating_mean": f"{average_rating_mean:.2f}",
        "average_rating_median": f"{average_rating_median:.2f}",
        "highest_rating": f"{highest_rating:.2f}",
        "lowest_rating": f"{lowest_rating:.2f}"
    }

    output["general"]["total_files"] = len(ratings)

    rating_ranges = [
        (1, 300),      # من 1-300
        (301, 700),    # من 301-700
        (701, 999),    # من 701-999
        (1000, 1000),  # 1000 فقط
        (1001, 1250),  # من 1001-1250
        (1251, 1399),  # من 1251-1399
        (1400, 1400),  # 1400 فقط
        (1401, 1999),  # من 1401-1999
        (2000, 3000),  # من 2000-3000
        (3001, float('inf'))  # أكبر من 3000
    ]

    output["rating_percentages"] = {}
    for lower, upper in rating_ranges:
        count = sum(1 for r in ratings if lower <= r <= upper)
        percentage = (count / len(ratings)) * 100
        output["rating_percentages"][
            f"from_{lower}_to_{upper}"] = f"{
            percentage:.2f}% ({count})"

    average_win_streak = np.mean(win_streaks)
    average_loss_streak = np.mean(loss_streaks)
    win_streak_5_plus = sum(1 for ws in win_streaks if ws > 5)
    loss_streak_5_plus = sum(1 for ls in loss_streaks if ls > 5)

    output["streak_statistics"] = {
        "average_win_streak": f"{average_win_streak:.2f}",
        "average_loss_streak": f"{average_loss_streak:.2f}",
        "win_streak_5_plus": f"{win_streak_5_plus}",
        "loss_streak_5_plus": f"{loss_streak_5_plus}"
    }

    rating_size_ranges = [
        (1, 800), (800, 1250), (1250, 2000), (2000, 3000)
    ]
    output["file_size_analysis"] = {}
    for lower, upper in rating_size_ranges:
        sizes_in_range = [file_sizes[i]
                          for i, r in enumerate(ratings) if lower <= r < upper]
        if sizes_in_range:
            average_size = convert_bytes_to_mb(np.mean(sizes_in_range))
            output["file_size_analysis"][f"from_{lower}_to_{upper}"] = f"{average_size:.2f} MB"
        else:
            output["file_size_analysis"][f"from_{lower}_to_{upper}"] = "N/A"

    std_rating = np.std(ratings)
    std_file_size = convert_bytes_to_mb(np.std(file_sizes))
    std_win_streak = np.std(win_streaks)
    std_loss_streak = np.std(loss_streaks)
    output["standard_deviation"] = {
        "std_rating": f"{std_rating:.2f}",
        "std_file_size": f"{std_file_size:.2f} MB",
        "std_win_streak": f"{std_win_streak:.2f}",
        "std_loss_streak": f"{std_loss_streak:.2f}"
    }

    sorted_ratings = sorted(ratings)
    percentiles = {
        "أقل 10%": (sorted_ratings[0], np.percentile(sorted_ratings, 10)),
        "أقل 20%": (sorted_ratings[0], np.percentile(sorted_ratings, 20)),
        "أعلى 10%": (np.percentile(sorted_ratings, 90), sorted_ratings[-1]),
        "أعلى 20%": (np.percentile(sorted_ratings, 80), sorted_ratings[-1])
    }

    output["percentile_ranges"] = {}
    for key, (lower, upper) in percentiles.items():
        output["percentile_ranges"][key] = f"من {lower:.2f} إلى {upper:.2f}"

    times_shown_count = {}
    for ts in times_shown_list:
        times_shown_count[ts] = times_shown_count.get(ts, 0) + 1

    average_times_shown = np.mean(times_shown_list) if times_shown_list else 0
    min_times_shown = min(times_shown_list) if times_shown_list else 0
    max_times_shown = max(times_shown_list) if times_shown_list else 0

    times_shown_analysis = {
        "counts": {
            f"Time shown {ts}": f"{count} فيديوهات"
            for ts, count in sorted(times_shown_count.items())
        },
        "متوسط مرات الظهور": f"{average_times_shown:.2f}",
        "أدنى مرات ظهور": f"{min_times_shown}",
        "أعلى مرات ظهور": f"{max_times_shown}"
    }
    output["times_shown_analysis"] = times_shown_analysis

    print(f"Analysis output: {output}")
    return output


def save_analysis_to_file(data, json_file_name, status_dir):
    os.makedirs(status_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = os.path.join(
        status_dir, f"{
            os.path.basename(json_file_name).replace(
                '.json', '')}_{timestamp}.txt")
    output = ""

    output += f"1. General Statistics:\n"
    output += f"   - Average File Size: {
        data['general']['average_file_size']}\n"
    output += f"   - Average Rating (Mean): {
        data['general']['average_rating_mean']}\n"
    output += f"   - Average Rating (Median): {
        data['general']['average_rating_median']}\n"
    output += f"   - Highest Rating: {data['general']['highest_rating']}\n"
    output += f"   - Lowest Rating: {data['general']['lowest_rating']}\n"

    output += f"\n2. Rating Percentages:\n"
    for key, value in data["rating_percentages"].items():
        lower = key.split('_')[1]
        upper = key.split('_')[3]
        output += f"   - Percentage of Ratings from {lower} to {upper}: {value}\n"

    output += f"\n3. Win/Loss Streak Statistics:\n"
    output += f"   - Average Win Streak Length: {
        data['streak_statistics']['average_win_streak']}\n"
    output += f"   - Average Loss Streak Length: {
        data['streak_statistics']['average_loss_streak']}\n"
    output += f"   - Number of Images with Win Streak > 5: {
        data['streak_statistics']['win_streak_5_plus']}\n"
    output += f"   - Number of Images with Loss Streak > 5: {
        data['streak_statistics']['loss_streak_5_plus']}\n"

    output += f"\n4. File Size Analysis Based on Ratings:\n"
    for key, value in data["file_size_analysis"].items():
        lower = key.split('_')[1]
        upper = key.split('_')[3]
        output += f"   - Average File Size for Ratings from {lower} to {upper}: {value}\n"

    output += f"\n5. Standard Deviation:\n"
    output += f"   - Standard Deviation of Ratings: {
        data['standard_deviation']['std_rating']}\n"
    output += f"   - Standard Deviation of File Sizes: {
        data['standard_deviation']['std_file_size']}\n"
    output += f"   - Standard Deviation of Win Streaks: {
        data['standard_deviation']['std_win_streak']}\n"
    output += f"   - Standard Deviation of Loss Streaks: {
        data['standard_deviation']['std_loss_streak']}\n"

    output += f"\n6. النسب المئوية للتقييمات:\n"
    for key, value in data["percentile_ranges"].items():
        output += f"   - {key}: {value}\n"

    output += f"\nالعدد الكلي للملفات: {data['general']['total_files']}\n"

    with open(output_file, 'w') as f:
        f.write(output)
    return output_file
