import json
import os
import uuid
from datetime import datetime
from typing import Optional
from src.config import TASKS_FILE, ensure_directories

def load_tasks() -> list:
    ensure_directories()
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_task(task_data: dict) -> dict:
    ensure_directories()
    tasks = load_tasks()
    
    task_record = {
        "id": str(uuid.uuid4()),
        "text": task_data.get("text", "").strip(),
        "memory_id": task_data.get("memory_id"),
        "image_filename": task_data.get("image_filename"),
        "due_date": task_data.get("due_date"),
        "priority": task_data.get("priority", "medium"),
        "completed": False,
        "provenance": task_data.get("provenance", "confirmed"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    tasks.insert(0, task_record)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
    
    return task_record

def save_tasks(task_list: list) -> list:
    saved = []
    for t in task_list:
        saved.append(save_task(t))
    return saved

def update_task(task_id: str, *, text: str, due_date: Optional[str], priority: str) -> Optional[dict]:
    ensure_directories()
    tasks = load_tasks()
    updated = None
    for t in tasks:
        if t.get("id") == task_id:
            t["text"] = text.strip()
            t["due_date"] = due_date
            t["priority"] = priority
            t["provenance"] = "edited"
            updated = t
            break
    if updated:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)
    return updated

def set_completed(task_id: str, completed: bool):
    tasks = load_tasks()
    for t in tasks:
        if t.get("id") == task_id:
            t["completed"] = completed
            break
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)

def delete_task(task_id: str):
    tasks = load_tasks()
    tasks = [t for t in tasks if t.get("id") != task_id]
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)