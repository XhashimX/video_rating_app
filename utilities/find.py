import sys
import json
import re
import os


def parse_sorted_file(sorted_file):
    """
    تحليل الملف النصي المستخرج سابقًا للحصول على ترتيب الفيديوهات.
    """
    video_rankings = {}
    try:
        with open(sorted_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        print(f"Error reading sorted file {sorted_file}: {e}")
        sys.exit(1)

    if not content:
        return video_rankings

    blocks = content.split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        match = re.match(r"(\d+)\.", lines[0].strip())
        if not match:
            continue
        rank = int(match.group(1))

        video_line = lines[1].strip()
        if video_line.startswith("Video Name:"):
            video_name = video_line.replace("Video Name:", "", 1).strip()
            video_rankings[video_name] = rank
    return video_rankings


def extract_tournament_videos(tournament_data, tournament_name):
    """
    استخراج أسماء الفيديوهات الفائزة من البطولة المطلوبة.
    """
    if tournament_name not in tournament_data:
        print(f"Tournament '{tournament_name}' not found in the database.")
        sys.exit(1)

    tournament = tournament_data[tournament_name]
    winners = {}

    for key in tournament:
        if key.startswith("top") and isinstance(tournament[key], dict):
            video_name = tournament[key].get("video")
            ranking = tournament[key].get("ranking", "Unknown")
            if video_name:
                winners[video_name] = ranking

    return winners


def main():
    if len(sys.argv) != 4:
        print("Usage: python compare_tournament.py <tournament_file.json> <sorted_file.txt> <tournament_name>")
        sys.exit(1)

    tournament_file = sys.argv[1]
    sorted_file = sys.argv[2]
    tournament_name = sys.argv[3]

    try:
        with open(tournament_file, 'r', encoding='utf-8') as f:
            tournament_data = json.load(f)
    except Exception as e:
        print(f"Error reading tournament file {tournament_file}: {e}")
        sys.exit(1)

    tournament_winners = extract_tournament_videos(
        tournament_data, tournament_name)

    sorted_videos = parse_sorted_file(sorted_file)

    output_lines = []
    for video, tournament_rank in tournament_winners.items():
        sorted_rank = sorted_videos.get(video, "Not found")
        output_lines.append(f"Video: {video}")
        output_lines.append(f"  - Tournament Ranking: {tournament_rank}")
        output_lines.append(f"  - Sorted File Ranking: {sorted_rank}")
        output_lines.append("")  # سطر فارغ للفصل بين الإدخالات

    output_content = "\n".join(output_lines)

    output_file = f"comparison_{tournament_name.replace(' ', '_')}.txt"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)
        print(f"Comparison results saved to {output_file}")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")


if __name__ == "__main__":
    main()
