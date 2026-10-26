import re
from dataclasses import dataclass
from typing import List, Optional, Callable

try:
    from dateutil import parser as dateutil_parser
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False

@dataclass
class ExtractedTask:
    text: str
    due_date: Optional[str] = None
    priority: str = "medium"  # low, medium, high
    completed: bool = False
    is_ambiguous_date: bool = False
    raw_date_phrase: Optional[str] = None
    provenance: str = "extracted"

def extract_tasks(ocr_text: str, ai_fn: Optional[Callable[[str], List[dict]]] = None) -> List[ExtractedTask]:
    if not ocr_text or not ocr_text.strip():
        return []

    # Optional AI hook fallback if provided
    if ai_fn is not None:
        try:
            ai_results = ai_fn(ocr_text)
            tasks = []
            for item in ai_results:
                tasks.append(ExtractedTask(
                    text=item.get("text", "").strip(),
                    due_date=item.get("due_date"),
                    priority=item.get("priority", "medium"),
                    provenance="ai_suggested"
                ))
            if tasks:
                return tasks
        except Exception:
            pass

    lines = ocr_text.splitlines()
    tasks = []
    
    high_keywords = ["urgent", "asap", "important", "high", "critical", "today"]
    low_keywords = ["low priority", "optional", "someday", "later", "eventually", "low"]

    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue
        
        is_bullet = clean_line.startswith(("-", "*", "•", "[ ]", "[x]", "✔"))
        has_action_verb = any(clean_line.lower().startswith(v) for v in ["buy", "call", "email", "submit", "finish", "complete", "pay", "review", "send", "meet", "check", "do", "prep", "create", "write"])
        
        if is_bullet or has_action_verb or len(clean_line) > 10:
            task_text = clean_line.lstrip("-*•[]x✔ ").strip()
            if not task_text:
                continue

            priority = "medium"
            lower_text = task_text.lower()
            if any(kw in lower_text for kw in low_keywords):
                priority = "low"
            elif any(kw in lower_text for kw in high_keywords):
                priority = "high"

            due_date = None
            is_ambiguous = False
            raw_phrase = None

            iso_date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", task_text)
            if iso_date_match:
                due_date = iso_date_match.group(1)
            elif DATEUTIL_AVAILABLE:
                try:
                    date_cue_match = re.search(r"\b(by|due|on)\s+([A-Za-z0-9,\s]+)", task_text, re.IGNORECASE)
                    if date_cue_match:
                        raw_phrase = date_cue_match.group(2).strip()
                        parsed = dateutil_parser.parse(raw_phrase, fuzzy=True, default=None)
                        if parsed:
                            due_date = parsed.strftime("%Y-%m-%d")
                except Exception:
                    pass

            ambiguous_words = ["tomorrow", "next week", "soon", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for amb in ambiguous_words:
                if f" {amb}" in f" {lower_text}" and not due_date:
                    is_ambiguous = True
                    raw_phrase = amb
                    break

            tasks.append(ExtractedTask(
                text=task_text,
                due_date=due_date,
                priority=priority,
                is_ambiguous_date=is_ambiguous,
                raw_date_phrase=raw_phrase,
                provenance="extracted"
            ))

    return tasks