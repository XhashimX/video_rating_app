import os
import json
import re

# paths
folder_path = "C:/Users/Stark/Download/myhome/video_rating_app/NS/TikTok/Elo tik/A1000 elo tik"
json_path = "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json"
unknown_file = "Unknown.txt"
id_file = "Id.txt"

# load JSON data
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# prepare output files
with open(unknown_file, "w", encoding="utf-8") as unk_f, \
     open(id_file, "w", encoding="utf-8") as id_f:

    for fname in os.listdir(folder_path):
        # skip non-files
        full = os.path.join(folder_path, fname)
        if not os.path.isfile(full):
            continue

        entry = data.get(fname, {})
        name_field = entry.get("name", "")

        if name_field:  # has a value, skip
            continue

        m = re.search(r"(\d{19})", fname)
        if m:
            id_f.write(m.group(1) + "\n")
        else:
            unk_f.write(fname + "\n")