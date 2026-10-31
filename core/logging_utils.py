import os
import datetime
from typing import Callable, List

LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "jarvis_debug.log"
)
LOG_FILE = os.path.abspath(LOG_FILE)

_subscribers: List[Callable[[str, str, str], None]] = []


def subscribe_log(cb: Callable[[str, str, str], None]):
    """Подписка на события логов: cb(timestamp, level, message)."""
    if cb not in _subscribers:
        _subscribers.append(cb)


def unsubscribe_log(cb: Callable[[str, str, str], None]):
    if cb in _subscribers:
        _subscribers.remove(cb)


def log(msg: str, level: str = "INFO"):
    """Записывает расширенное лог-сообщение с уровнем и временем."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    level_tag = level.upper()
    line = f"[{timestamp}] [{level_tag}] {msg}"
    print(line, flush=True)

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

    for cb in _subscribers:
        try:
            cb(timestamp, level_tag, msg)
        except Exception:
            pass


def log_voice(msg: str):
    log(msg, "VOICE")


def log_nlu(msg: str):
    log(msg, "NLU")


def log_action(msg: str):
    log(msg, "ACTION")


def log_error(msg: str):
    log(msg, "ERROR")


def log_system(msg: str):
    log(msg, "SYSTEM")


def get_log_file_path() -> str:
    return LOG_FILE
