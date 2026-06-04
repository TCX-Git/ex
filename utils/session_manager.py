import os
import uuid
import time
import pandas as pd
from flask import session
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS


def _get_session_id():
    """Get or create session ID."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']


def _get_session_dir():
    """Get the session directory, creating it if needed."""
    sid = _get_session_id()
    sess_dir = os.path.join(UPLOAD_FOLDER, sid)
    os.makedirs(sess_dir, exist_ok=True)
    return sess_dir


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage):
    """Save uploaded file to session directory. Returns (saved_path, extension)."""
    sess_dir = _get_session_dir()
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    original_path = os.path.join(sess_dir, f'original.{ext}')
    file_storage.save(original_path)
    return original_path, ext


def load_dataframe(use_cleaned=True):
    """Load DataFrame from session. If use_cleaned and cleaned.pkl exists, use it.
    Otherwise fall back to original file."""
    sess_dir = _get_session_dir()

    cleaned_path = os.path.join(sess_dir, 'cleaned.pkl')
    if use_cleaned and os.path.exists(cleaned_path):
        return pd.read_pickle(cleaned_path)

    # Try to load original file
    for ext in ['csv', 'xlsx', 'xls']:
        original_path = os.path.join(sess_dir, f'original.{ext}')
        if os.path.exists(original_path):
            if ext == 'csv':
                return pd.read_csv(original_path)
            else:
                return pd.read_excel(original_path)

    return None


def save_dataframe(df, filename='cleaned.pkl'):
    """Save DataFrame to session directory as pickle."""
    sess_dir = _get_session_dir()
    path = os.path.join(sess_dir, filename)
    df.to_pickle(path)
    return path


def reset_to_original():
    """Delete cleaned data so system falls back to original."""
    sess_dir = _get_session_dir()
    cleaned_path = os.path.join(sess_dir, 'cleaned.pkl')
    if os.path.exists(cleaned_path):
        os.remove(cleaned_path)
    return True


def get_session_info():
    """Get info about the current session data."""
    sess_dir = _get_session_dir()
    info = {
        'has_cleaned': os.path.exists(os.path.join(sess_dir, 'cleaned.pkl')),
        'original_file': None,
        'session_id': _get_session_id()
    }
    for ext in ['csv', 'xlsx', 'xls']:
        path = os.path.join(sess_dir, f'original.{ext}')
        if os.path.exists(path):
            info['original_file'] = f'original.{ext}'
            break
    return info


def cleanup_old_sessions():
    """Delete session directories older than max_age_hours."""
    from config import SESSION_CLEANUP_HOURS
    now = time.time()
    max_age = SESSION_CLEANUP_HOURS * 3600
    if not os.path.exists(UPLOAD_FOLDER):
        return
    for name in os.listdir(UPLOAD_FOLDER):
        dir_path = os.path.join(UPLOAD_FOLDER, name)
        if os.path.isdir(dir_path):
            mtime = os.path.getmtime(dir_path)
            if now - mtime > max_age:
                import shutil
                shutil.rmtree(dir_path, ignore_errors=True)
