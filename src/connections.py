from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from src.qa import _tokenize, _STOPWORDS

@dataclass
class RelatedMemory:
    memory_id: str
    title: str
    created_at: str
    image_filename: Optional[str]
    score: float
    reason: str
    snippet: str

def _safe_text(val: Any) -> str:
    if val is None:
        return ""
    return str(val)

def _best_snippet(text: str, query_tokens: list, max_chars: int = 160) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    best_idx = -1
    for token in query_tokens:
        idx = text_lower.find(token.lower())
        if idx != -1:
            best_idx = idx
            break
    if best_idx == -1:
        snippet = text[:max_chars].strip()
        return snippet + ("..." if len(text) > max_chars else "")
    start = max(0, best_idx - 60)
    end = min(len(text), start + max_chars)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet

DEFAULT_MIN_SCORE = 1.5

def related_memories(selected_memory: Dict[str, Any], all_memories: List[Dict[str, Any]], *, min_score: float = DEFAULT_MIN_SCORE, top_k: int = 5) -> List[RelatedMemory]:
    if not selected_memory or not isinstance(selected_memory, dict):
        return []
        
    sel_id = selected_memory.get("id")
    sel_title = _safe_text(selected_memory.get("title"))
    sel_desc = _safe_text(selected_memory.get("description"))
    sel_ocr = _safe_text(selected_memory.get("ocr_text"))
    
    # Tokenize selected memory fields
    sel_title_tokens = set(_tokenize(sel_title))
    sel_desc_tokens = set(_tokenize(sel_desc))
    sel_ocr_tokens = set(_tokenize(sel_ocr))
    
    all_tokens = sel_title_tokens | sel_desc_tokens | sel_ocr_tokens
    if not all_tokens:
        return []
        
    scored_relatives: List[RelatedMemory] = []
    
    for mem in all_memories:
        if not isinstance(mem, dict):
            continue
        m_id = mem.get("id")
        
        # Exclude self by id if id exists, otherwise compare reference
        if sel_id is not None and m_id is not None and sel_id == m_id:
            continue
            
        m_title = _safe_text(mem.get("title"))
        m_desc = _safe_text(mem.get("description"))
        m_ocr = _safe_text(mem.get("ocr_text"))
        
        m_title_tokens = set(_tokenize(m_title))
        m_desc_tokens = set(_tokenize(m_desc))
        m_ocr_tokens = set(_tokenize(m_ocr))
        
        score = 0.0
        shared_terms = []
        
        # Weighted overlap: title matches worth more than description, which are worth more than OCR
        common_title = sel_title_tokens & m_title_tokens
        if common_title:
            score += len(common_title) * 4.0
            shared_terms.extend(list(common_title))
            
        common_desc = sel_desc_tokens & m_desc_tokens
        if common_desc:
            score += len(common_desc) * 2.0
            shared_terms.extend(list(common_desc))
            
        common_ocr = all_tokens & m_ocr_tokens
        if common_ocr:
            pure_ocr = common_ocr - common_title - common_desc
            if pure_ocr:
                score += len(pure_ocr) * 1.0
                shared_terms.extend(list(pure_ocr))
                
        if score >= min_score:
            combined_text = f"{m_title} {m_desc} {m_ocr}"
            list_tokens_for_snippet = list(sel_title_tokens | sel_desc_tokens) or list(all_tokens)
            snippet = _best_snippet(combined_text, list_tokens_for_snippet)
            
            unique_shared = sorted(list(set(shared_terms)))
            if common_title:
                reason = f"Shares title keyword(s): {', '.join(sorted(list(common_title)))}"
            elif common_desc:
                reason = f"Shares description term(s): {', '.join(sorted(list(common_desc)))}"
            else:
                reason = f"Shares keyword(s): {', '.join(unique_shared[:3])}"
                
            scored_relatives.append(RelatedMemory(
                memory_id=m_id or "",
                title=m_title or "Untitled",
                created_at=_safe_text(mem.get("created_at")),
                image_filename=mem.get("image_path"),
                score=score,
                reason=reason,
                snippet=snippet
            ))
            
    scored_relatives.sort(key=lambda x: (-x.score, x.title))
    
    seen_ids = set()
    unique_relatives = []
    for rel in scored_relatives:
        if rel.memory_id and rel.memory_id not in seen_ids:
            seen_ids.add(rel.memory_id)
            unique_relatives.append(rel)
        elif not rel.memory_id:
            unique_relatives.append(rel)
            
    return unique_relatives[:top_k]