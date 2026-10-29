import json
import re
import requests
from dataclasses import dataclass
from typing import Optional

OLLAMA_BASE_URL = "http://localhost:11434"

# Одна модель на всё: и разбор команд, и обычный разговор.
# Qwen3 4B Instruct (~2.5 ГБ) целиком помещается в 4 ГБ видеопамяти.
# Установка: ollama pull qwen3:4b-instruct-2507-q4_K_M
MODEL = "qwen3:4b-instruct-2507-q4_K_M"
CLASSIFY_MODEL = MODEL
CHAT_MODEL     = MODEL

KEEP_ALIVE = "30m"   # держать модель в памяти между командами
NUM_CTX    = 4096    # ОДИНАКОВЫЙ во всех запросах, иначе Ollama перезагрузит модель


INTENT_SYSTEM_PROMPT = """
Ты — модуль КЛАССИФИКАЦИИ НАМЕРЕНИЙ голосового ассистента «Джарвис».
Твоя задача — ПРЕОБРАЗОВАТЬ команду пользователя в СТРОГО СТРУКТУРИРОВАННЫЙ JSON.

Важные правила:
1) Отвечай ТОЛЬКО ОДНИМ JSON-объектом.
2) НИКАКОГО текста до или после JSON, НИКАКИХ комментариев, пояснений, markdown.
3) ЕСЛИ команда не является действием (просто вопрос или small talk) — intent="chat".
4) ЕСЛИ ты сомневаешься между несколькими вариантами intent — выбирай "chat".

================ БЕЗОПАСНОСТЬ =================
Системные действия выключения / перезагрузки ОЧЕНЬ ОПАСНЫ.

1) intent="system" + target_en="shutdown"
   МОЖНО СТАВИТЬ ТОЛЬКО ЕСЛИ в тексте ясно сказано:
   - "выключи компьютер"
   - "выключи ноутбук"
   - "выключи пк"
   - "завершить работу компьютера / ноутбука / пк"

2) intent="system" + target_en="restart"
   МОЖНО СТАВИТЬ ТОЛЬКО ЕСЛИ в тексте сказано:
   - "перезагрузи компьютер / ноутбук / пк"
   - "перезагрузка компьютера / ноутбука / пк"

3) Команды ПРО ЗВУК и ПРО МУЗЫКУ НИКОГДА НЕ ДОЛЖНЫ
   становиться shutdown/restart/sleep.
   Примеры:
   - "выключи звук"        → mute
   - "включи звук"         → unmute
   - "сделай громче"       → volume_up
   - "сделай потише"       → volume_down
   - "выключи музыку"      → media.pause или media.next (но НЕ shutdown)

4) Если в команде есть слово "звук", "музыка", "громкость", "тише", "громче" —
   это ВСЕГДА про звук/медиа, НЕ про выключение компьютера.

5) Если в команде есть слова "компьютер", "ноутбук", "пк" БЕЗ слов "перезагрузи", "выключи" —
   НЕ назначай shutdown/restart. Лучше статус или chat.

================ INTENT =================
Поле intent — ОДНО из:
  "open_website"  — открыть сайт, сервис, соцсеть
  "open_app"      — запустить программу, игру, утилиту
  "open_folder"   — открыть папку на компьютере
  "system"        — системное действие (звук, яркость, скриншот, блокировка, выключение и т.п.)
  "media"         — управление воспроизведением (пауза, трек)
  "chat"          — вопрос, разговор, нет явного действия

================ ПОЛЯ JSON =================
Ты ВСЕГДА возвращаешь объект со следующими полями:

intent      — строка, одно из значений выше
target_ru   — цель действия на русском (как слышишь/понимаешь)
target_en   — цель действия на английском (для поиска на диске / системного действия)
url         — строка или null; URL только для open_website, иначе null
confidence  — число от 0.0 до 1.0; твоя уверенность в intent
chat_reply  — строка, если intent == "chat", иначе null

================ ЗНАЧЕНИЯ target_en ДЛЯ system =================
Используй СТРОГО эти значения (если нужно системное действие):

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

================ ЗНАЧЕНИЯ target_en ДЛЯ media =================
  pause, play, next, previous

================ ПРИМЕРЫ =================

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

# ЗВУК — ВСЕГДА НЕ shutdown/restart

Команда: "выключи звук"
{"intent":"system","target_ru":"выключить звук","target_en":"mute","url":null,"confidence":0.99,"chat_reply":null}

Команда: "включи звук"
{"intent":"system","target_ru":"включить звук","target_en":"unmute","url":null,"confidence":0.99,"chat_reply":null}

Команда: "сделай громче"
{"intent":"system","target_ru":"громче","target_en":"volume_up","url":null,"confidence":0.99,"chat_reply":null}

Команда: "сделай потише"
{"intent":"system","target_ru":"тише","target_en":"volume_down","url":null,"confidence":0.99,"chat_reply":null}

Команда: "поставь громкость 50"
{"intent":"system","target_ru":"громкость 50","target_en":"volume_set","url":null,"confidence":0.99,"chat_reply":null}

# ЯРКОСТЬ

Команда: "ярче"
{"intent":"system","target_ru":"ярче","target_en":"brightness_up","url":null,"confidence":0.99,"chat_reply":null}

Команда: "сделай темнее"
{"intent":"system","target_ru":"темнее","target_en":"brightness_down","url":null,"confidence":0.99,"chat_reply":null}

Команда: "поставь яркость 70"
{"intent":"system","target_ru":"яркость 70","target_en":"brightness_set","url":null,"confidence":0.99,"chat_reply":null}

Команда: "яркость второго монитора 40"
{"intent":"system","target_ru":"яркость второго монитора 40","target_en":"brightness_monitor_2","url":null,"confidence":0.98,"chat_reply":null}

# СИСТЕМНЫЕ БЕЗОПАСНЫЕ

Команда: "сделай скриншот"
{"intent":"system","target_ru":"скриншот","target_en":"screenshot","url":null,"confidence":0.99,"chat_reply":null}

Команда: "заблокируй компьютер"
{"intent":"system","target_ru":"блокировка","target_en":"lock","url":null,"confidence":0.99,"chat_reply":null}

# ОПАСНЫЕ КОМАНДЫ — ТОЛЬКО ЯВНО

Команда: "перезагрузи компьютер"
{"intent":"system","target_ru":"перезагрузка компьютера","target_en":"restart","url":null,"confidence":0.99,"chat_reply":null}

Команда: "выключи компьютер"
{"intent":"system","target_ru":"выключение компьютера","target_en":"shutdown","url":null,"confidence":0.99,"chat_reply":null}

Команда: "выключи ноутбук"
{"intent":"system","target_ru":"выключение ноутбука","target_en":"shutdown","url":null,"confidence":0.99,"chat_reply":null}

# МУЛЬТИМОНТОР

Команда: "расширь экраны"
{"intent":"system","target_ru":"расширить экраны","target_en":"display_extend","url":null,"confidence":0.99,"chat_reply":null}

Команда: "дублируй мониторы"
{"intent":"system","target_ru":"дублировать экраны","target_en":"display_duplicate","url":null,"confidence":0.99,"chat_reply":null}

Команда: "переключи на первый экран"
{"intent":"system","target_ru":"первый экран","target_en":"display_primary","url":null,"confidence":0.99,"chat_reply":null}

Команда: "сколько мониторов подключено"
{"intent":"system","target_ru":"информация о мониторах","target_en":"display_info","url":null,"confidence":0.98,"chat_reply":null}

# МЕДИА

Команда: "пауза"
{"intent":"media","target_ru":"пауза","target_en":"pause","url":null,"confidence":0.99,"chat_reply":null}

Команда: "продолжи воспроизведение"
{"intent":"media","target_ru":"продолжить","target_en":"play","url":null,"confidence":0.99,"chat_reply":null}

Команда: "следующий трек"
{"intent":"media","target_ru":"следующий трек","target_en":"next","url":null,"confidence":0.99,"chat_reply":null}

Команда: "предыдущая песня"
{"intent":"media","target_ru":"предыдущий трек","target_en":"previous","url":null,"confidence":0.99,"chat_reply":null}

# ЧАТ

Команда: "привет, как дела?"
{"intent":"chat","target_ru":null,"target_en":null,"url":null,"confidence":0.99,"chat_reply":"Всё отлично! Чем могу помочь?"}

Команда: "какая столица Франции?"
{"intent":"chat","target_ru":null,"target_en":null,"url":null,"confidence":0.99,"chat_reply":"Столица Франции — Париж."}

Команда: "расскажи про чёрные дыры"
{"intent":"chat","target_ru":null,"target_en":null,"url":null,"confidence":0.97,"chat_reply":"Чёрные дыры — это области пространства с настолько сильной гравитацией, что даже свет не может их покинуть."}
"""

def _nullable_str():
    return {"anyOf": [{"type": "string"}, {"type": "null"}]}


INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["open_website", "open_app", "open_folder",
                     "system", "media", "chat"],
        },
        "target_ru":  _nullable_str(),
        "target_en":  _nullable_str(),
        "url":        _nullable_str(),
        "confidence": {"type": "number"},
        "chat_reply": _nullable_str(),
    },
    "required": ["intent", "target_ru", "target_en",
                 "url", "confidence", "chat_reply"],
}


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
            schema=INTENT_SCHEMA,
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
                        "Ты — голосовой ассистент Джарвис. Твои ответы "
                        "озвучиваются голосом: отвечай по-русски, кратко "
                        "(1-3 предложения), без списков, markdown и эмодзи."
                    )
                },
                *self._chat_history
            ],
            "stream": False,
            "keep_alive": KEEP_ALIVE,
            "options": {"temperature": 0.6, "num_ctx": NUM_CTX,
                        "num_predict": 220},
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

    def warmup(self):
        """Загружает модель в память заранее (первый запрос иначе ждёт загрузки)."""
        requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.classify_model,
                "messages": [{"role": "user", "content": "ок"}],
                "stream": False,
                "keep_alive": KEEP_ALIVE,
                "options": {"num_ctx": NUM_CTX, "num_predict": 1},
            },
            timeout=180,
        )

    def _ask(self, model, system, user, temperature=0.3,
             timeout: int = 15, schema=None) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "stream": False,
            "keep_alive": KEEP_ALIVE,
            "options": {"temperature": temperature, "num_ctx": NUM_CTX,
                        "num_predict": 256},
        }
        if schema is not None:
            payload["format"] = schema

        url = f"{self.base_url}/api/chat"
        try:
            resp = requests.post(url, json=payload, timeout=timeout)

            if resp.status_code == 400 and schema is not None:
                # старая версия Ollama не понимает JSON-схему: пробуем без неё
                print("[Ollama] format не поддерживается, повторяю без схемы")
                retry = {k: v for k, v in payload.items() if k != "format"}
                resp = requests.post(url, json=retry, timeout=timeout)

            if resp.status_code == 404:
                print(f"[Ollama] Модель {model} не найдена. "
                      f"Выполните: ollama pull {model}")
                return ""

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