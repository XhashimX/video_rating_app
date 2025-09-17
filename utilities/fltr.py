import json  

def filter_videos(data_file):
    """
    Filters video data based on user-specified criteria for rating, times_shown, tags, and win_rate.

    Args:
        data_file (str): The path to the JSON file containing the video data.

    Returns:
        None: Writes the filtered data to a new JSON file. Prints error messages if
              the input file is invalid or if filtering parameters are incorrect.
    """

    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {data_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file: {data_file}")
        return

    filtered_data = data.copy()  # Start with a copy of the original data

    # فلترة بناءً على rating
    rating_filter = input("Enter rating filter (none, exact_value, min-max, min1-max1,min2-max2): ")
    if rating_filter.lower() != "none":
        try:
            if "," in rating_filter:  # Multiple ranges
                ranges = rating_filter.split(",")
                valid_ranges = []
                for r in ranges:
                    min_val, max_val = map(int, r.split("-"))
                    valid_ranges.append((min_val, max_val))
                filtered_data = {
                    k: v for k, v in filtered_data.items()
                    if any(min_val <= v['rating'] <= max_val for min_val, max_val in valid_ranges)
                }
            elif "-" in rating_filter:  # Single range
                min_val, max_val = map(int, rating_filter.split("-"))
                filtered_data = {
                    k: v for k, v in filtered_data.items()
                    if min_val <= v['rating'] <= max_val
                }
            else:  # Exact value
                exact_rating = int(rating_filter)
                filtered_data = {
                    k: v for k, v in filtered_data.items()
                    if v['rating'] == exact_rating
                }
        except (ValueError, TypeError):
            print("Error: Invalid rating filter format.")
            return

    # فلترة بناءً على times_shown
    times_shown_filter = input("Enter times_shown filter (none, exact_value, or comma-separated values): ")
    if times_shown_filter.lower() != "none":
        try:
            if "," in times_shown_filter:  # Multiple values
                allowed_times = set(map(int, times_shown_filter.split(",")))
                filtered_data = {
                    k: v for k, v in filtered_data.items()
                    if v['times_shown'] in allowed_times
                }
            else:  # Single value
                exact_times_shown = int(times_shown_filter)
                filtered_data = {
                    k: v for k, v in filtered_data.items()
                    if v["times_shown"] == exact_times_shown
                }
        except (ValueError, TypeError):
            print("Error: Invalid times_shown filter format.")
            return

    # فلترة بناءً على tags
    tag_filter = input("Enter tag filter (none, exact tag, or comma-separated tags): ")
    if tag_filter.lower() != "none":
        # تحويل التاغات المُدخلة إلى قائمة مع إزالة الفراغات الزائدة
        allowed_tags = [tag.strip() for tag in tag_filter.split(",")]
        filtered_data = {
            k: v for k, v in filtered_data.items()
            if any(tag in [t.strip() for t in v.get("tags", "").split(",") if t] for tag in allowed_tags)
        }

    # فلترة بناءً على win_rate
    win_rate_filter = input("Enter win_rate filter (none, exact_value, min-max, min1-max1,min2-max2): ")
    if win_rate_filter.lower() != "none":
        try:
            if "," in win_rate_filter:  # Multiple ranges
                ranges = win_rate_filter.split(",")
                valid_ranges = []
                for r in ranges:
                    min_val, max_val = map(float, r.split("-"))
                    valid_ranges.append((min_val, max_val))
                filtered_data = {
                    k: v for k, v in filtered_data.items()
                    if any(min_val <= v['win_rate'] <= max_val for min_val, max_val in valid_ranges)
                }
            elif "-" in win_rate_filter:  # Single range
                min_val, max_val = map(float, win_rate_filter.split("-"))
                filtered_data = {
                    k: v for k, v in filtered_data.items()
                    if min_val <= v['win_rate'] <= max_val
                }
            else:  # Exact value
                exact_win_rate = float(win_rate_filter)
                filtered_data = {
                    k: v for k, v in filtered_data.items()
                    if v['win_rate'] == exact_win_rate
                }
        except (ValueError, TypeError):
            print("Error: Invalid win_rate filter format.")
            return

    output_file = "filtered_" + data_file
    with open(output_file, 'w') as outfile:
        json.dump(filtered_data, outfile, indent=4)

    print(f"Filtered data saved to: {output_file}")

if __name__ == '__main__':
    data_file = input("Enter the name of the JSON data file (e.g., data.json): ")
    filter_videos(data_file)