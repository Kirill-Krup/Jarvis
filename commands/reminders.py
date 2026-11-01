"""Напоминания и таймеры.

Хранятся в config/reminders.json, поэтому переживают перезапуск Джарвиса.
Когда время пришло, Джарвис произносит напоминание вслух и присылает
уведомление на компьютер или в Telegram (как выбрано в настройках).

Понимает: «через 10 минут…», «через полчаса…», «в 18:30…», «завтра в 9…»,
«поставь таймер на 5 минут».
"""
import datetime
import json
import os
import re
import threading
import time
import uuid

from core.notifier import notify
from nlu.numbers import ru_numbers_to_digits

REMINDERS_FILE = "config/reminders.json"
CHECK_EVERY_SEC = 1.0
TIMER_TASK = "Таймер"

_lock = threading.Lock()
_scheduler_started = False

_UNIT_SECONDS = (("час", 3600), ("мин", 60), ("сек", 1))
_HALF_HOUR_RE = re.compile(r"через\s+(?:пол\s*часа|полчаса)\s*(.*)")
_RELATIVE_RE = re.compile(
    r"через\s+(?:(\d+)\s*)?(час(?:а|ов)?|минут\w*|мин|секунд\w*|сек)\b\s*(.*)")
_ABSOLUTE_RE = re.compile(
    r"(?:(завтра|послезавтра)\s+)?в\s+(\d{1,2})(?:[:\s]+(\d{2}))?"
    r"\s*(утра|вечера|дня|ночи)?\s*(.*)")
_TIMER_RE = re.compile(r"таймер\s+(?:на\s+)?(.*)")
_LEADING = re.compile(r"^(?:мне\s+)?(?:напомни(?:ть)?|напоминание)\s*(?:мне\s*)?")


def _load() -> list[dict]:
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(items: list[dict]):
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _plural(n: int, one: str, few: str, many: str) -> str:
    if 11 <= n % 100 <= 14:
        return many
    return one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many


def _duration_text(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    parts = []
    if hours:
        parts.append(f"{hours} {_plural(hours, 'час', 'часа', 'часов')}")
    if minutes:
        parts.append(f"{minutes} {_plural(minutes, 'минуту', 'минуты', 'минут')}")
    if secs and not hours:
        parts.append(f"{secs} {_plural(secs, 'секунду', 'секунды', 'секунд')}")
    return " ".join(parts) or "0 секунд"


# ------------------------------------------------------------------ разбор

def parse_when(text: str, now: datetime.datetime | None = None):
    """Выделяет время из фразы. Возвращает (datetime, текст дела)
    или None, если времени в фразе нет."""
    now = now or datetime.datetime.now()
    text = ru_numbers_to_digits(text.lower().strip())
    text = _LEADING.sub("", text).strip()

    m = _HALF_HOUR_RE.search(text)
    if m:
        return now + datetime.timedelta(minutes=30), m.group(1).strip()

    m = _RELATIVE_RE.search(text)
    if m:
        amount = int(m.group(1)) if m.group(1) else 1
        unit = m.group(2)
        seconds = next(mult for prefix, mult in _UNIT_SECONDS if unit.startswith(prefix))
        return now + datetime.timedelta(seconds=amount * seconds), m.group(3).strip()

    m = _ABSOLUTE_RE.search(text)
    if m:
        day_word, hour, minute, period, task = m.groups()
        hour, minute = int(hour), int(minute or 0)
        if period in ("вечера", "дня") and hour < 12:
            hour += 12
        elif period == "ночи" and hour == 12:
            hour = 0
        if hour > 23 or minute > 59:
            return None
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if day_word == "завтра":
            due += datetime.timedelta(days=1)
        elif day_word == "послезавтра":
            due += datetime.timedelta(days=2)
        elif due <= now:
            due += datetime.timedelta(days=1)
        return due, task.strip()
    return None


# ---------------------------------------------------------------- хранилище

def add_reminder(task: str, due: datetime.datetime) -> dict:
    item = {"id": uuid.uuid4().hex[:8], "task": task, "due": due.isoformat(timespec="seconds")}
    with _lock:
        items = _load()
        items.append(item)
        _save(items)
    return item


def list_reminders() -> list[dict]:
    return sorted(_load(), key=lambda r: r["due"])


def cancel_all() -> int:
    with _lock:
        count = len(_load())
        _save([])
    return count


def set_reminder(text: str) -> str:
    """Ставит напоминание по фразе и возвращает ответ для озвучки."""
    timer = _TIMER_RE.search(ru_numbers_to_digits(text.lower()))
    if timer:
        parsed = parse_when("через " + timer.group(1))
        task = TIMER_TASK
    else:
        parsed = parse_when(text)
        task = ""

    if not parsed:
        return ("Не понял, когда напомнить. Скажите, например: "
                "напомни через десять минут позвонить маме")

    due, parsed_task = parsed
    task = task or parsed_task or "Напоминание"
    add_reminder(task, due)

    delta = round((due - datetime.datetime.now()).total_seconds())
    if delta < 3 * 3600 and due.date() == datetime.date.today():
        when = f"через {_duration_text(max(delta, 1))}"
    else:
        day = "завтра " if due.date() > datetime.date.today() else ""
        when = f"{day}в {due:%H:%M}"
    if task == TIMER_TASK:
        return f"Таймер поставлен {when}"
    return f"Хорошо, напомню {when}: {task}"


def describe_reminders() -> str:
    items = list_reminders()
    if not items:
        return "Активных напоминаний нет"
    lines = []
    for r in items[:5]:
        due = datetime.datetime.fromisoformat(r["due"])
        lines.append(f"в {due:%H:%M} — {r['task']}")
    return f"Напоминаний: {len(items)}. " + ". ".join(lines)


# ---------------------------------------------------------------- планировщик

def _fire(item: dict, speaker):
    task = item["task"]
    print(f"[REMINDER] {task}")
    is_timer = task == TIMER_TASK
    notify("Джарвис: таймер" if is_timer else "Джарвис: напоминание",
           "Время вышло" if is_timer else task)
    try:
        speaker.speak("Время таймера вышло" if is_timer else f"Напоминаю: {task}")
    except Exception as e:
        print(f"[REMINDER] Ошибка озвучки: {e}")


def _loop(speaker):
    while True:
        time.sleep(CHECK_EVERY_SEC)
        now = datetime.datetime.now().isoformat(timespec="seconds")
        with _lock:
            items = _load()
            due = [r for r in items if r["due"] <= now]
            if due:
                _save([r for r in items if r["due"] > now])
        for item in due:
            _fire(item, speaker)


def start_scheduler(speaker):
    """Запускает фоновую проверку напоминаний (один раз за сеанс)."""
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True
    threading.Thread(target=_loop, args=(speaker,), daemon=True).start()
