import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
METADATA_PATH = os.path.join(DATA_DIR, "memories.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
PREFERENCES_FILE = os.path.join(DATA_DIR, "preferences.json")
REMINDER_LOG_FILE = os.path.join(DATA_DIR, "reminder_log.json")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# Environment-driven configurations
JOB_TOKEN = os.environ.get("RECALLFLOW_JOB_TOKEN", "")
DEFAULT_TZ = os.environ.get("RECALLFLOW_TZ", "UTC")

def ensure_directories():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)