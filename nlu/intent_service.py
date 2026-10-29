from nlu.schemas import IntentResult
from nlu.normalizer import normalize_text
from nlu.local_classifier import LocalIntentClassifier

LOCAL_MIN_CONFIDENCE = 0.5


class IntentService:
    """Разбор фразы в IntentResult.

    Основной путь — локальный классификатор (миллисекунды, без LLM).
    Если уверенность низкая:
      - use_llm_fallback=False (по умолчанию): считаем фразу обычным разговором,
        ответит chat-модель Ollama (короткий промпт);
      - use_llm_fallback=True: старый путь через Ollama.classify (медленно на
        слабой видеокарте, включайте только если нужно).
    """

    def __init__(self, ollama_client=None, use_llm_fallback: bool = False):
        self.ollama = ollama_client
        self.use_llm_fallback = use_llm_fallback
        self.local = LocalIntentClassifier()

    def classify(self, text: str) -> IntentResult:
        normalized = normalize_text(text)
        result = self.local.classify(normalized)
        result.raw = normalized

        if result.confidence >= LOCAL_MIN_CONFIDENCE:
            return result

        if self.use_llm_fallback and self.ollama is not None:
            llm_result = self.ollama.classify(normalized)
            llm_result.raw = normalized
            return llm_result

        return IntentResult(intent="chat", confidence=result.confidence, raw=normalized)