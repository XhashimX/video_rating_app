import os

folder = r"C:\Users\Stark\Download\myhome\video_rating_app\sd-danbooru-tags\dan"
output_file = os.path.join(folder, "combined.txt")

with open(output_file, "w", encoding="utf-8") as outfile:
    for file in sorted(os.listdir(folder)):
        if file.endswith(".txt"):
            outfile.write(f"\n# {file}\n")
            with open(os.path.join(folder, file), "r", encoding="utf-8") as infile:
                outfile.write(infile.read() + "\n")
print("Done! All files are combined in", output_file)
