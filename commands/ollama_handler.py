import json
import re
import requests
from dataclasses import dataclass
from typing import Optional


OLLAMA_BASE_URL = "http://localhost:11434"

CLASSIFY_MODEL = "qwen2.5:1.5b"
CHAT_MODEL     = "mistral"


INTENT_SYSTEM_PROMPT = """
Ты — модуль классификации намерений голосового ассистента «Джарвис».
Возвращай ТОЛЬКО JSON. Никаких пояснений, markdown, текста до/после.

=== INTENT ===
"open_website"  — открыть сайт, сервис, соцсеть
"open_app"      — запустить программу, игру, утилиту
"open_folder"   — открыть папку на компьютере
"system"        — системное действие (звук, яркость, скриншот, выключение, перезагрузка, блокировка)
"media"         — управление воспроизведением (пауза, трек, перемотка)
"chat"          — вопрос, разговор, нет явного действия

=== ПОЛЯ ===
intent      — одно из выше
target_ru   — цель действия из команды (русский/транслит)
target_en   — английский эквивалент (для поиска на диске / системного действия)
url         — URL только для open_website, иначе null
confidence  — уверенность 0.0–1.0
chat_reply  — ответ если intent==chat, иначе null

=== ЗНАЧЕНИЯ target_en ДЛЯ system ===
Используй СТРОГО эти значения:
  mute, unmute
  volume_up, volume_down, volume_set
  brightness_up, brightness_down, brightness_set
  brightness_monitor_1, brightness_monitor_2, brightness_monitor_3
  screenshot
  lock, restart, shutdown, sleep
  task_manager, explorer, settings, control_panel
  calculator
  display_extend, display_duplicate, display_primary, display_second
  display_info

=== ЗНАЧЕНИЯ target_en ДЛЯ media ===
  pause, play, next, previous

=== ПРИМЕРЫ ===

Команда: "открой ютуб"
{"intent":"open_website","target_ru":"ютуб","target_en":"youtube","url":"https://youtube.com","confidence":0.99,"chat_reply":null}

Команда: "зайди на гитхаб"
{"intent":"open_website","target_ru":"гитхаб","target_en":"github","url":"https://github.com","confidence":0.99,"chat_reply":null}

Команда: "запусти стим"
{"intent":"open_app","target_ru":"стим","target_en":"Steam","url":null,"confidence":0.97,"chat_reply":null}

Команда: "включи телеграм"
{"intent":"open_app","target_ru":"телеграм","target_en":"Telegram","url":null,"confidence":0.97,"chat_reply":null}

Команда: "открой аркнайтс эндфилд"
{"intent":"open_app","target_ru":"аркнайтс эндфилд","target_en":"Arknights Endfield","url":null,"confidence":0.95,"chat_reply":null}

Команда: "открой папку загрузки"
{"intent":"open_folder","target_ru":"загрузки","target_en":"Downloads","url":null,"confidence":0.98,"chat_reply":null}

Команда: "покажи папку с проектами"
{"intent":"open_folder","target_ru":"проекты","target_en":"Projects","url":null,"confidence":0.95,"chat_reply":null}

Команда: "выключи звук"
{"intent":"system","target_ru":"выключить звук","target_en":"mute","url":null,"confidence":0.99,"chat_reply":null}

Команда: "включи звук"
{"intent":"system","target_ru":"включить звук","target_en":"unmute","url":null,"confidence":0.99,"chat_reply":null}

Команда: "громче"
{"intent":"system","target_ru":"громче","target_en":"volume_up","url":null,"confidence":0.99,"chat_reply":null}

Команда: "сделай потише"
{"intent":"system","target_ru":"тише","target_en":"volume_down","url":null,"confidence":0.99,"chat_reply":null}

Команда: "поставь громкость 50"
{"intent":"system","target_ru":"громкость 50","target_en":"volume_set","url":null,"confidence":0.99,"chat_reply":null}

Команда: "ярче"
{"intent":"system","target_ru":"ярче","target_en":"brightness_up","url":null,"confidence":0.99,"chat_reply":null}

Команда: "сделай темнее"
{"intent":"system","target_ru":"темнее","target_en":"brightness_down","url":null,"confidence":0.99,"chat_reply":null}

Команда: "поставь яркость 70"
{"intent":"system","target_ru":"яркость 70","target_en":"brightness_set","url":null,"confidence":0.99,"chat_reply":null}

Команда: "яркость второго монитора 40"
{"intent":"system","target_ru":"яркость второго монитора 40","target_en":"brightness_monitor_2","url":null,"confidence":0.98,"chat_reply":null}

Команда: "сделай скриншот"
{"intent":"system","target_ru":"скриншот","target_en":"screenshot","url":null,"confidence":0.99,"chat_reply":null}

Команда: "заблокируй компьютер"
{"intent":"system","target_ru":"блокировка","target_en":"lock","url":null,"confidence":0.99,"chat_reply":null}

Команда: "перезагрузи компьютер"
{"intent":"system","target_ru":"перезагрузка","target_en":"restart","url":null,"confidence":0.99,"chat_reply":null}

Команда: "выключи компьютер"
{"intent":"system","target_ru":"выключение","target_en":"shutdown","url":null,"confidence":0.99,"chat_reply":null}

Команда: "расширь экраны"
{"intent":"system","target_ru":"расширить экраны","target_en":"display_extend","url":null,"confidence":0.99,"chat_reply":null}

Команда: "дублируй мониторы"
{"intent":"system","target_ru":"дублировать экраны","target_en":"display_duplicate","url":null,"confidence":0.99,"chat_reply":null}

Команда: "переключи на первый экран"
{"intent":"system","target_ru":"первый экран","target_en":"display_primary","url":null,"confidence":0.99,"chat_reply":null}

Команда: "сколько мониторов подключено"
{"intent":"system","target_ru":"информация о мониторах","target_en":"display_info","url":null,"confidence":0.98,"chat_reply":null}

Команда: "пауза"
{"intent":"media","target_ru":"пауза","target_en":"pause","url":null,"confidence":0.99,"chat_reply":null}

Команда: "продолжи воспроизведение"
{"intent":"media","target_ru":"продолжить","target_en":"play","url":null,"confidence":0.99,"chat_reply":null}

Команда: "следующий трек"
{"intent":"media","target_ru":"следующий трек","target_en":"next","url":null,"confidence":0.99,"chat_reply":null}

Команда: "предыдущая песня"
{"intent":"media","target_ru":"предыдущий трек","target_en":"previous","url":null,"confidence":0.99,"chat_reply":null}

Команда: "привет, как дела?"
{"intent":"chat","target_ru":null,"target_en":null,"url":null,"confidence":0.99,"chat_reply":"Всё отлично! Чем могу помочь?"}

Команда: "какая столица Франции?"
{"intent":"chat","target_ru":null,"target_en":null,"url":null,"confidence":0.99,"chat_reply":"Столица Франции — Париж."}

Команда: "расскажи про чёрные дыры"
{"intent":"chat","target_ru":null,"target_en":null,"url":null,"confidence":0.97,"chat_reply":"Чёрные дыры — это области пространства с настолько сильной гравитацией, что даже свет не может их покинуть."}
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
                 classify_model: str = CLASSIFY_MODEL,
                 chat_model: str     = CHAT_MODEL,
                 base_url: str       = OLLAMA_BASE_URL,
                 classify_timeout: int = 30,
                 chat_timeout: int     = 60):
        self.classify_model   = classify_model
        self.chat_model       = chat_model
        self.base_url         = base_url
        self.classify_timeout = classify_timeout
        self.chat_timeout     = chat_timeout
        self._chat_history    = []

    def classify(self, user_text: str) -> IntentResult:
        raw = self._ask(
            model=self.classify_model,
            system=INTENT_SYSTEM_PROMPT,
            user=user_text,
            temperature=0.1,
            timeout=self.classify_timeout,
        )
        return self._parse_intent(raw, user_text)

    def chat(self, user_text: str) -> str:
        self._chat_history.append({"role": "user", "content": user_text})

        payload = {
            "model": self.chat_model,
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
                timeout=self.chat_timeout,
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

    def _ask(self, model, system, user, temperature=0.3, timeout: int = 15) -> str:
        payload = {
            "model": model,
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
                timeout=timeout,
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
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text