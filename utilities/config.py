import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')
SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
BACKUP_FOLDER = os.path.join(SCRIPT_FOLDER, 'backups')
ALLOWED_EXTENSIONS = {
    'mp4',
    'mov',
    'webp',
    'mkv',
    'jpg',
    'jpeg',
    'png',
    'gif'}  # إضافة امتدادات الصور
