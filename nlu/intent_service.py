from nlu.schemas import IntentResult
from nlu.normalizer import normalize_text
from nlu.local_classifier import LocalIntentClassifier

LOCAL_MIN_CONFIDENCE = 0.5


class IntentService:
    """Разбор фразы в IntentResult локальным классификатором (миллисекунды, без LLM).

    Если уверенность низкая, фраза считается обычным разговором."""

    def __init__(self):
        self.local = LocalIntentClassifier()

    def classify(self, text: str) -> IntentResult:
        normalized = normalize_text(text)
        result = self.local.classify(normalized)
        result.raw = normalized
        if result.confidence >= LOCAL_MIN_CONFIDENCE:
            return result
        return IntentResult(intent="chat", confidence=result.confidence, raw=normalized)
