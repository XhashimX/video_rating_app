import os

# مسار مجلد السكربت
SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__)).replace("/utilities", "")

# مسار مجلد النسخ الاحتياطية
BACKUP_FOLDER = os.path.join(SCRIPT_FOLDER, "backups")

# مفتاح سري آمن لتشفير الجلسات
SECRET_KEY = 'your_secure_secret_key'

# أنواع الملفات المدعومة
ALLOWED_EXTENSIONS = {'mp4', 'mkv', 'avi', 'mov', 'wmv'}