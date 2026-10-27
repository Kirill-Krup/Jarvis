from nlu.schemas import IntentResult
from nlu.normalizer import normalize_text

class IntentService:
    def __init__(self, ollama_client):
        self.ollama = ollama_client

    def classify(self, text: str) -> IntentResult:
        normalized = normalize_text(text)
        result = self.ollama.classify(normalized)
        result.raw = normalized
        return result