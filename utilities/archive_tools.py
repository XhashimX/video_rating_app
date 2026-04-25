import os
import json
import re
import random

ARCHIVE_FILE = os.path.join('utilities', 'tournamentarchive.json')
UTILITIES_DIR = 'utilities'


def load_archive():
    try:
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading archive: {e}")
        return {}


def get_tournament_rating(tournament_id):
    """Extract the trailing rating/number from a tournament ID like '80.topcut_..._1172'."""
    match = re.search(r'_(\d+)$', tournament_id)
    if match:
        return int(match.group(1))
    return None


def filter_tournaments_by_name(archive, query):
    """
    Filter tournaments by name.
    The character 'x' acts as a single-character wildcard (matches any one character).
    """
    query = query.strip()
    if not query:
        return dict(archive)

    # Escape all regex special characters in the query
    escaped = re.escape(query)
    # After escaping, literal 'x' stays as 'x'. Replace it with '.' (any single char).
    # re.escape turns a space into '\ ', a dot into '\.', etc.
    # 'x' is not a special regex char so it stays as 'x' after escaping.
    pattern = escaped.replace('x', '.')

    result = {}
    for tid, tdata in archive.items():
        if re.search(pattern, tid, re.IGNORECASE):
            result[tid] = tdata
    return result


def filter_tournaments_by_ratings(archive, ratings_query):
    """
    Filter tournaments by their trailing rating number.

    Supported formats:
      - Exact:   "2050,3442,5424"     → matches _2050, _3442, _5424
      - Range:   "1111-1122"          → matches numbers from 1111 to 1122 inclusive
      - Mixed:   "1111-1122,2333-2345,5000"
    """
    ratings_query = ratings_query.strip()
    if not ratings_query:
        return dict(archive)

    exact_values = set()
    ranges = []

    for part in ratings_query.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            sub = part.split('-', 1)
            try:
                low = int(sub[0].strip())
                high = int(sub[1].strip())
                ranges.append((min(low, high), max(low, high)))
            except ValueError:
                pass
        else:
            try:
                exact_values.add(int(part))
            except ValueError:
                pass

    result = {}
    for tid, tdata in archive.items():
        rating = get_tournament_rating(tid)
        if rating is None:
            continue
        if rating in exact_values:
            result[tid] = tdata
            continue
        for low, high in ranges:
            if low <= rating <= high:
                result[tid] = tdata
                break

    return result


def load_elo_files():
    """
    Scan all elo_videos_*.json files in utilities/ and build a lookup:
      file_size (int) -> name (str)
    """
    size_to_name = {}
    try:
        for fname in os.listdir(UTILITIES_DIR):
            if fname.startswith('elo_videos_') and fname.endswith('.json'):
                fpath = os.path.join(UTILITIES_DIR, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for video_key, info in data.items():
                        if isinstance(info, dict):
                            fs = info.get('file_size')
                            name = info.get('name', '').strip()
                            if fs and name:
                                size_to_name[fs] = name
                except Exception as e:
                    print(f"Warning: Could not load elo file {fname}: {e}")
    except Exception as e:
        print(f"Error scanning utilities directory: {e}")
    return size_to_name


def extract_videos_from_selected(selected_ids, archive, top_levels, smart_match, size_to_name):
    """
    Extract video data from selected tournament IDs.

    Args:
        selected_ids:  list of tournament ID strings
        archive:       full archive dict
        top_levels:    list of ints like [1], [1,2], [1,2,3,4]
                       OR the string 'all' to include every position
        smart_match:   if True, also pull in videos from non-selected positions
                       when they share the same 'name' as a selected video
        size_to_name:  dict mapping file_size -> name (from elo files)

    Returns:
        list of dicts: [{'video': str, 'rating': float, 'file_size': int}, ...]
    """
    ALL_POSITIONS = ['top1', 'top2', 'top3', 'top4']

    if top_levels == 'all':
        selected_positions = ALL_POSITIONS
        check_positions = []
    else:
        selected_positions = [f'top{n}' for n in top_levels]
        check_positions = [p for p in ALL_POSITIONS if p not in selected_positions]

    extracted = []

    for tid in selected_ids:
        if tid not in archive:
            continue
        tdata = archive[tid]

        selected_names_this_tournament = set()

        # Step 1: collect videos from the chosen positions
        for pos in selected_positions:
            vdata = tdata.get(pos)
            if not vdata or not vdata.get('video'):
                continue

            video = vdata['video']
            rating = vdata.get('new_rating') or vdata.get('old_rating') or 1000.0
            file_size = vdata.get('file_size')

            extracted.append({
                'video': video,
                'rating': rating,
                'file_size': file_size
            })

            # Record the name for smart matching
            if smart_match and file_size and file_size in size_to_name:
                name = size_to_name[file_size]
                if name:
                    selected_names_this_tournament.add(name)

        # Step 2: smart match — check remaining positions
        if smart_match and selected_names_this_tournament and check_positions:
            for pos in check_positions:
                vdata = tdata.get(pos)
                if not vdata or not vdata.get('video'):
                    continue

                file_size = vdata.get('file_size')
                if not file_size:
                    continue

                name = size_to_name.get(file_size, '')
                if name and name in selected_names_this_tournament:
                    video = vdata['video']
                    rating = vdata.get('new_rating') or vdata.get('old_rating') or 1000.0
                    extracted.append({
                        'video': video,
                        'rating': rating,
                        'file_size': file_size
                    })

    return extracted


def create_tournament_files(videos, file_prefix, start_num, step, num_files, num_videos_per_match, ranking_type):
    """
    Shuffle the video list, split into num_files chunks, and build tournament match lists.

    Returns:
        dict mapping filename (str) -> list of match dicts
    """
    # Shuffle all videos randomly before distributing
    shuffled = list(videos)
    random.shuffle(shuffled)

    total = len(shuffled)
    num_files = max(1, num_files)

    # Ceiling division: spread videos as evenly as possible
    chunk_size = (total + num_files - 1) // num_files

    result_files = {}

    for file_idx in range(num_files):
        chunk_start = file_idx * chunk_size
        chunk_end = min(chunk_start + chunk_size, total)
        chunk = shuffled[chunk_start:chunk_end]

        if not chunk:
            break

        # Build matches from this chunk
        matches = []
        i = 0
        while i < len(chunk):
            group = chunk[i:i + num_videos_per_match]

            # Pad the last group with empty slots if it's smaller than num_videos_per_match
            while len(group) < num_videos_per_match:
                group.append({'video': '', 'rating': None, 'file_size': None})

            match = {
                "videos": [v['video'] for v in group],
                "rating": [v['rating'] for v in group],
                "file_size": [v['file_size'] for v in group],
                "mode": 1,
                "num_videos": num_videos_per_match,
                "ranking_type": ranking_type,
                "competition_type": "balanced_random"
            }
            matches.append(match)
            i += num_videos_per_match

        file_number = start_num + file_idx * step
        filename = f"{file_prefix}{file_number}.json"
        result_files[filename] = matches

    return result_files


def save_tournament_files(result_files):
    """
    Write each file in result_files to the utilities/ directory.

    Returns:
        list of successfully saved filenames
    """
    saved = []
    for filename, matches in result_files.items():
        filepath = os.path.join(UTILITIES_DIR, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(matches, f, indent=4, ensure_ascii=False)
            saved.append(filename)
            print(f"Saved tournament file: {filepath}")
        except Exception as e:
            print(f"Error saving {filename}: {e}")
    return saved


def export_file_sizes(videos, output_filename):
    """
    Write one file_size per line to a text file in utilities/.

    Returns:
        (success: bool, path_or_error: str)
    """
    filepath = os.path.join(UTILITIES_DIR, output_filename)
    sizes = [str(v['file_size']) for v in videos if v.get('file_size')]
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sizes))
        return True, filepath
    except Exception as e:
        return False, str(e)


def preview_filenames(file_prefix, start_num, step, num_files):
    """Return a list of preview filenames (for display in the UI)."""
    names = []
    for i in range(num_files):
        num = start_num + i * step
        names.append(f"{file_prefix}{num}.json")
    return names


def count_videos_preview(selected_ids, archive, top_levels):
    """
    Count how many non-empty videos exist across selected tournaments
    for each position (top1..top4).

    Returns a dict:
    {
        'total': int,
        'by_position': {'top1': int, 'top2': int, 'top3': int, 'top4': int},
        'per_tournament': [
            {
                'id': str,
                'top1': bool,   # True = has a non-empty video
                'top2': bool,
                'top3': bool,
                'top4': bool,
                'count': int    # how many non-empty positions will be extracted
            },
            ...
        ]
    }
    """
    ALL_POSITIONS = ['top1', 'top2', 'top3', 'top4']

    if top_levels == 'all':
        selected_positions = ALL_POSITIONS
    else:
        selected_positions = [f'top{n}' for n in top_levels]

    by_position = {p: 0 for p in ALL_POSITIONS}
    per_tournament = []
    total = 0

    for tid in selected_ids:
        if tid not in archive:
            continue
        tdata = archive[tid]
        row = {'id': tid, 'top1': False, 'top2': False, 'top3': False, 'top4': False, 'count': 0}

        # First scan ALL positions to show what exists (for the diagnostic display)
        for pos in ALL_POSITIONS:
            vdata = tdata.get(pos)
            has_video = bool(vdata and vdata.get('video', '').strip())
            row[pos] = has_video

        # Then count only what will actually be extracted
        for pos in selected_positions:
            vdata = tdata.get(pos)
            if vdata and vdata.get('video', '').strip():
                by_position[pos] += 1
                row['count'] += 1
                total += 1

        per_tournament.append(row)

    return {
        'total': total,
        'by_position': by_position,
        'per_tournament': per_tournament,
        'selected_positions': selected_positions,
    }