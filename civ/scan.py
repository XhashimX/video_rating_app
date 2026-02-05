import os
import subprocess
import json
import shutil
import time
import re
from pathlib import Path

# --- إعدادات المسارات ---
BASE_DIR = Path("C:/Users/Stark").resolve()

# المجلدات
DOWNLOAD_FOLDER = BASE_DIR / "Downloads"
DIB_FOLDER = Path(r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\Dib")
EXTRA_SCAN_FOLDER = BASE_DIR / "Desktop/Extra_Scan"

# ملفات الكاش
SCRIPT_DIR = Path(__file__).parent
MAIN_CACHE_FILE = SCRIPT_DIR / "image_cache.json"
SUBFOLDER_CACHE_FILE = SCRIPT_DIR / "subfolder_cache.json"

# --- دوال التنظيف ---

def clean_comfy_text(text):
    """تنظيف النص من الرموز الزائدة"""
    if not isinstance(text, str): return ""
    text = text.strip()
    # إزالة الأقواس المزدوجة إذا كانت تحيط بالنص كاملاً
    if text.startswith('"') and text.endswith('"'): text = text[1:-1]
    # إزالة الفواصل الفارغة من البداية والنهاية
    while text.startswith(','): text = text[1:].strip()
    while text.endswith(','): text = text[:-1].strip()
    # تنظيف الفواصل المتكررة
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r'\s+', ' ', text) # إزالة المسافات الزائدة
    return text.strip()

# --- دوال مساعدة للتحليل الذكي ---

def extract_text_from_node(node, all_nodes, visited=None):
    """استخراج النص من عقدة، مع تتبع المراجع ومنع التكرار اللانهائي"""
    if visited is None:
        visited = set()
    
    if not isinstance(node, dict):
        return ""
    
    # منع التكرار اللانهائي
    node_id = id(node)
    if node_id in visited:
        return ""
    visited.add(node_id)
    
    inputs = node.get('inputs', {})
    
    # 1. جرب text مباشر
    if 'text' in inputs:
        if isinstance(inputs['text'], str):
            return clean_comfy_text(inputs['text'])
        elif isinstance(inputs['text'], list) and len(inputs['text']) > 0:
            ref_str = str(inputs['text'][0])
            # جرب المفتاح الكامل أولاً (مثل "51:0")
            ref_node = all_nodes.get(ref_str)
            # إذا لم نجد، جرب بدون :
            if not ref_node and ':' in ref_str:
                ref_node = all_nodes.get(ref_str.split(':')[0])
            
            if ref_node:
                return extract_text_from_node(ref_node, all_nodes, visited)
    
    # 2. جرب widgets_values
    if isinstance(node.get('widgets_values'), list) and len(node['widgets_values']) > 0:
        widget_text = node['widgets_values'][0]
        if isinstance(widget_text, str) and widget_text:
            return clean_comfy_text(widget_text)
    
    return ""

def parse_comfyui_metadata(exif_data):
    """
    تحليل بيانات ComfyUI بنهج ذكي يتبع KSampler
    
    التحسينات v3.0:
    - يتبع سلسلة positive/negative من KSampler لاختيار البرومبت الصحيح
    - دعم JSON مباشر وبادئة "Prompt:"
    - معالجة محسنة للمراجع (node_id و node_id:output_index)
    - استخراج كامل للإعدادات والموديل
    """
    pos_prompt = ""
    neg_prompt = ""
    model_name = "ComfyUI_Model"
    settings = {}
    
    # استخراج JSON
    raw_json = None
    if 'Make' in exif_data:
        make_content = str(exif_data['Make'])
        if make_content.startswith('Prompt:'):
            raw_json = make_content[7:]
        elif make_content.startswith('{'):
            raw_json = make_content
    
    if not raw_json and 'UserComment' in exif_data:
        raw_json = exif_data['UserComment']

    if not raw_json:
        return "", model_name

    try:
        data = json.loads(raw_json)
        
        # تحويل nodes إلى dict إذا لزم الأمر
        nodes = {}
        if isinstance(data, dict):
            if 'nodes' in data and isinstance(data['nodes'], list):
                for n in data['nodes']:
                    nodes[str(n.get('id', ''))] = n
            else:
                nodes = data
        
        # ============== النهج الذكي: تتبع من KSampler ==============
        ksampler_found = False
        
        # 1. ابحث عن KSampler
        for node_id, node_data in nodes.items():
            if not isinstance(node_data, dict):
                continue
                
            class_type = str(node_data.get('class_type', '')).lower()
            if 'ksampler' in class_type:
                ksampler_found = True
                inputs = node_data.get('inputs', {})
                
                # استخرج الإعدادات
                if 'seed' in inputs and isinstance(inputs['seed'], (int, float)):
                    settings['Seed'] = int(inputs['seed'])
                if 'steps' in inputs and isinstance(inputs['steps'], (int, float)):
                    settings['Steps'] = int(inputs['steps'])
                if 'cfg' in inputs and isinstance(inputs['cfg'], (int, float)):
                    settings['CFG scale'] = float(inputs['cfg'])
                if 'sampler_name' in inputs and isinstance(inputs['sampler_name'], str):
                    settings['Sampler'] = inputs['sampler_name']
                if 'scheduler' in inputs and isinstance(inputs['scheduler'], str):
                    settings['Scheduler'] = inputs['scheduler']
                if 'denoise' in inputs and isinstance(inputs['denoise'], (int, float)):
                    settings['Denoising strength'] = float(inputs['denoise'])
                
                # تتبع positive
                if 'positive' in inputs and isinstance(inputs['positive'], list) and len(inputs['positive']) > 0:
                    pos_node_id = str(inputs['positive'][0])
                    pos_node = nodes.get(pos_node_id)
                    if pos_node:
                        pos_prompt = extract_text_from_node(pos_node, nodes)
                
                # تتبع negative
                if 'negative' in inputs and isinstance(inputs['negative'], list) and len(inputs['negative']) > 0:
                    neg_node_id = str(inputs['negative'][0])
                    neg_node = nodes.get(neg_node_id)
                    if neg_node:
                        neg_prompt = extract_text_from_node(neg_node, nodes)
                
                break  # وجدنا KSampler، لا حاجة للبحث أكثر
        
        # ============== النهج الاحتياطي: إذا لم نجد KSampler ==============
        if not ksampler_found:
            print("⚠️  لم يتم العثور على KSampler، استخدام النهج الاحتياطي")
            pos_candidates = []
            neg_candidates = []
            negative_keywords = [
                'lowres', 'worst quality', 'bad quality', 'bad anatomy', 'nsfw', 
                'watermark', 'jpeg artifacts', 'error', 'username', 'signature', 
                'censored', 'bar_censor', 'pregnant', 'chibi', 'loli', 
                'simple background', 'conjoined', 'futanari', 'sketch', 'old', 'oldest'
            ]
            
            for node_id, node_data in nodes.items():
                if not isinstance(node_data, dict):
                    continue
                
                text = extract_text_from_node(node_data, nodes)
                if text and len(text) > 2 and "[filename]" not in text and "TextBatch" not in text:
                    # تصنيف
                    neg_count = sum(1 for kw in negative_keywords if kw in text.lower())
                    starts_with_negative = any(text.lower().startswith(kw) for kw in ['lowres', 'worst quality', 'bad quality'])
                    
                    if neg_count >= 3 or starts_with_negative:
                        neg_candidates.append(text)
                    else:
                        pos_candidates.append(text)
            
            # اختر الأفضل
            if pos_candidates:
                unique_pos = list(set(pos_candidates))
                # أفضل نص = الأطول بعد إزالة الفواصل
                pos_prompt = max(unique_pos, key=lambda x: len(x.replace(',', '').replace(' ', '')))
            
            if neg_candidates:
                unique_neg = list(set(neg_candidates))
                neg_prompt = ", ".join(unique_neg)
        
        # ============== استخراج الموديل والأبعاد ==============
        for node_id, node_data in nodes.items():
            if not isinstance(node_data, dict):
                continue
            
            class_type = str(node_data.get('class_type', '')).lower()
            inputs = node_data.get('inputs', {})
            
            # الموديل
            if 'checkpoint' in class_type and 'ckpt_name' in inputs:
                model_name = inputs['ckpt_name']
            
            # الأبعاد
            if 'latent' in class_type and 'width' in inputs and 'height' in inputs:
                if isinstance(inputs['width'], (int, float)) and isinstance(inputs['height'], (int, float)):
                    settings['Size'] = f"{int(inputs['width'])}x{int(inputs['height'])}"
        
    except (json.JSONDecodeError, AttributeError, KeyError) as e:
        print(f"❌ خطأ في تحليل بيانات ComfyUI: {e}")
        return "", "ComfyUI_Model"
    
    # ============== تجميع النتيجة النهائية ==============
    parts = []
    
    if pos_prompt:
        parts.append(pos_prompt)
    
    if neg_prompt:
        parts.append(f"Negative prompt: {neg_prompt}")
    
    if settings:
        settings_list = []
        order = ['Steps', 'CFG scale', 'Sampler', 'Scheduler', 'Seed', 'Size', 'Denoising strength']
        for key in order:
            if key in settings:
                settings_list.append(f"{key}: {settings[key]}")
        
        for k, v in settings.items():
            if k not in order:
                settings_list.append(f"{k}: {v}")
        
        if model_name != "ComfyUI_Model":
            settings_list.append(f"Model: {model_name}")
        
        if parts:
            parts.append("")
        parts.append(", ".join(settings_list))
    
    return "\n".join(parts), model_name


# --- باقي الكود كما هو ---

def extract_image_info(exif_data):
    model_name = "غير معروف"
    prompt_data = ""

    # 1. ComfyUI Logic
    is_comfy = False
    if 'Make' in exif_data:
        make_content = str(exif_data['Make'])
        if make_content.startswith('Prompt:') or make_content.startswith('{'):
            is_comfy = True
    elif 'ImageDescription' in exif_data and str(exif_data['ImageDescription']).startswith('Workflow:'):
        is_comfy = True
        
    if is_comfy:
        p_text, m_name = parse_comfyui_metadata(exif_data)
        if p_text: prompt_data = p_text
        if m_name: model_name = m_name
        
    # 2. A1111 Logic
    elif 'UserComment' in exif_data or 'Parameters' in exif_data:
        text = exif_data.get('UserComment', '') or exif_data.get('Parameters', '')
        prompt_data = text
        match = re.search(r'Model: ([^,]+)', text)
        if match: model_name = match.group(1)

    return model_name, prompt_data


def find_images_with_exiftool(folder_path, extensions, check_ai_tag=False):
    print(f"🔎 البحث في: {folder_path}")
    command = ['exiftool', '-json']
    command.extend(['-Make', '-ImageDescription', '-UserComment', '-Parameters', '-SourceFile', '-Directory', '-FileName', '-FileModifyDate'])
    
    for ext in extensions:
        clean_ext = ext.replace('.', '')
        command.extend(['-ext', clean_ext])
    
    command.append(str(folder_path))
    
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace'
        )
        if not result.stdout: return []
        data = json.loads(result.stdout)
        return data if isinstance(data, list) else [data]
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return []

def process_image_list(image_data_list, source_group_name="Main"):
    images_to_process = []
    for item in image_data_list:
        file_path = Path(item.get('SourceFile'))
        model_name, prompt_data = extract_image_info(item)
        source = item.get('_source_group', source_group_name)
        
        try:
            if file_path.is_relative_to(BASE_DIR):
                relative_path = file_path.relative_to(BASE_DIR)
                images_to_process.append({
                    'name': file_path.name,
                    'relative_path': str(relative_path).replace('\\', '/'),
                    'mod_time': item.get('FileModifyDate', ''),
                    'model_name': model_name,
                    'prompt_data': prompt_data,
                    'source_group': source
                })
        except: continue
    
    images_to_process.reverse() 
    return images_to_process

def scan_and_cache_images():
    start_time = time.time()
    print("--- بدء عملية الفحص الذكي (ComfyUI v3.0 + A1111) ---")

    if not shutil.which("exiftool"):
        print("\n❌ خطأ: exiftool غير موجود. يرجى إضافته لمسار النظام.")
        return

    main_ai_images_raw = []
    supported_extensions = ['.png', '.jpg', '.jpeg', '.webp']

    # 1. Download
    if DOWNLOAD_FOLDER.is_dir():
        print(f"📁 فحص مجلد التحميل...")
        images = find_images_with_exiftool(DOWNLOAD_FOLDER, supported_extensions)
        ai_images = []
        for img in images:
            if 'Make' in img or 'ImageDescription' in img or 'UserComment' in img or 'Parameters' in img:
                 img['_source_group'] = 'Download'
                 ai_images.append(img)
        main_ai_images_raw.extend(ai_images)

    # 2. Dib
    if DIB_FOLDER.is_dir():
        print(f"📁 فحص مجلد Dib...")
        images = find_images_with_exiftool(DIB_FOLDER, supported_extensions)
        for img in images: img['_source_group'] = 'Dib'
        main_ai_images_raw.extend(images)

    # 3. Extra
    if EXTRA_SCAN_FOLDER.is_dir():
        print(f"📁 فحص المجلد الإضافي...")
        images = find_images_with_exiftool(EXTRA_SCAN_FOLDER, supported_extensions)
        for img in images: img['_source_group'] = 'Extra'
        main_ai_images_raw.extend(images)

    if main_ai_images_raw:
        final_list_processed = process_image_list(main_ai_images_raw)
        
        with open(MAIN_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_list_processed, f, ensure_ascii=False, indent=4)
        print(f"💾 تم حفظ {len(final_list_processed)} صورة في الكاش الرئيسي.")
    else:
        with open(MAIN_CACHE_FILE, 'w', encoding='utf-8') as f: json.dump([], f)
        print("🟡 لم يتم العثور على صور.")

    with open(SUBFOLDER_CACHE_FILE, 'w', encoding='utf-8') as f: json.dump({}, f)
    
    print(f"\n--- ✅ تم الفحص في {time.time() - start_time:.2f} ثانية ---")

if __name__ == '__main__':
    scan_and_cache_images()