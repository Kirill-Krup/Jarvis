"""To-Do List и напоминания для Джарвиса.

Хранит список дел в JSON-файле. Поддерживает:
  - Добавление дел
  - Озвучку списка
  - Удаление дел
(напоминания по времени: commands/reminders.py)
"""
import json
import os
import re
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
    """Обработчик интента todo:remind (время разбирает commands.reminders)."""
    from commands import reminders
    text = cmd.text_lower
    if reminders.parse_when(text) is None:
        task = text
        for prefix in ("напомни мне", "напомни"):
            if task.startswith(prefix):
                task = task[len(prefix):].strip()
                break
        return ctx.reply(add_todo(task) if task else "Не понял, о чём и когда напомнить")
    return ctx.reply(reminders.set_reminder(text))
