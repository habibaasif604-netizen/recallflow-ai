def search_memories(memories: list, query: str) -> list:
    if not query or not query.strip():
        return memories
    
    q = query.strip().lower()
    filtered = []
    for m in memories:
        title = m.get("title", "").lower()
        desc = m.get("description", "").lower()
        ocr = m.get("ocr_text", "").lower()

        if q in title or q in desc or q in ocr:
            filtered.append(m)
    return filtered