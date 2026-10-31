"""To-Do List и напоминания для Джарвиса.

Хранит список дел в JSON-файле. Поддерживает:
  - Добавление дел
  - Озвучку списка
  - Удаление дел
  - Напоминания по таймеру (через N минут)
"""
import json
import os
import re
import threading
import datetime


TODO_FILE = "config/todo_list.json"


def _load_todos() -> list[dict]:
    if os.path.exists(TODO_FILE):
        try:
            with open(TODO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_todos(todos: list[dict]):
    os.makedirs(os.path.dirname(TODO_FILE), exist_ok=True)
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def add_todo(task: str) -> str:
    """Добавляет задачу в список."""
    if not task.strip():
        return "Не понял, что добавить в список дел"

    todos = _load_todos()
    todo_item = {
        "task": task.strip(),
        "created": datetime.datetime.now().isoformat(),
        "done": False,
    }
    todos.append(todo_item)
    _save_todos(todos)
    return f"Добавил в список дел: {task.strip()}"


def list_todos() -> str:
    """Озвучивает текущий список дел."""
    todos = _load_todos()
    active = [t for t in todos if not t.get("done")]

    if not active:
        return "Список дел пуст. Можно отдыхать!"

    if len(active) == 1:
        return f"В списке одно дело: {active[0]['task']}"

    items = []
    for i, t in enumerate(active, 1):
        items.append(f"{i}. {t['task']}")

    result = f"В списке {len(active)} дел. "
    result += ". ".join(items)
    return result


def complete_todo(query: str) -> str:
    """Отмечает задачу как выполненную."""
    todos = _load_todos()
    active = [t for t in todos if not t.get("done")]

    if not active:
        return "Список дел пуст"

    # Попробуем по номеру
    num_match = re.search(r"\d+", query)
    if num_match:
        idx = int(num_match.group()) - 1
        if 0 <= idx < len(active):
            active[idx]["done"] = True
            task_name = active[idx]["task"]
            _save_todos(todos)
            return f"Отмечено как выполненное: {task_name}"

    # Попробуем по тексту
    query_lower = query.lower().strip()
    for t in active:
        if query_lower in t["task"].lower():
            t["done"] = True
            _save_todos(todos)
            return f"Отмечено как выполненное: {t['task']}"

    return "Не нашёл такую задачу в списке"


def clear_done() -> str:
    """Удаляет выполненные задачи."""
    todos = _load_todos()
    active = [t for t in todos if not t.get("done")]
    _save_todos(active)
    return "Выполненные задачи очищены"


def clear_all() -> str:
    """Очищает весь список."""
    _save_todos([])
    return "Список дел полностью очищен"


def get_all_todos() -> list[dict]:
    """Возвращает сырой список всех задач."""
    return _load_todos()


def delete_todo_by_index(idx: int) -> bool:
    """Удаляет задачу по её индексу в списке."""
    todos = _load_todos()
    if 0 <= idx < len(todos):
        todos.pop(idx)
        _save_todos(todos)
        return True
    return False


def toggle_todo_by_index(idx: int) -> bool:
    """Переключает статус выполнения задачи."""
    todos = _load_todos()
    if 0 <= idx < len(todos):
        todos[idx]["done"] = not todos[idx].get("done", False)
        _save_todos(todos)
        return True
    return False


# ─── Напоминания ───

_active_reminders: list[threading.Timer] = []


_WORD_NUMBERS = {
    "один": 1, "одну": 1, "одна": 1,
    "два": 2, "две": 2, "пару": 2, "парочку": 2,
    "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,
    "десять": 10, "одиннадцать": 11, "двенадцать": 12, "пятнадцать": 15,
    "двадцать": 20, "тридцать": 30, "сорок": 40, "сорок пять": 45, "пятьдесят": 50,
}


def set_reminder(text: str, speaker=None) -> str:
    """Парсит 'напомни через N минут/часов ...' и ставит таймер.

    Поддерживаемые форматы:
      - напомни через минуту выпить таблетку
      - напомни через пару минут проверить суп
      - напомни через полчаса выключить духовку
      - напомни через 30 минут выпить таблетку
      - напомни через 1 час позвонить маме
    """
    clean_text = text.lower().strip()

    # Особый случай: «полчаса»
    if "полчаса" in clean_text or "пол часа" in clean_text:
        amount = 30
        unit = "мин"
        task = re.sub(r".*?(?:полчаса|пол\s+часа)\s*", "", clean_text, count=1).strip()
    else:
        # Проверяем «через (число или слово) (минут/часов/секунд) (дело)»
        # Либо «через минуту/часик (дело)» без указания числа
        pattern = re.compile(
            r"через\s+(?:(\d+|[а-яё]+)\s+)?(минут[аыу]?|минутку|мин|час(?:а|ов|ик)?|секунд[аыу]?|секундочку|сек)\s*(.*)",
            re.IGNORECASE,
        )
        match = pattern.search(clean_text)

        if not match:
            # Если нет слова «через», но есть «напомни ...» без времени — сохраняем в To-Do
            task = clean_text
            for prefix in ("напомни мне", "напомни", "напоминание"):
                if task.startswith(prefix):
                    task = task[len(prefix):].strip()
                    break
            if task:
                return add_todo(task)
            return "Не понял, о чём и когда напомнить"

        raw_num = match.group(1)
        unit = match.group(2).lower()
        task = match.group(3).strip()

        if raw_num:
            if raw_num.isdigit():
                amount = int(raw_num)
            else:
                amount = _WORD_NUMBERS.get(raw_num.lower(), 1)
        else:
            # «через минуту», «через час», «через секунду» -> 1
            amount = 1

    if not task:
        task = "Напоминание"

    # Переводим в секунды
    if unit.startswith("час"):
        seconds = amount * 3600
        unit_text = _pluralize_time(amount, "час", "часа", "часов")
    elif unit.startswith("мин"):
        seconds = amount * 60
        unit_text = _pluralize_time(amount, "минуту", "минуты", "минут")
    else:
        seconds = amount
        unit_text = _pluralize_time(amount, "секунду", "секунды", "секунд")

    def _fire_reminder():
        reminder_text = f"Напоминаю: {task}"
        print(f"[REMINDER] {reminder_text}")
        try:
            from core.logging_utils import log_action
            log_action(f"Сработало напоминание: {task}")
        except Exception:
            pass

        # Голосовое воспроизведение
        spk = speaker
        if not spk:
            try:
                from core.speakers.speaker import Speaker
                spk = Speaker()
            except Exception:
                pass

        if spk:
            try:
                spk.speak(reminder_text)
            except Exception as e:
                print(f"[REMINDER] Ошибка озвучки: {e}")

    timer = threading.Timer(seconds, _fire_reminder)
    timer.daemon = True
    timer.start()
    _active_reminders.append(timer)

    return f"Хорошо, напомню через {amount} {unit_text}: {task}"


def _pluralize_time(n: int, one: str, few: str, many: str) -> str:
    if 11 <= n % 100 <= 14:
        return many
    mod10 = n % 10
    if mod10 == 1:
        return one
    if 2 <= mod10 <= 4:
        return few
    return many


# ─── Обработчики для NLU actions ───

def handle_todo_add(cmd, ctx):
    """Обработчик интента todo:add."""
    text = cmd.text_lower
    for prefix in (
        "добавь в список дел",
        "добавь в туду",
        "добавь задачу",
        "добавь в список",
        "запиши в дела",
        "запиши дело",
        "добавь дело",
        "новая задача",
    ):
        if prefix in text:
            task = text.split(prefix, 1)[1].strip()
            return ctx.reply(add_todo(task))

    # Если не нашли префикс — берём всё после "добавь"
    task = text
    for w in ("добавь", "запиши", "внеси"):
        if w in task:
            task = task.split(w, 1)[1].strip()
            break
    return ctx.reply(add_todo(task))


def handle_todo_list(cmd, ctx):
    """Обработчик интента todo:list."""
    return ctx.reply(list_todos())


def handle_todo_done(cmd, ctx):
    """Обработчик интента todo:done."""
    text = cmd.text_lower
    for prefix in (
        "выполнено", "выполнил", "сделано", "сделал",
        "отметь", "зачеркни", "убери из списка",
    ):
        if prefix in text:
            query = text.split(prefix, 1)[1].strip()
            return ctx.reply(complete_todo(query))
    return ctx.reply(complete_todo(text))


def handle_todo_clear(cmd, ctx):
    """Обработчик интента todo:clear."""
    text = cmd.text_lower
    if "все" in text or "весь" in text or "полностью" in text:
        return ctx.reply(clear_all())
    return ctx.reply(clear_done())


def handle_todo_remind(cmd, ctx):
    """Обработчик интента todo:remind."""
    text = cmd.text_lower
    return ctx.reply(set_reminder(text, ctx.speaker))
