import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
"""LLM-диспетчер Джарвиса.

Принимает фразу пользователя, отдаёт её локальной модели (Ollama) вместе со
списком инструментов. Модель либо вызывает инструмент (открыть программу,
громкость, поиск в интернете...), либо отвечает коротким текстом.

Модель только ВЫБИРАЕТ действие. Само действие выполняет код проекта
(executors), так что опасные вещи вроде выключения ПК остаются под контролем.
"""
import datetime
import inspect
import re
import threading

from config.profile_manager import ProfileManager

try:
    import ollama
except ImportError:
    ollama = None

MODEL = "qwen3:4b-instruct-2507-q4_K_M"
OLLAMA_HOST = "http://127.0.0.1:11434"
KEEP_ALIVE = "30m"
OPTIONS = {
    "temperature": 0.3,
    "num_ctx": 4096,
    "num_predict": 220,
}
MAX_HISTORY = 6      # сколько последних реплик помнить
MAX_TOOL_CALLS = 3   # максимум инструментов за одну фразу

CONTROL_REPLIES = {"SLEEP_MODE", "SHUTDOWN", "CONFIRM_SHUTDOWN_PC"}

WEEKDAYS = ["понедельник", "вторник", "среда", "четверг",
            "пятница", "суббота", "воскресенье"]


def _tool(name: str, description: str, properties=None, required=None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
            },
        },
    }


TOOLS = [
    _tool(
        "open_app",
        "Открыть или запустить программу на компьютере.",
        {"name": {
            "type": "string",
            "description": "Название программы латиницей, как у exe-файла: "
                           "chrome, telegram, discord, steam, code, notepad",
        }},
        ["name"],
    ),
    _tool(
        "set_volume",
        "Установить громкость компьютера на точное значение.",
        {"percent": {"type": "integer",
                     "description": "Громкость от 0 до 100"}},
        ["percent"],
    ),
    _tool(
        "change_volume",
        "Изменить громкость относительно текущей: громче или тише.",
        {"delta": {"type": "integer",
                   "description": "Положительное число — громче, "
                                  "отрицательное — тише. Обычно 10."}},
        ["delta"],
    ),
    _tool(
        "set_mute",
        "Выключить или включить звук на компьютере.",
        {"muted": {"type": "boolean",
                   "description": "true — выключить звук, false — включить"}},
        ["muted"],
    ),
    _tool(
        "web_search",
        "Поиск в интернете. Для свежей и фактической информации: новости, "
        "погода, курсы валют, цены, события, незнакомые термины.",
        {"query": {"type": "string",
                   "description": "Поисковый запрос"}},
        ["query"],
    ),
    _tool(
        "sleep_mode",
        "Уйти в режим сна: Джарвис замолчит до команды 'проснись'.",
    ),
    _tool(
        "exit_jarvis",
        "Закрыть программу Джарвис (компьютер остаётся включённым).",
    ),
    _tool(
        "shutdown_pc",
        "Выключить компьютер. Перед выполнением будет запрошено "
        "подтверждение.",
    ),
]


class Dispatcher:

    def __init__(self, executors: dict | None = None):
        """executors: {имя_инструмента: функция(**аргументы) -> str}."""
        self.executors = executors or {}
        self.profile = ProfileManager()
        self.history: list[dict] = []
        self.client = None

        if ollama is None:
            print("Dispatcher: пакет ollama не установлен (pip install ollama)")
        else:
            self.client = ollama.Client(host=OLLAMA_HOST)
            print(f"Dispatcher готов [OK] (модель {MODEL})")

    # ------------------------------------------------------------------ API

    def warmup(self):
        """Загружает модель в видеопамять заранее (в фоне), чтобы первый
        ответ не ждал загрузки."""
        if self.client is None:
            return

        def _load():
            try:
                self.client.chat(
                    model=MODEL,
                    messages=[{"role": "user", "content": "ок"}],
                    options={"num_ctx": OPTIONS["num_ctx"], "num_predict": 1},
                    keep_alive=KEEP_ALIVE,
                )
                print("Модель прогрета [OK]")
            except Exception as e:
                print(f"Прогрев модели не удался: {e}")

        threading.Thread(target=_load, daemon=True).start()

    def ask(self, question: str) -> str:
        """Возвращает текст для озвучки или служебный ответ из CONTROL_REPLIES."""
        if self.client is None:
            return self._with_honorific(
                "Модель не подключена, не установлен пакет ollama")

        messages = [
            {"role": "system", "content": self._system_prompt()},
            *self.history,
            {"role": "user", "content": question},
        ]

        try:
            response = self._chat(messages, tools=TOOLS)
            message = response.message
            calls = list(message.tool_calls or [])[:MAX_TOOL_CALLS]

            if calls:
                answer = self._run_tools(calls, messages, message)
            else:
                answer = message.content or ""
        except Exception as e:
            print(f"Dispatcher ошибка: {e}")
            return self._with_honorific(
                "Не могу связаться с моделью. Проверьте, запущен ли Ollama")

        if answer in CONTROL_REPLIES:
            return answer

        answer = self._clean_for_speech(answer)
        if not answer:
            answer = self._with_honorific("Не понял, повторите, пожалуйста")

        self._remember(question, answer)
        return answer

    # ------------------------------------------------------------- internals

    def _chat(self, messages: list, tools: list | None = None):
        return self.client.chat(
            model=MODEL,
            messages=messages,
            tools=tools,
            options=OPTIONS,
            keep_alive=KEEP_ALIVE,
        )

    def _run_tools(self, calls: list, messages: list, assistant_message) -> str:
        results = []
        for call in calls:
            name = call.function.name
            args = call.function.arguments or {}
            print(f"[инструмент] {name}({args})")
            result = self._execute(name, args)
            if result in CONTROL_REPLIES:
                return result
            results.append((name, result))

        # Поиску нужен второй проход: модель формулирует ответ по результатам.
        # Остальные действия возвращают готовую фразу, без лишнего вызова LLM.
        if any(name == "web_search" for name, _ in results):
            messages.append(assistant_message)
            for name, result in results:
                messages.append(
                    {"role": "tool", "tool_name": name, "content": result})
            final = self._chat(messages)  # без tools: просто ответ
            return final.message.content or ""

        return ". ".join(result for _, result in results)

    def _execute(self, name: str, args) -> str:
        func = self.executors.get(name)
        if func is None:
            return "Такого действия у меня нет"
        if not isinstance(args, dict):
            args = {}
        # модель иногда добавляет лишние поля: оставляем только нужные
        accepted = inspect.signature(func).parameters
        args = {k: v for k, v in args.items() if k in accepted}
        try:
            return str(func(**args))
        except Exception as e:
            print(f"Ошибка инструмента {name}: {e}")
            return "Не получилось выполнить действие"

    def _system_prompt(self) -> str:
        now = datetime.datetime.now()
        return (
            f"Ты — Джарвис, голосовой ассистент на компьютере пользователя. "
            f"Пользователя зовут {self.profile.name}, обращайся к нему "
            f"«{self.profile.honorific}».\n"
            f"Сейчас {now:%d.%m.%Y}, {WEEKDAYS[now.weekday()]}, "
            f"{now:%H:%M}.\n"
            "Правила:\n"
            "- Твои ответы озвучиваются голосом: говори по-русски, коротко "
            "(1-3 предложения), без списков, markdown, эмодзи и ссылок.\n"
            "- Если просят что-то сделать на компьютере, вызови подходящий "
            "инструмент. Не выдумывай действия, которых нет в инструментах.\n"
            "- Для свежих и фактических данных (новости, погода, курсы, цены, "
            "события) используй web_search.\n"
            "- На обычные вопросы и разговор отвечай сам, без инструментов.\n"
            "- Если просьба непонятна, задай один короткий уточняющий вопрос."
        )

    def _remember(self, question: str, answer: str):
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": answer})
        self.history = self.history[-MAX_HISTORY:]

    def _with_honorific(self, text: str) -> str:
        return f"{text}, {self.profile.honorific}"

    @staticmethod
    def _clean_for_speech(text: str) -> str:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"[*_#`>~|]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
