import os
import requests
import json
import uuid
import time # --- إضافة جديدة: استيراد مكتبة time ---
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, send_from_directory
import logging

# --- إعداد logging ---
# يمكنك تعديل مستوى التسجيل هنا (DEBUG, INFO, WARNING, ERROR, CRITICAL)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger(__name__)


# --- تحميل الإعدادات الأولية ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    app_logger.error("خطأ: لم يتم العثور على مفتاح GEMINI_API_KEY في ملف .env")

# --- إعدادات Flask ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-flask-session")

# --- إعدادات تخزين بيانات المحادثات على الخادم ---
CHATS_STORAGE_FILE = "chats_storage.json"
chats_data = {
    "chats": {},
    "active_chat_id": None
}

# --- وظائف تحميل وحفظ المحادثات من/إلى ملف ---
# --- وظائف تحميل وحفظ المحادثات من/إلى ملف ---
def load_chats_from_file():
    global chats_data
    try:
        if os.path.exists(CHATS_STORAGE_FILE):
            with open(CHATS_STORAGE_FILE, 'r', encoding='utf-8') as f:
                data_from_file = json.load(f)

                # --- !!! بداية الإضافة التشخيصية !!! ---
                # هذا السطر سيطبع معلومات حيوية في سجل الخادم عند بدء التشغيل
                # سيؤكد لنا أن الخادم الجديد قد بدأ وقرأ الملف الصحيح من القرص
                app_logger.info("*"*20 + " DIAGNOSTIC INFO " + "*"*20)
                app_logger.info(f"!!! DIAGNOSTIC: Attempting to load from {CHATS_STORAGE_FILE}")
                app_logger.info(f"!!! DIAGNOSTIC: Loaded active_chat_id: {data_from_file.get('active_chat_id')}")
                app_logger.info(f"!!! DIAGNOSTIC: Loaded total number of chats: {len(data_from_file.get('chats', {}))}")
                app_logger.info("*"*57)
                # --- !!! نهاية الإضافة التشخيصية !!! ---
                
                if isinstance(data_from_file, dict) and \
                   "chats" in data_from_file and isinstance(data_from_file["chats"], dict) and \
                   "active_chat_id" in data_from_file:
                    chats_data = data_from_file
                    app_logger.info(f"تم تحميل المحادثات بنجاح من {CHATS_STORAGE_FILE}") # تم تغيير الرسالة قليلاً للوضوح
                    if chats_data["active_chat_id"] and chats_data["active_chat_id"] not in chats_data["chats"]:
                        app_logger.warning(f"تحذير: active_chat_id المحمل '{chats_data['active_chat_id']}' لم يعد موجودًا. إعادة التعيين.")
                        if chats_data["chats"]:
                            # --- تعديل: استخدام الفرز الجديد لاختيار أول محادثة ---
                            first_chat_id = sorted(chats_data["chats"].keys(),
                                                   key=lambda cid: chats_data["chats"][cid].get("last_modified", 0),
                                                   reverse=True)[0]
                            chats_data["active_chat_id"] = first_chat_id
                        else:
                            chats_data["active_chat_id"] = None
                else:
                    app_logger.warning(f"تحذير: ملف {CHATS_STORAGE_FILE} لا يحتوي على الهيكل المتوقع. بدء ببيانات فارغة.")
                    chats_data = {"chats": {}, "active_chat_id": None}
        else:
            app_logger.info(f"ملف {CHATS_STORAGE_FILE} غير موجود. بدء ببيانات فارغة.")
    except json.JSONDecodeError:
        app_logger.error(f"خطأ في تحليل JSON من {CHATS_STORAGE_FILE}. بدء ببيانات فارغة.")
        chats_data = {"chats": {}, "active_chat_id": None}
    except Exception as e:
        app_logger.error(f"خطأ غير متوقع أثناء تحميل المحادثات: {e}. بدء ببيانات فارغة.")
        chats_data = {"chats": {}, "active_chat_id": None}

def save_chats_to_file():
    global chats_data
    try:
        with open(CHATS_STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(chats_data, f, ensure_ascii=False, indent=4)
        app_logger.info(f"تم حفظ المحادثات في {CHATS_STORAGE_FILE}")
    except Exception as e:
        app_logger.critical(f"!!! خطأ فادح: فشل حفظ المحادثات في {CHATS_STORAGE_FILE}: {e}")

load_chats_from_file()

# --- إعدادات ومعلومات المودلات ---
MODEL_CONFIG = {
    "gemini-2.5-pro": {"max_tokens": 65536, "supports_thinking": True, "supports_budget": False, "supports_search": True},
    "gemini-2.5-flash-preview-04-17": {"max_tokens": 65536, "supports_thinking": True, "supports_budget": True, "supports_search": True},
    "gemini-2.5-flash": {"max_tokens": 65536, "supports_thinking": True, "supports_budget": True, "supports_search": True},
    "gemini-2.0-flash-lite": {"max_tokens": 8192, "supports_thinking": False, "supports_budget": False, "supports_search": True},
    "gemini-2.5-pro-preview-05-06": {"max_tokens": 65536, "supports_thinking": True, "supports_budget": False, "supports_search": True},
    "gemini-2.5-flash-preview-05-20": {"max_tokens": 65536, "supports_thinking": True, "supports_budget": True, "supports_search": True},
}
DEFAULT_MODEL = "gemini-2.5-pro"
AVAILABLE_MODELS = list(MODEL_CONFIG.keys())

BASE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/"

DEFAULT_GENERATION_CONFIG = {
    "temperature": 1.0,
    "topP": 1.0,
    "topK": 1,
}

DEFAULT_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]


# --- *** بداية الكود الجديد: منطق إدارة سياق المحادثة *** ---

# الحد الأقصى للتوكنات التي سيتم إرسالها في كل طلب.
# يمكنك تعديل هذا الرقم. 50,000 هو رقم جيد يوازن بين السياق والأداء.
CONTEXT_TOKEN_LIMIT = 1700000 
# تقدير بسيط لعدد الأحرف لكل توكن. هذا ليس دقيقًا 100% ولكنه كافٍ لهذا الغرض.
# النماذج الإنجليزية حوالي 4، العربية قد تكون أقل. سنستخدم 3 كتقدير آمن.
CHARS_PER_TOKEN_ESTIMATE = 3

def trim_history(history, token_limit):
    """
    يقص سجل المحادثة من البداية إذا تجاوز عدد التوكنات التقديري الحد المسموح.
    لا يعدل السجل الأصلي، بل يعيد نسخة جديدة.
    """
    history_copy = list(history) # العمل على نسخة لحماية السجل الأصلي
    
    # حساب عدد التوكنات التقديري الحالي
    try:
        current_tokens = sum(len(part.get('text', '')) / CHARS_PER_TOKEN_ESTIMATE 
                             for message in history_copy 
                             for part in message.get('parts', []))
    except Exception as e:
        app_logger.error(f"خطأ أثناء حساب التوكنات التقديرية: {e}")
        return history_copy # في حالة الخطأ، أعد النسخة كما هي

    if current_tokens <= token_limit:
        return history_copy # لا حاجة للقطع، أعد النسخة

    app_logger.warning(f"السياق طويل ({int(current_tokens)} توكن > {token_limit}). سيتم قصه.")

    # ابدأ بحذف أقدم الرسائل حتى يصبح حجم السياق ضمن الحد المسموح
    # نحافظ على رسالة واحدة على الأقل لضمان عدم إرسال سجل فارغ
    while current_tokens > token_limit and len(history_copy) > 1:
        # إزالة أقدم رسالة (من بداية القائمة)
        removed_message = history_copy.pop(0)
        
        # إعادة حساب عدد التوكنات بعد الحذف
        removed_tokens = sum(len(part.get('text', '')) / CHARS_PER_TOKEN_ESTIMATE 
                             for part in removed_message.get('parts', []))
        current_tokens -= removed_tokens
    
    app_logger.info(f"تم قص السياق بنجاح. الحجم الجديد: {int(current_tokens)} توكن.")
    return history_copy

# --- *** نهاية الكود الجديد *** ---


@app.after_request
def add_header(response):
    if request.path.startswith('/static/'):
        if response.content_type and any(t in response.content_type for t in ['text/css', 'application/javascript', 'image/', 'font/']):
            response.headers['Cache-Control'] = 'public, max-age=31536000'
    return response

# --- دالة لإنشاء حالة محادثة جديدة ---
def get_default_chat_state(model_name=DEFAULT_MODEL):
    model_info = MODEL_CONFIG.get(model_name, list(MODEL_CONFIG.values())[0])
    max_tokens_for_model = model_info.get("max_tokens", 8192)
    config = DEFAULT_GENERATION_CONFIG.copy()
    config["maxOutputTokens"] = max_tokens_for_model

    supports_thinking = model_info.get("supports_thinking", False)
    supports_budget = model_info.get("supports_budget", False)

    new_id = str(uuid.uuid4())
    return {
        "id": new_id,
        "name": None, # --- تعديل: الاسم الافتراضي يبدأ بـ None ---
        "history": [],
        "config": config,
        "model": model_name,
        "safety": DEFAULT_SAFETY_SETTINGS.copy(),
        "thinking_enabled": supports_thinking and supports_budget,
        "thinking_budget": 24576 if supports_budget else None,
        "search_enabled": False,
        "last_modified": int(time.time() * 1000) # --- إضافة جديدة: وقت الإنشاء ---
    }

# --- الدالة الأساسية لاستدعاء API ---
def call_gemini_api(api_key, model, history, config, safety, thinking_enabled, thinking_budget, search_enabled):
    if not api_key:
        app_logger.error("API Key is not configured.")
        return None, None, "[خطأ: مفتاح API غير مكوّن]"

    # --- *** تعديل لاستخدام دالة قص السياق *** ---
    # نمرر السجل الكامل للدالة، وهي ستعيده مقصوصًا إذا لزم الأمر
    history_to_send = trim_history(history, CONTEXT_TOKEN_LIMIT)
    
    if not history_to_send:
        app_logger.warning("Attempted API call with empty history after trimming.")
        return None, None, "[خطأ: لا يمكن إجراء استدعاء API بسجل محادثة فارغ بعد قصه]"

    api_endpoint = f"{BASE_API_URL}{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    payload = {
        "contents": history_to_send, # <-- استخدام السجل الذي تم قصه
        "safetySettings": safety
    }

    gen_config = {
        "temperature": config.get("temperature", 1.0),
        "topP": config.get("topP", 1.0),
        "topK": config.get("topK", 1),
        "maxOutputTokens": config.get("maxOutputTokens", 8192),
    }

    model_info = MODEL_CONFIG.get(model, {})
    if model_info.get("supports_thinking"):
        if not thinking_enabled:
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}
        elif model_info.get("supports_budget") and thinking_budget is not None:
            try:
                budget_value = int(thinking_budget)
                clamped_budget = max(0, min(24576, budget_value))
                if clamped_budget >= 0:
                    gen_config["thinkingConfig"] = {"thinkingBudget": clamped_budget}
            except (ValueError, TypeError):
                 app_logger.warning(f"قيمة thinking_budget غير صالحة ({thinking_budget}). سيتم تجاهلها.")

    payload["generationConfig"] = gen_config

    if model_info.get("supports_search") and search_enabled:
        payload["tools"] = [{"googleSearch": {}}]
        app_logger.info(f"تم تفعيل Google Search tool للمودل {model}")

    app_logger.debug(f"Payload API: {json.dumps(payload)}")

    try:
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        response_data = response.json()
        app_logger.debug(f"API Response: {json.dumps(response_data)}")

        model_reply = "[حدث خطأ في استخلاص الرد]"
        error_reason = None

        if 'candidates' in response_data and response_data['candidates']:
            candidate = response_data['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content'] and candidate['content']['parts']:
                if candidate['content']['parts'][0] and 'text' in candidate['content']['parts'][0]:
                    model_reply = candidate['content']['parts'][0]['text']
                else:
                    model_reply = "[تم إرجاع جزء فارغ أو غير نصي]"
                    error_reason = "Received non-text or empty part in candidate content."
            elif 'finishReason' in candidate:
                model_reply = f"[تم إنهاء التوليد مبكراً. السبب: {candidate.get('finishReason', 'غير معروف')}]"
                error_reason = f"Finish Reason: {candidate.get('finishReason', 'غير معروف')}"
                if 'safetyRatings' in candidate:
                    model_reply += f" (تقييمات الأمان: {candidate['safetyRatings']})"
                    error_reason += f", Safety Ratings: {candidate['safetyRatings']}"
            else:
                error_reason = "No valid content or finish reason in candidate."
        elif 'promptFeedback' in response_data and 'blockReason' in response_data['promptFeedback']:
            block_reason_str = response_data['promptFeedback']['blockReason']
            model_reply = f"[تم حظر الطلب. السبب: {block_reason_str}]"
            error_reason = f"Prompt Blocked: {block_reason_str}"
        else:
            model_reply = "[رد غير متوقع أو فارغ من API]"
            error_reason = "Unexpected or empty API response structure."

        token_usage = response_data.get('usageMetadata', {})
        token_info_str = (
            f"الإدخال: {token_usage.get('promptTokenCount', 'N/A')}, "
            f"الإخراج: {token_usage.get('candidatesTokenCount', 'N/A')}, "
            f"الإجمالي: {token_usage.get('totalTokenCount', 'N/A')}"
        )
        app_logger.info(f"Token Usage: {token_info_str}")

        return model_reply, token_info_str, error_reason, response_data # --- تعديل: إعادة response_data كاملة ---

    except requests.exceptions.Timeout:
        app_logger.error("انتهت مهلة الاتصال بالـ API.")
        return None, None, "انتهت مهلة الاتصال بالـ API", None
    except requests.exceptions.RequestException as e:
        app_logger.error(f"خطأ في الاتصال بالـ API: {e}")
        error_details_str = f"خطأ في الاتصال: {e}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                app_logger.error(f"تفاصيل الخطأ من الخادم: {json.dumps(error_details, indent=2)}")
                api_error_message = error_details.get("error", {}).get("message", json.dumps(error_details))
                error_details_str = f"خطأ API ({e.response.status_code}): {api_error_message}"
            except json.JSONDecodeError:
                error_details_str = f"خطأ API ({e.response.status_code}): {e.response.text}"
                app_logger.error(f"لم يتمكن من تحليل رد الخطأ من الخادم: {e.response.text}")
            except Exception as api_e:
                 app_logger.error(f"خطأ أثناء معالجة رد خطأ API: {api_e}")
                 error_details_str = f"خطأ API ({e.response.status_code}): Failed to process error response"
        return None, None, error_details_str, None
    except Exception as e:
        app_logger.error(f"حدث خطأ غير متوقع أثناء استدعاء API: {e}")
        return None, None, f"خطأ داخلي غير متوقع: {e}", None

# --- مسارات Flask ---

@app.route('/')
def index():
    app_logger.info("تم طلب الصفحة الرئيسية.")
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    global chats_data
    if not API_KEY:
        return jsonify({"error": "API key is not configured on the server."}), 500

    data = request.get_json()
    if not data:
        app_logger.warning("Received invalid JSON payload for /chat.")
        return jsonify({"error": "Invalid JSON payload"}), 400

    user_prompt = data.get('user_prompt')
    chat_id = data.get('chat_id')

    if not user_prompt:
        app_logger.warning("Missing user prompt in /chat request.")
        return jsonify({"error": "User prompt is missing"}), 400

    if not chat_id or chat_id not in chats_data["chats"]:
        if chats_data["active_chat_id"] and chats_data["active_chat_id"] in chats_data["chats"]:
            chat_id = chats_data["active_chat_id"]
            app_logger.warning(f"chat_id غير موجود أو غير صالح في طلب /chat، استخدام active_chat_id للخادم: {chat_id}")
        else:
            app_logger.error("Valid chat_id is missing or chat not found, and no valid active_chat_id on server for /chat.")
            return jsonify({"error": "Valid chat_id is missing or chat not found on server."}), 400

    active_chat_state = chats_data["chats"].get(chat_id)
    if not active_chat_state:
        app_logger.error(f"Chat with ID {chat_id} not found on server during /chat processing.")
        return jsonify({"error": f"Chat with ID {chat_id} not found on server."}), 404

    app_logger.info(f"Processing chat message for chat ID: {chat_id}")

    current_config = active_chat_state['config']
    current_model = active_chat_state['model']
    safety_settings = active_chat_state['safety']
    thinking_enabled = active_chat_state['thinking_enabled']
    thinking_budget = active_chat_state.get('thinking_budget')
    search_enabled = active_chat_state.get('search_enabled', False)

    user_message_entry = {"role": "user", "parts": [{"text": user_prompt}]}
    active_chat_state['history'].append(user_message_entry)

    # --- تعديل: استلام response_data من call_gemini_api ---
    model_response_text, token_info, error_reason, api_raw_response = call_gemini_api(
        API_KEY, current_model, active_chat_state['history'], current_config,
        safety_settings, thinking_enabled, thinking_budget, search_enabled
    )

    if model_response_text is not None:
        model_message_entry = {"role": "model", "parts": [{"text": model_response_text}]}
        active_chat_state['history'].append(model_message_entry)
        
        # --- START: تعديل الاسم الافتراضي الذكي وتحديث last_modified ---
        new_chat_name_for_client = None
        # تحقق مما إذا كانت هذه هي الرسالة الثانية في المحادثة (المحادثة تحتوي على رسالتي مستخدم/نموذج)
        # وهذا يعني أنها أول رسالة تمت الإجابة عليها.
        if len(active_chat_state['history']) == 2:
            # إذا لم يكن للمحادثة اسم مخصص بالفعل (الافتراضي هو None)
            if active_chat_state.get('name') is None:
                # استخراج أول 7 كلمات من رسالة المستخدم الأولى
                first_user_message_text = active_chat_state['history'][0]['parts'][0]['text']
                words = first_user_message_text.split()
                # إذا كانت الرسالة قصيرة جداً، اجعلها تبدو طبيعية
                if len(words) > 7:
                    new_name = ' '.join(words[:7]) + '...'
                else:
                    new_name = ' '.join(words)
                
                # تحديث الاسم في حالة المحادثة
                active_chat_state['name'] = new_name
                new_chat_name_for_client = new_name # لإرسالها للعميل
                app_logger.info(f"Automatically named chat {chat_id} to '{new_name}' based on first prompt.")

        # تحديث وقت التعديل الأخير للمحادثة
        active_chat_state['last_modified'] = int(time.time() * 1000)
        # --- END: تعديل الاسم الافتراضي الذكي وتحديث last_modified ---

        save_chats_to_file()
        app_logger.info(f"Successfully processed chat message and generated model response for chat {chat_id}.")
        
        response_payload = {
            "response": model_response_text,
            "token_info": token_info,
            "error": error_reason,
            "new_history_entry": model_message_entry
        }
        if new_chat_name_for_client:
            response_payload["new_chat_name"] = new_chat_name_for_client
        
        return jsonify(response_payload)
    else:
        if active_chat_state['history'] and active_chat_state['history'][-1].get('role') == "user" and \
           active_chat_state['history'][-1].get('parts') and active_chat_state['history'][-1]['parts'][0].get('text') == user_prompt:
            active_chat_state['history'].pop()
            app_logger.warning(f"تم إزالة رسالة المستخدم من سجل المحادثة {chat_id} بسبب فشل API.")
        app_logger.error(f"API call failed for chat {chat_id}. Error: {error_reason}")
        return jsonify({"error": error_reason or "Unknown error calling API"}), 500

@app.route('/regenerate', methods=['POST'])
def regenerate():
    global chats_data
    if not API_KEY:
        return jsonify({"error": "API key is not configured on the server."}), 500

    data = request.get_json()
    if not data:
        app_logger.warning("Received invalid JSON payload for /regenerate.")
        return jsonify({"error": "Invalid JSON payload"}), 400

    chat_id = data.get('chat_id')
    truncate_length = data.get('truncate_length')
    edit_index = data.get('edit_index')
    new_text_for_edit = data.get('new_text_for_edit')

    if not chat_id or chat_id not in chats_data["chats"]:
        app_logger.error(f"Invalid chat_id '{chat_id}' or chat not found for /regenerate.")
        return jsonify({"error": "Valid chat_id is missing or chat not found"}), 404

    active_chat_state = chats_data["chats"].get(chat_id)
    if not active_chat_state:
        app_logger.error(f"Chat with ID {chat_id} not found on server during /regenerate processing.")
        return jsonify({"error": f"Chat with ID {chat_id} not found."}), 404

    app_logger.info(f"Processing regenerate request for chat ID: {chat_id}, truncate_length: {truncate_length}, edit_index: {edit_index}")

    if edit_index is not None and new_text_for_edit is not None:
        try:
            edit_index_int = int(edit_index)
            if 0 <= edit_index_int < len(active_chat_state['history']):
                if active_chat_state['history'][edit_index_int].get('parts') and \
                   len(active_chat_state['history'][edit_index_int]['parts']) > 0 and \
                   active_chat_state['history'][edit_index_int]['parts'][0].get('text') is not None:
                    active_chat_state['history'][edit_index_int]['parts'][0]['text'] = str(new_text_for_edit)
                    app_logger.info(f"Edited message at index {edit_index_int} in chat {chat_id} history before truncation.")
                    if truncate_length is None or truncate_length != edit_index_int + 1:
                         app_logger.warning(f"truncate_length ({truncate_length}) لا يتطابق مع edit_index + 1 ({edit_index_int + 1}). استخدام edit_index + 1 كطول قطع.")
                         truncate_length = edit_index_int + 1
                else:
                    app_logger.warning(f"Invalid message structure at index {edit_index_int} for editing in chat {chat_id}.")
            else:
                app_logger.warning(f"Invalid edit_index {edit_index_int} for chat {chat_id} history length {len(active_chat_state['history'])}. Ignoring edit.")
        except (ValueError, TypeError):
            app_logger.warning(f"Invalid edit_index or new_text_for_edit type for chat {chat_id}. Ignoring edit.")


    if truncate_length is None or not isinstance(truncate_length, int) or truncate_length < 0:
        app_logger.error("Invalid or missing truncate_length after processing edit for /regenerate.")
        return jsonify({"error": "Invalid truncate_length for regeneration"}), 400

    if truncate_length > len(active_chat_state['history']):
         app_logger.error(f"truncate_length ({truncate_length}) أكبر من طول السجل ({len(active_chat_state['history'])}) لـ /regenerate.")
         return jsonify({"error": "Truncate length is greater than history length"}), 400


    truncated_history = active_chat_state['history'][:truncate_length]

    if truncated_history and truncated_history[-1].get('role') == 'model':
        app_logger.info("Regenerate: Last message in truncated history was 'model', removing it.")
        truncated_history.pop()

    if not truncated_history:
        app_logger.error("Cannot regenerate from an empty or invalid history state after truncation.")
        return jsonify({"error": "Cannot regenerate from an empty or invalid history state after truncation."}), 400

    current_config = active_chat_state['config']
    current_model = active_chat_state['model']
    safety_settings = active_chat_state['safety']
    thinking_enabled = active_chat_state['thinking_enabled']
    thinking_budget = active_chat_state.get('thinking_budget')
    search_enabled = active_chat_state.get('search_enabled', False)

    # --- تعديل: استلام response_data من call_gemini_api ---
    model_response_text, token_info, error_reason, api_raw_response = call_gemini_api(
        API_KEY, current_model, truncated_history, current_config,
        safety_settings, thinking_enabled, thinking_budget, search_enabled
    )

    if model_response_text is not None:
        active_chat_state['history'] = truncated_history
        model_message_entry = {"role": "model", "parts": [{"text": model_response_text}]}
        active_chat_state['history'].append(model_message_entry)
        
        # --- إضافة جديدة: تحديث last_modified ---
        active_chat_state['last_modified'] = int(time.time() * 1000)
        # --- نهاية الإضافة الجديدة ---

        save_chats_to_file()
        app_logger.info(f"Successfully regenerated response for chat {chat_id}.")
        return jsonify({
            "response": model_response_text,
            "token_info": token_info,
            "error": error_reason,
            "new_history_entry": model_message_entry
        })
    else:
        app_logger.error(f"API call failed during regeneration for chat {chat_id}. Error: {error_reason}")
        return jsonify({"error": error_reason or "Unknown error calling API during regeneration"}), 500

@app.route('/branch_chat/<chat_id>', methods=['POST'])
def branch_chat(chat_id):
    global chats_data
    if chat_id not in chats_data["chats"]:
        app_logger.error(f"Chat with ID {chat_id} not found for branching.")
        return jsonify({"error": f"Chat with ID {chat_id} not found"}), 404

    data = request.get_json()
    if not data:
        app_logger.warning("Received invalid JSON payload for /branch_chat.")
        return jsonify({"error": "Invalid JSON payload"}), 400

    message_index = data.get('message_index')
    if message_index is None or not isinstance(message_index, int) or message_index < 0:
        app_logger.warning(f"Invalid message_index {message_index} for /branch_chat.")
        return jsonify({"error": "Invalid message_index provided"}), 400

    original_chat = chats_data["chats"][chat_id]

    if message_index >= len(original_chat['history']):
        app_logger.warning(f"message_index ({message_index}) خارج نطاق سجل المحادثة ({len(original_chat['history'])}) لـ /branch_chat.")
        return jsonify({"error": "Message index is out of history range"}), 400

    branched_history = original_chat['history'][:message_index + 1]
    app_logger.info(f"Branched history from chat {chat_id} up to index {message_index}.")

    new_chat_object = get_default_chat_state(original_chat['model'])
    new_chat_id = new_chat_object['id']

    new_chat_object['name'] = f"فرع من ({original_chat.get('name') or original_chat['id'][:4]}) رسالة #{message_index + 1}" # --- تعديل: اسم الفرع ---
    new_chat_object['history'] = branched_history
    new_chat_object['config'] = original_chat['config'].copy()
    new_chat_object['safety'] = original_chat['safety'].copy()
    new_chat_object['thinking_enabled'] = original_chat.get('thinking_enabled', False)
    new_chat_object['thinking_budget'] = original_chat.get('thinking_budget')
    new_chat_object['search_enabled'] = original_chat.get('search_enabled', False)
    # --- إضافة جديدة: تحديث last_modified للفرع الجديد ---
    new_chat_object['last_modified'] = int(time.time() * 1000)
    # --- نهاية الإضافة الجديدة ---

    chats_data["chats"][new_chat_id] = new_chat_object
    chats_data["active_chat_id"] = new_chat_id
    save_chats_to_file()

    app_logger.info(f"New branched chat created (ID: {new_chat_id}) from chat {chat_id} at index {message_index}. Set as active.")

    return jsonify(branched_chat_state=new_chat_object, active_chat_id=new_chat_id), 201

# --- المسارات المتعلقة بإدارة حالة العميل والجلسة (الآن تُدار البيانات على الخادم) ---

@app.route('/get_initial_app_state', methods=['GET'])
def get_initial_app_state():
    global chats_data
    app_logger.info("Requested initial application state.")

    if not chats_data["chats"]:
        app_logger.info("No chats found on server during initial state request. Creating a default one.")
        default_model_for_new = DEFAULT_MODEL
        new_chat_object = get_default_chat_state(default_model_for_new)
        chat_id = new_chat_object['id']
        chats_data["chats"][chat_id] = new_chat_object
        chats_data["active_chat_id"] = chat_id
        save_chats_to_file()
        app_logger.info(f"Initial state: Created and set active chat: {chat_id}")

    chats_metadata = []
    # --- تعديل: الفرز حسب last_modified (الأحدث أولاً) في البيانات الوصفية ---
    sorted_chat_ids = sorted(chats_data["chats"].keys(),
                             key=lambda cid: chats_data["chats"][cid].get("last_modified", 0),
                             reverse=True) # الأحدث أولاً

    for cid in sorted_chat_ids:
        chat = chats_data["chats"][cid]
        chats_metadata.append({
            "id": chat["id"],
            "name": chat.get("name"), # --- تعديل: الاسم هنا قد يكون None
            "last_modified": chat.get("last_modified", 0) # --- إضافة جديدة: إرسال last_modified
        })

    active_chat_full_state = None
    if chats_data["active_chat_id"] and chats_data["active_chat_id"] in chats_data["chats"]:
         active_chat_full_state = chats_data["chats"].get(chats_data["active_chat_id"])
         app_logger.info(f"Returning full state for active chat: {chats_data['active_chat_id']}")
    elif chats_metadata:
        first_chat_id = chats_metadata[0]["id"]
        chats_data["active_chat_id"] = first_chat_id
        active_chat_full_state = chats_data["chats"].get(first_chat_id)
        save_chats_to_file()
        app_logger.info(f"Server: Active chat ID was invalid. Resetting to first chat: {first_chat_id}. Returning its full state.")
    else:
         app_logger.info("Server: No chats available after initial load. Returning empty state.")


    return jsonify({
        "all_chats_metadata": chats_metadata,
        "active_chat_id": chats_data["active_chat_id"],
        "active_chat_full_state": active_chat_full_state,
        "available_models": AVAILABLE_MODELS,
        "model_config": MODEL_CONFIG
    })


@app.route('/create_new_chat', methods=['POST'])
def create_new_chat():
    global chats_data
    app_logger.info("Received request to create new chat.")

    requested_model = request.json.get('model', DEFAULT_MODEL)
    if requested_model not in MODEL_CONFIG:
        app_logger.warning(f"Requested model '{requested_model}' not found. Using default model '{DEFAULT_MODEL}'.")
        requested_model = DEFAULT_MODEL

    new_chat_object = get_default_chat_state(requested_model)
    chat_id = new_chat_object['id']

    chats_data["chats"][chat_id] = new_chat_object
    chats_data["active_chat_id"] = chat_id
    save_chats_to_file()

    app_logger.info(f"New chat created and set active: {chat_id}")
    return jsonify(new_chat_state=new_chat_object, active_chat_id=chat_id), 201


@app.route('/get_chat_state/<chat_id>', methods=['GET'])
def get_chat_state_by_id(chat_id):
    global chats_data
    app_logger.info(f"Requested chat state for chat ID: {chat_id}")
    chat_state = chats_data["chats"].get(chat_id)
    if chat_state:
        return jsonify(chat_state=chat_state), 200
    else:
        app_logger.warning(f"Chat with ID {chat_id} not found when requesting state.")
        return jsonify({"error": f"Chat with ID {chat_id} not found"}), 404


@app.route('/switch_chat/<chat_id>', methods=['POST'])
def switch_chat(chat_id):
    global chats_data
    app_logger.info(f"Received request to switch active chat to ID: {chat_id}")
    if chat_id in chats_data["chats"]:
        chats_data["active_chat_id"] = chat_id
        # --- إضافة جديدة: تحديث last_modified للمحادثة التي تم التبديل إليها ---
        chats_data["chats"][chat_id]['last_modified'] = int(time.time() * 1000)
        # --- نهاية الإضافة الجديدة ---
        save_chats_to_file()
        app_logger.info(f"Server: Active chat switched to: {chat_id}")
        return jsonify({"message": f"Server: Switched to chat {chat_id}", "active_chat_id": chat_id}), 200
    else:
        app_logger.warning(f"Chat with ID {chat_id} not found when switching.")
        return jsonify({"error": f"Chat with ID {chat_id} not found"}), 404


@app.route('/delete_chat/<chat_id>', methods=['DELETE'])
def delete_chat_from_server(chat_id):
    global chats_data
    app_logger.info(f"Received request to delete chat ID: {chat_id}")
    if chat_id in chats_data["chats"]:
        deleted_chat_name = chats_data["chats"][chat_id].get("name", chat_id)
        del chats_data["chats"][chat_id]
        app_logger.info(f"Server: Deleted chat: {deleted_chat_name} (ID: {chat_id})")

        new_active_id = chats_data["active_chat_id"]
        if new_active_id == chat_id:
            if chats_data["chats"]:
                # --- تعديل: استخدام الفرز الجديد لاختيار أول محادثة بعد الحذف ---
                new_active_id = sorted(chats_data["chats"].keys(),
                                         key=lambda cid: chats_data["chats"][cid].get("last_modified", 0),
                                         reverse=True)[0]
                chats_data["active_chat_id"] = new_active_id
                app_logger.info(f"Server: Active chat was deleted. New active chat set to: {new_active_id}")
            else:
                new_active_id = None
                chats_data["active_chat_id"] = None
                app_logger.info("Server: Active chat was deleted. No chats remaining.")

        save_chats_to_file()
        return jsonify({
            "message": f"Server: Chat '{deleted_chat_name}' deleted successfully.",
            "deleted_chat_id": chat_id,
            "new_active_chat_id": new_active_id
        }), 200
    else:
        app_logger.warning(f"Chat with ID {chat_id} not found for deletion.")
        return jsonify({"error": f"Chat with ID {chat_id} not found for deletion"}), 404


@app.route('/update_chat_config/<chat_id>', methods=['POST'])
def update_chat_config(chat_id):
    global chats_data
    app_logger.info(f"Received request to update config for chat ID: {chat_id}")
    if chat_id not in chats_data["chats"]:
        app_logger.warning(f"Chat {chat_id} not found for config update.")
        return jsonify({"error": f"Chat {chat_id} not found"}), 404

    data = request.get_json()
    if not data:
        app_logger.warning("Received invalid JSON payload for /update_chat_config.")
        return jsonify({"error": "Invalid JSON payload"}), 400

    chat_to_update = chats_data["chats"][chat_id]
    config_changed = False
    updated_fields = {} # لإرسال تفاصيل التحديث للعميل

    new_model = data.get('model')
    if new_model and new_model in MODEL_CONFIG and new_model != chat_to_update['model']:
        chat_to_update['model'] = new_model
        model_info = MODEL_CONFIG[new_model]
        chat_to_update['config']['maxOutputTokens'] = model_info.get('max_tokens', 8192)
        chat_to_update['thinking_enabled'] = model_info.get('supports_thinking', False) and model_info.get('supports_budget', False)
        chat_to_update['thinking_budget'] = 24576 if model_info.get('supports_budget', False) else None
        chat_to_update['search_enabled'] = False # عادةً يتم تعطيل البحث عند تغيير المودل كإعداد افتراضي
        config_changed = True
        app_logger.info(f"Model for chat {chat_id} updated to {new_model}. Features reset based on model.")

    new_name = data.get('name')
    # يجب أن نسمح بتعيين الاسم إلى None (لإفراغه)
    if new_name is not None: # تحقق إذا تم إرسال حقل الاسم
        if (new_name.strip() == '' and chat_to_update.get('name') is not None) or \
           (new_name.strip() != '' and new_name.strip() != chat_to_update.get('name')):
            chat_to_update['name'] = new_name.strip() or None # حفظ الاسم الفارغ كـ None
            config_changed = True
            app_logger.info(f"Name for chat {chat_id} updated to '{chat_to_update['name']}'.")
    
    new_config_params = data.get('config')
    if new_config_params and isinstance(new_config_params, dict):
        current_config_obj = chat_to_update['config']
        for key in ['temperature', 'topP', 'topK']:
            if key in new_config_params and isinstance(new_config_params[key], (int, float)):
                 new_val = float(new_config_params[key]) if key != 'topK' else int(new_config_params[key])
                 if (key == 'temperature' and 0.0 <= new_val <= 2.0 and new_val != current_config_obj.get(key)) or \
                    (key == 'topP' and 0.0 <= new_val <= 1.0 and new_val != current_config_obj.get(key)) or \
                    (key == 'topK' and new_val >= 1 and new_val != current_config_obj.get(key)):
                     current_config_obj[key] = new_val
                     config_changed = True
                     app_logger.info(f"Config '{key}' for chat {chat_id} updated.")

    if 'thinking_enabled' in data:
        model_supports_thinking = MODEL_CONFIG.get(chat_to_update['model'], {}).get('supports_thinking', False)
        new_thinking_enabled = bool(data['thinking_enabled'])
        if model_supports_thinking and new_thinking_enabled != chat_to_update.get('thinking_enabled', False):
            chat_to_update['thinking_enabled'] = new_thinking_enabled
            config_changed = True
            app_logger.info(f"Thinking enabled for chat {chat_id} updated to {chat_to_update['thinking_enabled']}.")
        elif not model_supports_thinking and chat_to_update.get('thinking_enabled', False): # إذا كان المودل لا يدعم ولكن كان مفعلاً
            chat_to_update['thinking_enabled'] = False
            config_changed = True
            app_logger.info(f"Thinking disabled for chat {chat_id} as current model does not support it.")


    if 'thinking_budget' in data:
         model_supports_budget = MODEL_CONFIG.get(chat_to_update['model'], {}).get('supports_budget', False)
         # إذا كان المودل يدعم الميزانية والتفكير مفعّل، أو إذا كانت القيمة المرسلة None لإلغاء الميزانية
         if model_supports_budget and chat_to_update.get('thinking_enabled', False) or data['thinking_budget'] is None:
             new_budget_value = data['thinking_budget']
             current_budget = chat_to_update.get('thinking_budget')

             if new_budget_value is None:
                 if current_budget is not None:
                     chat_to_update['thinking_budget'] = None
                     config_changed = True
                     app_logger.info(f"Thinking budget for chat {chat_id} set to None.")
             else:
                 try:
                     budget = int(new_budget_value)
                     clamped_budget = max(0, min(24576, budget))
                     if clamped_budget != current_budget:
                         chat_to_update['thinking_budget'] = clamped_budget
                         config_changed = True
                         app_logger.info(f"Thinking budget for chat {chat_id} updated to {chat_to_update['thinking_budget']}.")
                 except (ValueError, TypeError):
                     app_logger.warning(f"Invalid thinking_budget value received for chat {chat_id}. Ignoring.")
         elif not model_supports_budget and chat_to_update.get('thinking_budget') is not None: # إذا كان المودل لا يدعم ولكن كانت هناك قيمة
             chat_to_update['thinking_budget'] = None
             config_changed = True
             app_logger.info(f"Thinking budget disabled for chat {chat_id} as current model does not support it.")


    if 'search_enabled' in data:
        model_supports_search = MODEL_CONFIG.get(chat_to_update['model'], {}).get('supports_search', False)
        new_search_enabled = bool(data['search_enabled'])
        if model_supports_search and new_search_enabled != chat_to_update.get('search_enabled', False):
            chat_to_update['search_enabled'] = new_search_enabled
            config_changed = True
            app_logger.info(f"Search enabled for chat {chat_id} updated to {chat_to_update['search_enabled']}.")
        elif not model_supports_search and chat_to_update.get('search_enabled', False): # إذا كان المودل لا يدعم ولكن كان مفعلاً
            chat_to_update['search_enabled'] = False
            config_changed = True
            app_logger.info(f"Search disabled for chat {chat_id} as current model does not support it.")


    if config_changed:
        # --- إضافة جديدة: تحديث last_modified عند تغيير الإعدادات ---
        chat_to_update['last_modified'] = int(time.time() * 1000)
        # --- نهاية الإضافة الجديدة ---
        save_chats_to_file()
        app_logger.info(f"Config for chat {chat_id} saved.")
        return jsonify({
            "message": f"Config for chat {chat_id} updated.",
            "chat_id": chat_id,
            "updated_chat_metadata": { # إرسال البيانات الوصفية المحدثة للعميل
                "id": chat_id,
                "name": chat_to_update.get("name"),
                "last_modified": chat_to_update.get("last_modified")
            }
        }), 200
    else:
        app_logger.info(f"No configuration changes detected for chat {chat_id}.")
        return jsonify({"message": "No configuration changes applied.", "chat_id": chat_id}), 200


@app.route('/clear_chat_history/<chat_id>', methods=['POST'])
def clear_chat_history(chat_id):
    global chats_data
    app_logger.info(f"Received request to clear history for chat ID: {chat_id}")
    if chat_id not in chats_data["chats"]:
        app_logger.warning(f"Chat {chat_id} not found for history clear.")
        return jsonify({"error": f"Chat {chat_id} not found"}), 404

    chats_data["chats"][chat_id]['history'] = []
    # --- إضافة جديدة: تحديث last_modified عند مسح السجل ---
    chats_data["chats"][chat_id]['last_modified'] = int(time.time() * 1000)
    # --- نهاية الإضافة الجديدة ---
    save_chats_to_file()
    app_logger.info(f"History cleared for chat {chat_id}.")
    return jsonify({"message": f"History cleared for chat {chat_id}.", "cleared_chat_id": chat_id}), 200

@app.route('/export_all_chats', methods=['GET'])
def export_all_chats():
    global chats_data
    app_logger.info("Received request to export all chats.")
    try:
        data_to_export = chats_data.copy()
        response = jsonify(data_to_export)
        response.headers['Content-Disposition'] = 'attachment; filename="gemini_flask_chats_backup.json"'
        response.headers['Content-Type'] = 'application/json'
        app_logger.info("Preparing chat data for export.")
        return response, 200
    except Exception as e:
        app_logger.error(f"Error during export: {e}")
        return jsonify({"error": f"An unexpected error occurred during export: {str(e)}"}), 500


@app.route('/import_all_chats', methods=['POST'])
def import_all_chats():
    global chats_data
    app_logger.info("Received request to import chats.")
    try:
        if 'file' not in request.files:
            app_logger.warning("No file part in the import request.")
            return jsonify({"error": "No file part in the request"}), 400
        file = request.files['file']
        if file.filename == '':
            app_logger.warning("No file selected for import.")
            return jsonify({"error": "No file selected for uploading"}), 400

        if file and (file.filename.lower().endswith('.json') or file.filename.lower().endswith('.txt')):
            imported_data_str = file.read().decode('utf-8')
            new_data = json.loads(imported_data_str)

            if isinstance(new_data, dict) and \
               "chats" in new_data and isinstance(new_data["chats"], dict) and \
               "active_chat_id" in new_data:

                app_logger.info("Importing new chats data...")
                # --- تعديل: التأكد من وجود last_modified في البيانات المستوردة أو تعيينها ---
                for chat_id, chat_obj in new_data["chats"].items():
                    if "last_modified" not in chat_obj:
                        chat_obj["last_modified"] = 0 # تعيين قيمة افتراضية قديمة جداً
                        app_logger.warning(f"Added default 'last_modified' to imported chat {chat_id}.")

                chats_data = new_data

                if chats_data["active_chat_id"] and chats_data["active_chat_id"] not in chats_data["chats"]:
                    app_logger.warning(f"Imported active_chat_id '{chats_data['active_chat_id']}' is invalid. Resetting.")
                    if chats_data["chats"]:
                        # --- تعديل: استخدام الفرز الجديد لاختيار أول محادثة مستوردة ---
                        first_imported_chat_id = sorted(chats_data["chats"].keys(),
                                                        key=lambda cid: chats_data["chats"][cid].get("last_modified", 0),
                                                        reverse=True)[0]
                        chats_data["active_chat_id"] = first_imported_chat_id
                        app_logger.info(f"Setting active chat to first imported chat: {first_imported_chat_id}")
                    else:
                        chats_data["active_chat_id"] = None
                        app_logger.info("Imported data contains no chats. Setting active chat to None.")

                save_chats_to_file()
                app_logger.info("Chats imported successfully and saved.")
                return jsonify({
                    "message": "Chats imported successfully.",
                    "imported_chats_data": chats_data
                }), 200
            else:
                app_logger.warning("Invalid JSON structure in the imported file.")
                return jsonify({"error": "Invalid JSON structure in the imported file."}), 400
        else:
            app_logger.warning(f"Invalid file type for import: {file.filename}")
            return jsonify({"error": "Invalid file type. Please upload a .json or .txt file."}), 400
    except json.JSONDecodeError:
        app_logger.error("Invalid JSON content in the imported file.")
        return jsonify({"error": "Invalid JSON content in the file."}), 400
    except Exception as e:
        app_logger.error(f"An unexpected error occurred during import: {e}")
        return jsonify({"error": f"An unexpected error occurred during import: {str(e)}"}), 500


# --- تشغيل الخادم ---
if __name__ == '__main__':
    app_logger.info("*" * 80)
    app_logger.info(" بدء تشغيل خادم Gemini Chat المحلي (Flask/Termux) - إصدار تخزين الخادم")
    app_logger.info(f" ملف تخزين المحادثات: {os.path.abspath(CHATS_STORAGE_FILE)}")
    app_logger.info(" المودلات المتاحة: " + ", ".join(AVAILABLE_MODELS))
    app_logger.info(" المودل الافتراضي للمحادثة الجديدة: " + DEFAULT_MODEL)
    app_logger.info(" هام: يتم تخزين المحادثات على الخادم الآن في ملف")
    app_logger.info(" للوصول: افتح المتصفح على http://localhost:5001 أو http://127.0.0.1:5001")
    app_logger.info("*" * 80)
    # debug=False مناسب أكثر بعد الانتهاء من التطوير المكثف
    # use_reloader=False في Termux غالباً ما يكون أفضل لتجنب مشاكل التفرع
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)