import json
import re
import requests
from dataclasses import dataclass
from typing import Optional


OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "mistral"


INTENT_SYSTEM_PROMPT = """
Ты — модуль классификации намерений голосового ассистента «Джарвис».
Твоя единственная задача — анализировать команду пользователя и возвращать
ТОЛЬКО JSON без каких-либо пояснений, текста до/после, markdown-блоков.

Возможные значения поля "intent":
  "open_website"   — открыть сайт/веб-сервис
  "open_app"       — открыть локальное приложение или игру
  "open_folder"    — открыть папку на компьютере
  "system"         — системная команда (звук, скриншот, выключение и т.п.)
  "media"          — управление воспроизведением (пауза, следующий трек)
  "chat"           — свободный разговор, вопрос, нет явного действия

Поля ответа:
  intent          — одно из перечисленных выше
  target_ru       — что открыть/сделать (русское/транслит написание из команды)
  target_en       — английское/латинское написание (для поиска файла на диске)
  url             — URL если intent == open_website, иначе null
  confidence      — уверенность 0.0–1.0
  chat_reply      — если intent == chat, ответ пользователю; иначе null

Примеры:

Команда: "открой ютуб"
{"intent":"open_website","target_ru":"ютуб","target_en":"youtube","url":"https://youtube.com","confidence":0.99,"chat_reply":null}

Команда: "открой аркнайтс эндфилд"
{"intent":"open_app","target_ru":"аркнайтс эндфилд","target_en":"Arknights Endfield","url":null,"confidence":0.95,"chat_reply":null}

Команда: "запусти стим"
{"intent":"open_app","target_ru":"стим","target_en":"Steam","url":null,"confidence":0.97,"chat_reply":null}

Команда: "открой папку загрузки"
{"intent":"open_folder","target_ru":"загрузки","target_en":"Downloads","url":null,"confidence":0.98,"chat_reply":null}

Команда: "выключи звук"
{"intent":"system","target_ru":"выключить звук","target_en":"mute","url":null,"confidence":0.99,"chat_reply":null}

Команда: "привет, как дела?"
{"intent":"chat","target_ru":null,"target_en":null,"url":null,"confidence":0.99,"chat_reply":"Всё отлично! Чем могу помочь?"}

Команда: "какая столица Франции?"
{"intent":"chat","target_ru":null,"target_en":null,"url":null,"confidence":0.99,"chat_reply":"Столица Франции — Париж."}
"""


@dataclass
class IntentResult:
    intent:      str
    target_ru:   Optional[str]
    target_en:   Optional[str]
    url:         Optional[str]
    confidence:  float
    chat_reply:  Optional[str]
    raw:         str


class OllamaHandler:
    def __init__(self,
                 model: str = OLLAMA_MODEL,
                 base_url: str = OLLAMA_BASE_URL,
                 timeout: int = 15):
        self.model    = model
        self.base_url = base_url
        self.timeout  = timeout
        self._chat_history = []


    def classify(self, user_text: str) -> IntentResult:
        raw = self._ask(
            system=INTENT_SYSTEM_PROMPT,
            user=user_text,
            temperature=0.1,
        )
        return self._parse_intent(raw, user_text)

    def chat(self, user_text: str) -> str:
        self._chat_history.append({"role": "user", "content": user_text})

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты — голосовой ассистент Джарвис. "
                        "Отвечай кратко, по-русски, без лишних слов."
                    )
                },
                *self._chat_history
            ],
            "stream": False,
            "options": {"temperature": 0.7},
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            reply = resp.json()["message"]["content"].strip()
        except Exception as e:
            print(f"[Ollama] Ошибка chat: {e}")
            reply = "Извини, не смог подключиться к AI."

        self._chat_history.append({"role": "assistant", "content": reply})

        if len(self._chat_history) > 20:
            self._chat_history = self._chat_history[-20:]

        return reply

    def reset_history(self):
        self._chat_history.clear()

    def _ask(self, system: str, user: str, temperature: float = 0.3) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
        except requests.exceptions.ConnectionError:
            print("[Ollama] Сервер недоступен (ollama serve запущен?)")
            return ""
        except Exception as e:
            print(f"[Ollama] Ошибка: {e}")
            return ""

    def _parse_intent(self, raw: str, original_text: str) -> IntentResult:
        json_str = self._extract_json(raw)
        try:
            data = json.loads(json_str)
            return IntentResult(
                intent     = data.get("intent", "chat"),
                target_ru  = data.get("target_ru"),
                target_en  = data.get("target_en"),
                url        = data.get("url"),
                confidence = float(data.get("confidence", 0.5)),
                chat_reply = data.get("chat_reply"),
                raw        = raw,
            )
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[Ollama] Не удалось разобрать JSON: {e}\nСырой ответ: {raw!r}")
            return IntentResult(
                intent="chat",
                target_ru=None,
                target_en=None,
                url=None,
                confidence=0.0,
                chat_reply="Не смог разобрать команду.",
                raw=raw,
            )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Извлекает первый {...} блок из строки."""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text