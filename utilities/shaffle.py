import json
import random
import argparse  # استيراد وحدة argparse


def load_data(input_file):
    """
    قراءة بيانات المنافسات من ملف JSON.
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def extract_video_entries(data):
    """
    استخراج كافة بيانات الفيديو من المنافسات.
    لكل منافسة، يتم استخراج كل فيديو مع تقييمه وحجم الملف.
    """
    video_entries = []
    for comp in data:
        videos = comp.get("videos", [])
        ratings = comp.get("rating", [])
        file_sizes = comp.get("file_size", [])
        for i in range(len(videos)):
            video_entries.append({
                "video": videos[i],
                "rating": ratings[i] if i < len(ratings) else None,
                "file_size": file_sizes[i] if i < len(file_sizes) else None
            })
    return video_entries


def create_new_competitions(video_entries, default_comp_properties):
    """
    يقوم بتجميع الفيديوهات على شكل مباريات (زوج من الفيديوهات)
    وينشئ قائمة جديدة من المنافسات.
    """
    if len(video_entries) % 2 != 0:
        print("عدد الفيديوهات فردي؛ سيتم تجاهل آخر فيديو.")
        video_entries = video_entries[:-1]

    new_comps = []
    for i in range(0, len(video_entries), 2):
        comp = {}
        comp["videos"] = [video_entries[i]["video"],
                          video_entries[i + 1]["video"]]
        comp["rating"] = [video_entries[i]["rating"],
                          video_entries[i + 1]["rating"]]
        comp["file_size"] = [video_entries[i]["file_size"],
                             video_entries[i + 1]["file_size"]]
        comp.update(default_comp_properties)
        new_comps.append(comp)
    return new_comps


def main():
    parser = argparse.ArgumentParser(
        description="معالجة ملف JSON لإنشاء منافسات جديدة.")
    parser.add_argument("input_file", help="اسم ملف JSON للإدخال")
    args = parser.parse_args()

    input_file = args.input_file  # الحصول على اسم الملف من arguments

    data = load_data(input_file)

    default_comp_properties = {}
    if data and isinstance(data, list) and len(data) > 0:
        for key, value in data[0].items():
            if key not in ["videos", "rating", "file_size"]:
                default_comp_properties[key] = value

    video_entries = extract_video_entries(data)

    random.shuffle(video_entries)

    new_competitions = create_new_competitions(
        video_entries, default_comp_properties)

    print(json.dumps(new_competitions, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
