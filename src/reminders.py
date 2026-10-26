import json
import os
from datetime import datetime, date
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from src.config import REMINDER_LOG_FILE, DEFAULT_TZ, ensure_directories
from src.tasks_storage import load_tasks
from src.preferences import load_preferences

def _get_local_now() -> datetime:
    prefs = load_preferences()
    tz_str = prefs.get("timezone", DEFAULT_TZ)
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)

def load_reminder_log() -> list:
    ensure_directories()
    if not os.path.exists(REMINDER_LOG_FILE):
        return []
    try:
        with open(REMINDER_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_reminder_log(log: list):
    ensure_directories()
    with open(REMINDER_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=4, ensure_ascii=False)

def load_reminder_history() -> list:
    log = load_reminder_log()
    history = []
    for entry in reversed(log):
        history.append({
            "task_id": entry.get("task_id"),
            "text": entry.get("text"),
            "due_date": entry.get("due_date"),
            "reason": entry.get("reason"),
            "notified_at": entry.get("notified_at")
        })
    return history

def run_deadline_check(notifier_fn=None, dry_run: bool = False) -> dict:
    ensure_directories()
    now = _get_local_now()
    today_str = now.date().isoformat()
    
    prefs = load_preferences()
    days_before = prefs.get("days_before_deadline", 1)
    
    tasks = load_tasks()
    log = load_reminder_log()
    
    reminded_keys = set((item.get("task_id"), item.get("due_date")) for item in log)
    
    overdue = []
    due_today = []
    reminders_sent = []
    reminders_skipped = []
    
    for t in tasks:
        if t.get("completed", False):
            continue
        due = t.get("due_date")
        if not due:
            continue
            
        try:
            due_d = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            continue
            
        today_d = now.date()
        
        if due_d < today_d:
            overdue.append(t)
        elif due_d == today_d:
            due_today.append(t)
            
        delta_days = (due_d - today_d).days
        is_due_for_reminder = (delta_days <= days_before)
        
        if is_due_for_reminder:
            key = (t.get("id"), due)
            if key in reminded_keys:
                reminders_skipped.append({
                    "task_id": t.get("id"),
                    "text": t.get("text"),
                    "due_date": due,
                    "reason": "already_notified_for_this_deadline"
                })
            else:
                reason = "overdue" if delta_days < 0 else ("due_today" if delta_days == 0 else "upcoming_deadline")
                reminders_sent.append({
                    "task_id": t.get("id"),
                    "text": t.get("text"),
                    "due_date": due,
                    "reason": reason
                })
                
                if notifier_fn and not dry_run:
                    try:
                        notifier_fn(t, reason)
                    except Exception:
                        pass
                        
                if not dry_run:
                    log.append({
                        "task_id": t.get("id"),
                        "text": t.get("text"),
                        "due_date": due,
                        "reason": reason,
                        "notified_at": now.strftime("%Y-%m-%d %H:%M:%S")
                    })

    if not dry_run and reminders_sent:
        save_reminder_log(log)

    return {
        "checked_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": str(now.tzinfo),
        "total_tasks_scanned": len(tasks),
        "overdue": [t.get("text") for t in overdue],
        "due_today": [t.get("text") for t in due_today],
        "reminders_sent": reminders_sent,
        "reminders_skipped": reminders_skipped,
        "dry_run": dry_run
    }