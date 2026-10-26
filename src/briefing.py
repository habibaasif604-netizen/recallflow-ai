import os
from datetime import datetime, date
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from src.config import DEFAULT_TZ, ensure_directories
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

def get_daily_briefing() -> dict:
    ensure_directories()
    now = _get_local_now()
    today = now.date()
    
    tasks = load_tasks()
    
    overdue = []
    due_today = []
    upcoming = []
    completed = []
    
    for t in tasks:
        if t.get("completed", False):
            completed.append(t)
            continue
            
        due = t.get("due_date")
        if not due:
            continue
            
        try:
            due_date = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            continue
            
        if due_date < today:
            overdue.append(t)
        elif due_date == today:
            due_today.append(t)
        else:
            upcoming.append(t)
            
    return {
        "date": today.isoformat(),
        "timezone": str(now.tzinfo),
        "overdue": overdue,
        "due_today": due_today,
        "upcoming": upcoming,
        "completed": completed
    }

# --- SMART DAILY PLANNER LOGIC ---

_PRIORITY_RANK = {"high": 0, "normal": 1, "low": 2}
_PLAN_LABELS = {
    "overdue": ("🔥 Overdue", "Overdue"),
    "today": ("🎯 Due Today", "Due today"),
    "upcoming": ("⏳ Upcoming", "Upcoming"),
    "later": ("📅 Later", "Future deadline"),
    "undated": ("📌 No Due Date", "No due date")
}

def plan_tasks() -> list:
    """
    Returns a sorted list of active (non-completed) tasks for the Smart Daily Plan.
    Ordering: Overdue -> Due Today -> Upcoming -> Later -> Undated.
    Within each group: High -> Medium (normal) -> Low priority, then by due date (earliest first).
    Attaches 'plan_group' and 'plan_reason' fields to each returned dict without mutating stored tasks.
    """
    tasks = load_tasks()
    now = _get_local_now()
    today = now.date()

    overdue_list = []
    today_list = []
    upcoming_list = []
    later_list = []
    undated_list = []

    for t in tasks:
        if t.get("completed", False):
            continue
        
        # Clone so we don't mutate the raw task dict in memory
        item = dict(t)
        due = item.get("due_date")

        if not due:
            item["_group"] = "undated"
            undated_list.append(item)
            continue

        try:
            due_date = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            item["_group"] = "undated"
            undated_list.append(item)
            continue

        delta = (due_date - today).days
        if delta < 0:
            item["_group"] = "overdue"
            overdue_list.append(item)
        elif delta == 0:
            item["_group"] = "today"
            today_list.append(item)
        elif delta <= 7:
            item["_group"] = "upcoming"
            upcoming_list.append(item)
        else:
            item["_group"] = "later"
            later_list.append(item)

    def _sort_key(task_item):
        prio_str = str(task_item.get("priority", "normal")).lower()
        prio_val = _PRIORITY_RANK.get(prio_str, 1) # default normal/medium = 1
        d_val = task_item.get("due_date") or "9999-12-31"
        return (prio_val, d_val)

    overdue_list.sort(key=_sort_key)
    today_list.sort(key=_sort_key)
    upcoming_list.sort(key=_sort_key)
    later_list.sort(key=_sort_key)
    undated_list.sort(key=_sort_key)

    ordered_groups = [
        ("overdue", overdue_list),
        ("today", today_list),
        ("upcoming", upcoming_list),
        ("later", later_list),
        ("undated", undated_list)
    ]

    final_plan = []
    for group_key, group_items in ordered_groups:
        group_label, base_reason = _PLAN_LABELS[group_key]
        for item in group_items:
            prio_raw = str(item.get("priority", "normal")).lower()
            prio_display = "Medium" if prio_raw == "normal" else prio_raw.capitalize()
            
            due_str = item.get("due_date")
            if due_str and group_key not in ("overdue", "today"):
                reason = f"{base_reason} ({due_str}) · {prio_display} priority"
            else:
                reason = f"{base_reason} · {prio_display} priority"

            item["plan_group"] = group_label
            item["plan_reason"] = reason
            final_plan.append(item)

    return final_plan