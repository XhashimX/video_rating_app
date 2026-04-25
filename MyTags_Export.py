import json
import re

file1_path = r"C:\Users\Stark\Downloads\GoogleLabs_MyTags_Export (5).js"
file2_path = r"C:\Users\Stark\Downloads\GoogleLabs_MyTags_Export (6).js"
output_path = r"C:\Users\Stark\Downloads\GoogleLabs_MyTags_Merged.js"

def extract_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # البحث عن الكائن بين أقواس البداية والنهاية
        match = re.search(r'const\s+MY_TAGS_INITIAL\s*=\s*(\{.*?\});', content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return None

data1 = extract_json(file1_path)
data2 = extract_json(file2_path)

if not data1 or not data2:
    print("❌ فشل في قراءة أو تحليل الملفات.")
    exit()

merged_data = {}
all_keys = set(data1.keys()).union(set(data2.keys()))

for key in all_keys:
    merged_data[key] =[]
    seen_tags = set()
    
    # دمج عناصر الملف الأول
    if key in data1:
        for item in data1[key]:
            tag = item.get("tag", "")
            if tag not in seen_tags:
                merged_data[key].append(item)
                seen_tags.add(tag)
                
    # دمج عناصر الملف الثاني
    if key in data2:
        for item in data2[key]:
            tag = item.get("tag", "")
            if tag not in seen_tags:
                merged_data[key].append(item)
                seen_tags.add(tag)

# إنشاء الملف المدمج الجديد
with open(output_path, 'w', encoding='utf-8') as f:
    f.write("// تم الدمج بواسطة السكريبت\n")
    f.write("const MY_TAGS_INITIAL = ")
    json.dump(merged_data, f, ensure_ascii=False, indent=4)
    f.write(";\n")

print(f"✅ تم دمج الملفات بنجاح في:\n{output_path}")