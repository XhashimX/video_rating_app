import json
import sys
import os


def main():
    if len(sys.argv) != 2:
        print("Usage: python sort_videos.py <data_file>")
        sys.exit(1)

    data_file = sys.argv[1]

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {data_file}: {e}")
        sys.exit(1)

    records = []
    if isinstance(data, list):
        for entry in data:
            videos = entry.get("videos", [])
            ratings = entry.get("rating", [])
            file_sizes = entry.get("file_size", [])
            for video, rating, file_size in zip(videos, ratings, file_sizes):
                records.append({
                    "video": video,
                    "rating": rating,
                    "file_size": file_size
                })
    else:
        print("The JSON structure is not a list.")
        sys.exit(1)

    sorted_records = sorted(records, key=lambda x: x["rating"], reverse=True)

    output_lines = []
    for idx, record in enumerate(sorted_records, start=1):
        output_lines.append(f"{idx}.")
        output_lines.append(f"Video Name: {record['video']}")
        output_lines.append(f"File Size: {record['file_size']}")
        output_lines.append(f"Rating: {record['rating']}")
        output_lines.append("")  # Blank line for separation

    output_content = "\n".join(output_lines)

    base_name = os.path.basename(data_file)
    output_file = os.path.join(os.path.dirname(data_file), f"rate_{base_name}")

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)
        print(f"Output saved to {output_file}")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")


if __name__ == "__main__":
    main()
