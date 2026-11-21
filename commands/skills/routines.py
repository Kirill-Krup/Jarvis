"""Умные сценарии дня: Доброе утро, Рабочий режим, Ночной режим."""
import datetime
import json
import os
import psutil
import pyautogui

from commands.skills.registry import skill

pyautogui.FAILSAFE = False

CATEGORY = "🚀 Сценарии и режимы"


def _get_todos_summary() -> str:
    todo_file = "config/reminders.json"
    if os.path.exists(todo_file):
        try:
            with open(todo_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                todos = data.get("todos", [])
                if todos:
                    active = [t.get("text", t) if isinstance(t, dict) else str(t) for t in todos[:3]]
                    return f"В вашем списке дел на сегодня: {', '.join(active)}."
        except Exception:
            pass
    return "Список запланированных дел пуст."


@skill(CATEGORY, "Утренний отчёт и брифинг",
       ["доброе утро", "утренний отчет", "утренняя сводка", "начни день", "проснись и пой"],
       [r"^(?:доброе\s+утро|утренн\w+\s+(?:сводк\w*|отчет\w*|брифинг)|начни\s+день)\b"],
       exclusive=True)
def handle_morning(cmd, ctx):
    now = datetime.datetime.now()
    name = ctx.profile.name
    honorific = ctx.profile.honorific

    lines = [f"Доброе утро, {name}. Сейчас {now.strftime('%H:%M')}."]

    # 1. Задачи
    lines.append(_get_todos_summary())

    # 2. Статус батареи (если ноутбук)
    battery = psutil.sensors_battery()
    if battery:
        state = "подключен к сети" if battery.power_plugged else "работает от аккумулятора"
        lines.append(f"Заряд батареи {round(battery.percent)} процентов, {state}.")

    lines.append(f"Все системы готовы к работе. Чем займёмся, {honorific}?")
    return " ".join(lines)


@skill(CATEGORY, "Сценарий: Рабочий режим / Режим кодинга",
       ["рабочий режим", "режим работы", "режим кодинга", "время работать", "пора за работу"],
       [r"^(?:рабочий\s+режим|режим\s+(?:работы|кодинга|разработки)|время\s+работать|пора\s+за\s+работу)\b"],
       exclusive=True)
def handle_work(cmd, ctx):
    # 1. Запуск IDE
    ide = ctx.profile.default_ide or "idea"
    ctx.app_launcher.launch(ide, "")

    # 2. Запуск мессенджера
    ctx.app_launcher.launch("телеграм", "")

    # 3. Установка рабочей громкости
    ctx.volume_control.set_volume(30)

    # 4. Включение рабочей музыки
    from commands.skills.music import play_query
    play_query("lofi hip hop radio study focus beats", ctx.profile)

    return ctx.reply("Рабочий режим активирован: запустил среду разработки, мессенджер и включил музыку для концентрации")


@skill(CATEGORY, "Сценарий: Ночной режим / Отбой",
       ["спокойной ночи", "я спать", "ночной режим", "режим ночи", "пора спать"],
       [r"^(?:спокойной\s+ночи|я\s+спать|ночной\s+режим|режим\s+ночи|пора\s+спать)\b"],
       exclusive=True)
def handle_sleep(cmd, ctx):
    # 1. Приглушение звука
    ctx.volume_control.set_volume(10)

    # 2. Остановка медиа
    try:
        pyautogui.press("playpause")
    except Exception:
        pass

    # 3. Сворачивание окон
    try:
        pyautogui.hotkey("win", "d")
    except Exception:
        pass

    return ctx.reply("Системы переведены в ночной режим, громкость снижена. Спокойной ночи")
