"""Состояние компьютера, управление окнами, сценарии и утренняя сводка."""
import datetime
import json
import os
import shutil

import psutil

from commands.skills.registry import skill

CATEGORY_INFO = "📊 Состояние компьютера"
CATEGORY_WINDOWS = "🪟 Окна"
CATEGORY_MODES = "🚀 Сценарии и сводка"
MODES_FILE = "config/modes.json"

DEFAULT_MODES = {
    "работа": {"ide": True, "apps": ["телеграм"], "music": "включи музыку для работы"},
    "игра": {"apps": ["стим", "дискорд"]},
    "отдых": {"music": "включи музыку для отдыха"},
}

WEEKDAYS = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"]


def _plural(n: int, one: str, few: str, many: str) -> str:
    if 11 <= n % 100 <= 14:
        return many
    return one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many


# --------------------------------------------------------- состояние ПК

@skill(CATEGORY_INFO, "Заряд батареи ноутбука",
       ["сколько заряда", "какой заряд батареи"],
       [r"(?:сколько|какой|каков\w*|проверь)\W+(?:\w+\W+)?(?:заряд|батаре)", r"^заряд\w*\s+батаре"])
def battery(cmd, ctx):
    info = psutil.sensors_battery()
    if info is None:
        return ctx.reply("Батареи не вижу, похоже, это стационарный компьютер")
    percent = round(info.percent)
    state = "заряжается" if info.power_plugged else "работает от батареи"
    left = ""
    if not info.power_plugged and info.secsleft and info.secsleft > 0:
        hours, minutes = divmod(info.secsleft // 60, 60)
        left = f", хватит примерно на {hours} ч {minutes} мин" if hours else f", хватит на {minutes} мин"
    return ctx.reply(f"Заряд {percent} {_plural(percent, 'процент', 'процента', 'процентов')}, {state}{left}")


@skill(CATEGORY_INFO, "Загрузка процессора и оперативной памяти",
       ["как загружен процессор", "сколько занято памяти", "загрузка системы"],
       [r"загрузк\w+\s+(?:процессор|системы|компьютер|памяти|цп)", r"(?:сколько|как)\W+.*(?:занято|загружен\w*)\W+.*(?:памят|процессор|озу)",
        r"состояние (?:системы|компьютера)"])
def load(cmd, ctx):
    cpu = round(psutil.cpu_percent(interval=0.5))
    mem = psutil.virtual_memory()
    return ctx.reply(
        f"Процессор загружен на {cpu} процентов. Оперативная память занята на "
        f"{round(mem.percent)} процентов, свободно {mem.available / 2**30:.1f} гигабайта")


@skill(CATEGORY_INFO, "Свободное место на дисках",
       ["сколько свободного места на диске", "сколько места осталось"],
       [r"свободн\w+\s+мест\w+", r"сколько\W+(?:места|памяти)\W+(?:осталось|на диске)"])
def disk_space(cmd, ctx):
    parts = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or not part.fstype:
            continue
        try:
            usage = shutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        letter = part.mountpoint[0]
        parts.append(f"на диске {letter} свободно {usage.free / 2**30:.0f} гигабайт")
    return ctx.reply(". ".join(parts) if parts else "Не удалось получить данные о дисках")


# ------------------------------------------------------------------- окна

def _hotkey(*keys):
    import pyautogui
    pyautogui.hotkey(*keys)


@skill(CATEGORY_WINDOWS, "Свернуть все окна и показать рабочий стол",
       ["сверни все окна", "покажи рабочий стол"],
       [r"сверни\w*\s+все\s+окна", r"покажи\w*\s+рабочий стол"])
def minimize_all(cmd, ctx):
    _hotkey("win", "d")
    return ctx.reply("Свернул все окна")


@skill(CATEGORY_WINDOWS, "Свернуть или развернуть текущее окно",
       ["сверни окно", "разверни окно на весь экран"],
       [r"^сверни\w*\s+(?:это\s+)?окно", r"^разверни\w*\s+(?:это\s+)?окно"])
def window_state(cmd, ctx):
    if cmd.text_lower.startswith("сверни"):
        _hotkey("win", "down")
        return ctx.reply("Окно свёрнуто")
    _hotkey("win", "up")
    return ctx.reply("Окно развёрнуто")


@skill(CATEGORY_WINDOWS, "Переключиться на другое окно",
       ["переключи окно", "следующее окно"],
       [r"переключ\w+\s+(?:на\s+другое\s+)?окно", r"следующее окно"])
def switch_window(cmd, ctx):
    _hotkey("alt", "tab")
    return ctx.reply("Переключил")


# ------------------------------------------------------ сценарии и сводка

def load_modes() -> dict:
    if not os.path.exists(MODES_FILE):
        os.makedirs(os.path.dirname(MODES_FILE), exist_ok=True)
        with open(MODES_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_MODES, f, ensure_ascii=False, indent=2)
        return dict(DEFAULT_MODES)
    try:
        with open(MODES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(DEFAULT_MODES)


@skill(CATEGORY_MODES,
       "Запустить сценарий: набор программ и музыки одной командой (настраивается в config/modes.json)",
       ["режим работы", "включи режим игры", "режим отдыха"],
       [r"режим\s+(\w+)"])
def run_mode(cmd, ctx):
    import re
    from commands.skills import dev, registry
    name = re.search(r"режим\s+(?:в\s+)?(\w+)", cmd.text_lower).group(1)
    modes = load_modes()
    mode = next((m for key, m in modes.items() if name.startswith(key[:3])), None)
    if mode is None:
        if name in ("сна", "самолёте", "самолете"):
            return None  # это другие команды
        return ctx.reply("Такого режима нет. Доступны: " + ", ".join(modes))

    done = []
    if mode.get("ide"):
        ide_id = ctx.profile.default_ide
        if dev.find_ide(ide_id):
            dev._launch_ide(dev.find_ide(ide_id))
            done.append(dev.IDES[ide_id]["title"])
    for app in mode.get("apps", []):
        result = ctx.app_launcher.launch(app, "")
        if "не удалось" not in result.lower():
            done.append(app)
    if mode.get("music"):
        skill_obj = registry.find_skill(mode["music"])
        if skill_obj:
            from commands.command_handler import Command
            skill_obj.handler(Command(mode["music"]), ctx)
            done.append("музыку")
    if not done:
        return ctx.reply(f"Режим {name} запущен, но ничего открыть не удалось")
    return ctx.reply(f"Режим {name}: запускаю " + ", ".join(done))


@skill(CATEGORY_MODES, "Сводка дня: дата, погода, дела и напоминания",
       ["доброе утро джарвис", "что у меня на сегодня", "сводка дня"],
       [r"^доброе утро", r"что у меня (?:на сегодня|сегодня)", r"сводка(?: дня)?", r"какие планы на (?:сегодня|день)"])
def briefing(cmd, ctx):
    from commands import reminders, todo_handler
    from commands.web import intents_web
    now = datetime.datetime.now()
    hour = now.hour
    greeting = ("Доброе утро" if 5 <= hour < 12 else "Добрый день" if hour < 18
                else "Добрый вечер" if hour < 23 else "Доброй ночи")
    parts = [f"{greeting}, {ctx.profile.name}. Сегодня {WEEKDAYS[now.weekday()]}, {now:%d.%m}, на часах {now:%H:%M}"]

    try:
        from commands.command_handler import Command
        weather = intents_web.handle_weather(Command("какая погода"), ctx)
        parts.append(weather.rsplit(", ", 1)[0] if weather.endswith(ctx.profile.honorific) else weather)
    except Exception:
        pass

    todos = [t for t in todo_handler.get_all_todos() if not t.get("done")]
    if todos:
        parts.append(f"В списке дел: {len(todos)}. Первое: {todos[0]['task']}")
    upcoming = reminders.list_reminders()
    if upcoming:
        due = datetime.datetime.fromisoformat(upcoming[0]["due"])
        parts.append(f"Ближайшее напоминание в {due:%H:%M}: {upcoming[0]['task']}")
    if len(parts) == 1:
        parts.append("Свободный день, дел нет")
    return ". ".join(parts)
