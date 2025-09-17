def load_chats_from_file():
    global chats_data
    try:
        if os.path.exists(CHATS_STORAGE_FILE):
            with open(CHATS_STORAGE_FILE, 'r', encoding='utf-8') as f:
                data_from_file = json.load(f)
                if isinstance(data_from_file, dict) and \
                   "chats" in data_from_file and isinstance(data_from_file["chats"], dict) and \
                   "active_chat_id" in data_from_file:
                    chats_data = data_from_file
                    app_logger.info(f"تم تحميل المحادثات من {CHATS_STORAGE_FILE}")
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

