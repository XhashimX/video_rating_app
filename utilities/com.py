import json
import sys


def load_json(file_path):
    """تحميل ملف JSON."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def save_json(data, file_path):
    """حفظ بيانات JSON إلى ملف."""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def compare_and_correct(first_file_data, second_file_data):
    """مقارنة الملفين وتصحيح البيانات في الملف الثاني."""
    corrected_data = []

    first_file_lookup = {
        video_data['file_size']: video_name for video_name,
        video_data in first_file_data.items()}

    for entry in second_file_data:
        new_entry = entry.copy()  # نسخ الإدخال لتجنب التعديل المباشر على الملف الثاني
        videos = entry['videos']
        ratings = entry['rating']
        file_sizes = entry['file_size']

        for i, file_size in enumerate(file_sizes):
            if file_size in first_file_lookup:
                video_name = first_file_lookup[file_size]
                video_data = first_file_data[video_name]

                new_entry['videos'][i] = video_name

                if ratings[i] != video_data['rating']:
                    new_entry['rating'][i] = video_data['rating']

        corrected_data.append(new_entry)

    return corrected_data


def main():
    if len(sys.argv) != 4:
        print("Usage: python compare.py first_file.json second_file.json output_file.json")
        sys.exit(1)

    first_file_path = sys.argv[1]
    second_file_path = sys.argv[2]
    output_file_path = sys.argv[3]

    first_file_data = load_json(first_file_path)
    second_file_data = load_json(second_file_path)

    corrected_data = compare_and_correct(first_file_data, second_file_data)

    save_json(corrected_data, output_file_path)
    print(f"Data has been successfully saved to {output_file_path}")


if __name__ == "__main__":
    main()
