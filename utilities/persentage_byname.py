import json
import sys
import re

def categorize_videos(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    less_than_1000 = 0
    equal_1000 = 0
    greater_than_1000 = 0
    total_videos = 0

    for entry in data:
        for video in entry.get("videos", []):
            match = re.match(r"^(\d+)_", video)
            if match:
                num = int(match.group(1))
                total_videos += 1
                if num < 1000:
                    less_than_1000 += 1
                elif num == 1000:
                    equal_1000 += 1
                else:
                    greater_than_1000 += 1

    def percentage(count):
        return f"{(count / total_videos * 100):.2f}%" if total_videos > 0 else "0.00%"

    print(f"Videos < 1000: {less_than_1000} ({percentage(less_than_1000)})")
    print(f"Videos = 1000: {equal_1000} ({percentage(equal_1000)})")
    print(f"Videos > 1000: {greater_than_1000} ({percentage(greater_than_1000)})")
    print(f"Total videos: {total_videos}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py path/to/file.json")
        sys.exit(1)

    categorize_videos(sys.argv[1])
