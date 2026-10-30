"""Реестр действий: метка намерения -> существующий обработчик.

Старые обработчики (commands/intents_*.py) достают аргументы из текста через
text.replace("найди", ""), поэтому мы не меняем их, а подаём каждому
каноническую фразу, которую он понимает: «открой стим», «найди на ютубе X».
Всё знание о ключевых словах живёт здесь, в одном месте.

Обработчики импортируются лениво, чтобы классификатор можно было загружать и
тестировать без Windows-зависимостей (pyautogui и т.п.).
"""
import importlib

# метка: (модуль, функция, каноническая фраза, вопрос если слот пустой)
ACTIONS = {
    # приложения, сайты, папки
    "open_app": ("commands.intents_apps", "handle_open", "открой {q}", "Что именно открыть?"),
    "close_app": ("commands.intents_apps", "handle_close", "закрой {q}", "Что именно закрыть?"),
    "open_website": ("commands.web.intents_web", "handle_web", "открой сайт {q}", "Какой сайт открыть?"),
    "open_folder": ("commands.intents_apps", "handle_folder", "открой папку {q}", "Какую папку открыть?"),
    "close_folder": ("commands.intents_apps", "handle_close_folder", "закрой папку {q}", "Какую папку закрыть?"),
    "folder:downloads": ("commands.system.intents_utils", "handle_downloads", "открой загрузки", None),
    "folder:documents": ("commands.system.intents_utils", "handle_documents", "открой документы", None),
    "folder:desktop": ("commands.system.intents_utils", "handle_desktop", "открой рабочий стол", None),
    "folder:disk_d": ("commands.system.intents_utils", "handle_disk_d", "открой диск d", None),
    "folder:disk_e": ("commands.system.intents_utils", "handle_disk_e", "открой диск e", None),

    # поиск и контент
    "web:currency": ("commands.web.intents_web", "handle_currency", "курс валют", None),
    "web:search": ("commands.web.intents_web", "handle_search", "найди {q}", "Что именно найти?"),
    "web:info": ("commands.web.intents_web", "handle_info_search", "найди информацию {q}", "Какую информацию искать?"),
    "web:video": ("commands.web.intents_web", "handle_video_search", "найди видео {q}", "Какое видео найти?"),
    "web:movie": ("commands.web.intents_web", "handle_movie_search", "хочу посмотреть {q}", "Какой фильм или сериал?"),
    "web:music": ("commands.web.intents_web", "handle_music", "включи музыку", None),
    "web:youtube_search": ("commands.web.intents_youtube", "handle_youtube_search", "найди на ютубе {q}", "Что искать на ютубе?"),
    "web:channel": ("commands.web.intents_youtube", "handle_open_channel", "открой канал {q}", "Какой канал открыть?"),
    "web:weather": ("commands.web.intents_web", "handle_weather", "какая погода {q}", None),

    # управление ютубом
    "youtube:fullscreen": ("commands.web.intents_youtube", "handle_youtube_fullscreen", "полный экран", None),
    "youtube:forward": ("commands.web.intents_youtube", "handle_youtube_forward", "перемотай вперёд", None),
    "youtube:backward": ("commands.web.intents_youtube", "handle_youtube_backward", "перемотай назад", None),

    # антивирус
    "scan:quick": ("commands.system.intents_scan", "handle_scan_quick", "быстрая проверка", None),
    "scan:full": ("commands.system.intents_scan", "handle_scan_full", "полная проверка", None),
    "scan:cancel": ("commands.system.intents_scan", "handle_scan_cancel", "останови сканирование", None),

    # утилиты
    "util:time": ("commands.system.intents_utils", "handle_time", "который час", None),
    "util:date": ("commands.system.intents_utils", "handle_date", "какая дата", None),

    # подключения (Bluetooth, WiFi)
    "system:bluetooth_on": ("commands.system.intents_connectivity", "handle_bluetooth_on", "включи блютуз", None),
    "system:bluetooth_off": ("commands.system.intents_connectivity", "handle_bluetooth_off", "выключи блютуз", None),
    "system:wifi_on": ("commands.system.intents_connectivity", "handle_wifi_on", "включи вай фай", None),
    "system:wifi_off": ("commands.system.intents_connectivity", "handle_wifi_off", "выключи вай фай", None),
    "system:hotspot": ("commands.system.intents_connectivity", "handle_hotspot_on", "включи точку доступа", None),
    "system:airplane": ("commands.system.intents_connectivity", "handle_airplane_on", "режим в самолёте", None),

    # To-Do список
    "todo:add": ("commands.todo_handler", "handle_todo_add", "добавь в список дел {q}", "Что добавить в список дел?"),
    "todo:list": ("commands.todo_handler", "handle_todo_list", "список дел", None),
    "todo:done": ("commands.todo_handler", "handle_todo_done", "выполнено {q}", "Какое дело выполнено?"),
    "todo:clear": ("commands.todo_handler", "handle_todo_clear", "очисти список дел", None),
    "todo:remind": ("commands.todo_handler", "handle_todo_remind", "напомни {q}", "О чём напомнить?"),
}

ACTION_LABELS = frozenset(ACTIONS)


def clarification(label: str, query: str):
    """Уточняющий вопрос, если действию нужен слот, а он пустой."""
    _, _, template, question = ACTIONS[label]
    if "{q}" in template and not query.strip():
        return question
    return None


def resolve(label: str, query: str):
    """Возвращает (функция-обработчик, каноническая фраза для неё)."""
    module, func, template, _ = ACTIONS[label]
    handler = getattr(importlib.import_module(module), func)
    return handler, template.format(q=query).strip()
