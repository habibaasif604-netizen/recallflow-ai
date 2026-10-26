import json
import os
from src.config import PREFERENCES_FILE, DEFAULT_TZ, ensure_directories

def load_preferences() -> dict:
    ensure_directories()
    if not os.path.exists(PREFERENCES_FILE):
        return {
            "briefing_time": "08:00",
            "days_before_deadline": 1,
            "timezone": DEFAULT_TZ
        }
    try:
        with open(PREFERENCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "briefing_time": "08:00",
            "days_before_deadline": 1,
            "timezone": DEFAULT_TZ
        }

def save_preferences(prefs: dict):
    ensure_directories()
    with open(PREFERENCES_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=4, ensure_ascii=False)