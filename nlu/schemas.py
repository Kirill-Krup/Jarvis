from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class IntentResult:
    intent: str
    target_ru: Optional[str] = None
    target_en: Optional[str] = None
    url: Optional[str] = None
    confidence: float = 0.0
    chat_reply: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    candidates: List[str] = field(default_factory=list)
    raw: str = ""