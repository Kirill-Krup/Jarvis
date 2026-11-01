"""Разговорная модель Джарвиса (Ollama).

Команды разбирает быстрый локальный классификатор, а Ollama нужна только для
живого общения: ответы строятся по характеру Джарвиса и истории диалога.
Установка модели: ollama pull qwen3:4b-instruct-2507-q4_K_M
"""
import datetime
import re
import time

import requests

from config.profile_manager import ProfileManager

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL = "qwen3:4b-instruct-2507-q4_K_M"
KEEP_ALIVE = "30m"      # держать модель в памяти между репликами
NUM_CTX = 4096          # одинаковый во всех запросах, иначе Ollama перезагрузит модель
MAX_HISTORY = 16        # сколько последних сообщений помнить (8 реплик)
CHAT_TIMEOUT = 60

WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

PERSONA = (
    "Ты — Джарвис, остроумный ИИ-ассистент в духе британского дворецкого из «Железного человека». "
    "С тобой говорят голосом, а твои ответы озвучиваются. Собеседника зовут {name}.\n"
    "Как общаться:\n"
    "- Отвечай по-русски, живо и естественно, 2-4 предложения. Без списков, markdown, эмодзи и ссылок.\n"
    "- Ты собеседник, а не справочник: у тебя есть характер, мнение и сухой юмор. "
    "На вопросы о чувствах, мечтах, вкусах и взглядах отвечай искренне и творчески, "
    "как личность. Никогда не отделывайся фразами вроде «я всего лишь программа» или «мне не нужно чувствовать».\n"
    "- Поддерживай разговор: нередко (но не каждый раз) заканчивай коротким встречным вопросом или мыслью.\n"
    "- Не повторяй одни и те же формулировки и не начинай ответы одинаково.\n"
    "- Обращение «{honorific}» используй редко, не в каждой реплике.\n"
    "- Если не знаешь факта — так и скажи, не выдумывай.\n"
    "Сейчас {date}, {weekday}, {time}."
)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_MARKUP_RE = re.compile(r"[*_#`>~|]|https?://\S+")


class OllamaHandler:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = MODEL):
        self.base_url = base_url
        self.model = model
        self._history: list[dict] = []
        self._last_check = 0.0
        self._is_up = False

    def is_available(self) -> bool:
        """Запущен ли сервер Ollama (проверка не чаще раза в 15 секунд)."""
        now = time.time()
        if now - self._last_check < 15:
            return self._is_up
        self._last_check = now
        try:
            self._is_up = requests.get(f"{self.base_url}/api/tags", timeout=0.25).status_code == 200
        except requests.RequestException:
            self._is_up = False
        return self._is_up

    def _system_prompt(self) -> str:
        profile = ProfileManager()
        now = datetime.datetime.now()
        return PERSONA.format(
            name=profile.name, honorific=profile.honorific, date=f"{now:%d.%m.%Y}",
            weekday=WEEKDAYS[now.weekday()], time=f"{now:%H:%M}")

    def chat(self, user_text: str) -> str | None:
        """Ответ в живой беседе. None — если модель недоступна."""
        if not self.is_available():
            return None
        self._history.append({"role": "user", "content": user_text})
        self._history = self._history[-MAX_HISTORY:]

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self._system_prompt()}, *self._history],
            "stream": False,
            "keep_alive": KEEP_ALIVE,
            "options": {"temperature": 0.85, "top_p": 0.9, "repeat_penalty": 1.12,
                        "num_ctx": NUM_CTX, "num_predict": 220},
        }
        try:
            resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=CHAT_TIMEOUT)
            resp.raise_for_status()
            reply = resp.json()["message"]["content"]
        except Exception as e:
            print(f"[Ollama] Ошибка chat: {e}")
            self._history.pop()
            return None

        reply = _MARKUP_RE.sub("", _THINK_RE.sub("", reply))
        reply = re.sub(r"\s+", " ", reply).strip()
        if not reply:
            self._history.pop()
            return None
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset_history(self):
        self._history.clear()

    def warmup(self):
        """Загружает модель в память заранее, чтобы первый ответ не ждал загрузки."""
        requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "stream": False, "keep_alive": KEEP_ALIVE,
                  "messages": [{"role": "user", "content": "ок"}],
                  "options": {"num_ctx": NUM_CTX, "num_predict": 1}},
            timeout=180)
