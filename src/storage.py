import json
import os
import uuid
from datetime import datetime
from typing import Optional
from src.config import IMAGES_DIR, METADATA_PATH, ensure_directories

def load_memories() -> list:
    ensure_directories()
    if not os.path.exists(METADATA_PATH):
        return []
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_memory(title: str, description: str, uploaded_file, ocr_text: str) -> dict:
    ensure_directories()
    
    memory_id = str(uuid.uuid4())
    ext = uploaded_file.name.split(".")[-1].lower()
    image_filename = f"{memory_id}.{ext}"
    image_path = os.path.join(IMAGES_DIR, image_filename)

    with open(image_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    memory_record = {
        "id": memory_id,
        "title": title.strip(),
        "description": description.strip(),
        "image_path": f"data/images/{image_filename}",
        "ocr_text": ocr_text,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    memories = load_memories()
    memories.insert(0, memory_record)

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=4, ensure_ascii=False)

    return memory_record

def image_path_for(memory_record: dict) -> str:
    return memory_record.get("image_path", "")

def _safe_image_path_within_dir(image_path_str: Optional[str]) -> Optional[str]:
    if not image_path_str:
        return None
    filename = os.path.basename(image_path_str)
    if not filename:
        return None
    full_path = os.path.join(IMAGES_DIR, filename)
    try:
        real_images_dir = os.path.realpath(IMAGES_DIR)
        real_full_path = os.path.realpath(full_path)
        if os.path.commonpath([real_images_dir, real_full_path]) == real_images_dir:
            return full_path
    except Exception:
        pass
    return None

def delete_memory(memory_id: str) -> dict:
    ensure_directories()
    if not memory_id:
        return {"deleted": False, "reason": "invalid_id"}
    
    memories = load_memories()
    target_memory = None
    remaining_memories = []
    
    for mem in memories:
        if mem.get("id") == memory_id:
            target_memory = mem
        else:
            remaining_memories.append(mem)
            
    if not target_memory:
        return {"deleted": False, "reason": "not_found"}
        
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(remaining_memories, f, indent=4, ensure_ascii=False)
        
    image_deleted = False
    image_missing = False
    img_path_str = target_memory.get("image_path") or target_memory.get("image_filename")
    safe_path = _safe_image_path_within_dir(img_path_str)
    
    if safe_path and os.path.exists(safe_path):
        try:
            os.remove(safe_path)
            image_deleted = True
        except Exception:
            pass
    elif safe_path:
        image_missing = True
        
    return {
        "deleted": True,
        "memory_id": memory_id,
        "image_deleted": image_deleted,
        "image_missing": image_missing
    }