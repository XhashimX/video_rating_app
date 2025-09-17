import json
import sys

def extract_sizes_from_first_file(filename):
    sizes = []
    with open(filename, encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"خطأ في قراءة JSON من {filename}: {e}")
            sys.exit(1)
    # الملف الأول عبارة عن قائمة من القواميس، نأخذ القيم من المفتاح "file_size"
    for entry in data:
        file_sizes = entry.get("file_size", [])
        sizes.extend(file_sizes)
    return sizes

def count_matches_by_size(filename, sizes_list):
    count = 0
    with open(filename, encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"خطأ في قراءة JSON من {filename}: {e}")
            return 0
    # الملف الثاني عبارة عن قاموس والمفاتيح هي أسماء ملفات الفيديو
    for info in data.values():
        fs = info.get("file_size")
        if fs in sizes_list:
            count += 1
    return count

def main():
    if len(sys.argv) < 3:
        print("Usage: python script.py first_file.json other_file1.json [other_file2.json ...]")
        sys.exit(1)
    
    first_file = sys.argv[1]
    other_files = sys.argv[2:]
    
    sizes_list = extract_sizes_from_first_file(first_file)
    total_sizes = len(sizes_list)
    
    print(f"إجمالي الأحجام المستخرجة: {total_sizes}\n")
    
    for file in other_files:
        match_count = count_matches_by_size(file, sizes_list)
        percentage = (match_count / total_sizes * 100) if total_sizes else 0
        print(f"الملف: {file}")
        print(f"  عدد الأحجام المطابقة: {match_count}")
        print(f"  النسبة المئوية: {percentage:.2f}%\n")

if __name__ == "__main__":
    main()
