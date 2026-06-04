import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
SECRET_KEY = os.urandom(24)
MAX_PREVIEW_ROWS = 100
SESSION_CLEANUP_HOURS = 24
