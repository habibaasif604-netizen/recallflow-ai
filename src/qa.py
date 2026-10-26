import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from src.storage import load_memories

@dataclass
class FieldMatch:
    field_name: str  # "title", "description", or "ocr_text"
    snippet: str
    provenance_label: str

@dataclass
class MemoryAnswer:
    memory_id: str
    title: str
    created_at: str
    image_filename: Optional[str]
    score: float
    matches: List[FieldMatch]
    extracted_dates: List[str]

@dataclass
class AskResult:
    question: str
    answers: List[MemoryAnswer]
    has_conflicts: bool
    conflict_message: Optional[str]
    no_results: bool

# Basic English stopwords to filter out from questions so we search meaningful terms
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", 
    "with", "by", "from", "up", "about", "into", "over", "after", "is", 
    "are", "was", "were", "be", "been", "being", "have", "has", "had", 
    "do", "does", "did", "will", "would", "shall", "should", "may", 
    "might", "must", "can", "could", "i", "you", "he", "she", "it", "we", 
    "they", "my", "your", "his", "her", "its", "our", "their", "this", 
    "that", "these", "those", "what", "which", "who", "whom", "where", 
    "when", "why", "how", "not", "no", "so", "if", "than", "too", "very",
    "just", "show", "find", "get", "tell", "me", "please", "search"
}

def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS]

def _extract_snippets(text: str, query_tokens: List[str], max_chars: int = 160) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    
    best_idx = -1
    for token in query_tokens:
        idx = text_lower.find(token)
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

def _extract_dates(text: str) -> List[str]:
    if not text:
        return []
    iso_matches = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    return list(set(iso_matches))

def answer_question(question: str) -> AskResult:
    if not question or not question.strip():
        return AskResult(question="", answers=[], has_conflicts=False, conflict_message=None, no_results=True)
        
    q_tokens = _tokenize(question)
    if not q_tokens:
        q_tokens = [t for t in re.findall(r"\b[a-z0-9]+\b", question.lower()) if len(t) > 1]
        if not q_tokens:
            return AskResult(question=question, answers=[], has_conflicts=False, conflict_message=None, no_results=True)

    memories = load_memories()
    scored_answers: List[MemoryAnswer] = []
    
    for mem in memories:
        title = mem.get("title", "")
        desc = mem.get("description", "")
        ocr = mem.get("ocr_text", "")
        
        title_lower = title.lower()
        desc_lower = desc.lower()
        ocr_lower = ocr.lower()
        
        score = 0.0
        matches = []
        
        title_hits = sum(1 for t in q_tokens if t in title_lower)
        desc_hits = sum(1 for t in q_tokens if t in desc_lower)
        ocr_hits = sum(1 for t in q_tokens if t in ocr_lower)
        
        if title_hits > 0:
            score += title_hits * 5.0
            matches.append(FieldMatch(
                field_name="title",
                snippet=_extract_snippets(title, q_tokens),
                provenance_label="from memory title"
            ))
            
        if desc_hits > 0:
            score += desc_hits * 3.0
            matches.append(FieldMatch(
                field_name="description",
                snippet=_extract_snippets(desc, q_tokens),
                provenance_label="from description / notes"
            ))
            
        if ocr_hits > 0:
            score += ocr_hits * 1.0
            matches.append(FieldMatch(
                field_name="ocr_text",
                snippet=_extract_snippets(ocr, q_tokens),
                provenance_label="from extracted OCR text"
            ))
                
        if score > 0.0:
            combined_text = f"{title} {desc} {ocr}"
            dates = _extract_dates(combined_text)
            scored_answers.append(MemoryAnswer(
                memory_id=mem.get("id", ""),
                title=title or "Untitled",
                created_at=mem.get("created_at", ""),
                image_filename=mem.get("image_path"),
                score=score,
                matches=matches,
                extracted_dates=dates
            ))

    scored_answers.sort(key=lambda x: x.score, reverse=True)
    
    seen_ids = set()
    unique_answers = []
    for ans in scored_answers:
        if ans.memory_id not in seen_ids:
            seen_ids.add(ans.memory_id)
            unique_answers.append(ans)
            
    if not unique_answers:
        return AskResult(question=question, answers=[], has_conflicts=False, conflict_message=None, no_results=True)
        
    all_dates_found = set()
    for ans in unique_answers[:3]:
        for d in ans.extracted_dates:
            all_dates_found.add(d)
            
    has_conflicts = len(all_dates_found) > 1
    conflict_msg = None
    if has_conflicts:
        conflict_msg = f"⚠️ Note: Multiple differing dates found across top matching memories ({', '.join(all_dates_found)}). Please verify which record is most current."

    return AskResult(
        question=question,
        answers=unique_answers[:5],
        has_conflicts=has_conflicts,
       conflict_message=conflict_msg,
        no_results=False
    )