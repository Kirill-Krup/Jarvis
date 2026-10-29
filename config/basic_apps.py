"""Список базовых приложений для быстрого первого сканирования и сохранения путей в memory.json.

Содержит:
- id: уникальный идентификатор
- title: отображаемое название
- search_names: имена для поиска через FileSearch (ярлыки Start Menu, Desktop и т.д.)
- aliases: все варианты названия (русские, английские, сленговые, падежные),
           которые сохраняются в config/memory.json для мгновенного запуска (0 мс)
- fallback_paths: прямые пути на диске, если поиск по ярлыкам не нашел файл
- process_name: имя процесса для закрытия через taskkill
"""
import os
import getpass

_USERNAME = getpass.getuser()

BASIC_APPS = [
    {
        "id": "telegram",
        "title": "Telegram",
        "search_names": ["Telegram", "Telegram Desktop"],
        "aliases": ["telegram", "телеграм", "телега", "телегу", "тг", "тгшку"],
        "fallback_paths": [
            f"C:/Users/{_USERNAME}/AppData/Roaming/Telegram Desktop/Telegram.exe",
            f"C:/Users/{_USERNAME}/AppData/Local/Telegram Desktop/Telegram.exe",
            "C:/Program Files/Telegram Desktop/Telegram.exe",
        ],
        "process_name": "Telegram.exe",
    },
    {
        "id": "discord",
        "title": "Discord",
        "search_names": ["Discord"],
        "aliases": ["discord", "дискорд", "диску", "дискорда"],
        "fallback_paths": [
            f"C:/Users/{_USERNAME}/AppData/Local/Discord/Discord.exe",
            f"C:/Users/{_USERNAME}/AppData/Local/Discord/Update.exe",
            "C:/Program Files/Discord/Discord.exe",
        ],
        "process_name": "Discord.exe",
    },
    {
        "id": "steam",
        "title": "Steam",
        "search_names": ["Steam"],
        "aliases": ["steam", "стим", "стима", "стимик"],
        "fallback_paths": [
            "C:/Program Files (x86)/Steam/steam.exe",
            "D:/Steam/steam.exe",
            "E:/Steam/steam.exe",
            "C:/Steam/steam.exe",
        ],
        "process_name": "steam.exe",
    },
    {
        "id": "chrome",
        "title": "Google Chrome",
        "search_names": ["Google Chrome", "Chrome"],
        "aliases": ["chrome", "google chrome", "хром", "гугл хром", "браузер", "интернет"],
        "fallback_paths": [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            f"C:/Users/{_USERNAME}/AppData/Local/Google/Chrome/Application/chrome.exe",
        ],
        "process_name": "chrome.exe",
    },
    {
        "id": "yandex",
        "title": "Yandex Browser",
        "search_names": ["Yandex", "YandexBrowser", "Яндекс"],
        "aliases": ["yandex", "яндекс", "яндекс браузер"],
        "fallback_paths": [
            f"C:/Users/{_USERNAME}/AppData/Local/Yandex/YandexBrowser/Application/browser.exe",
        ],
        "process_name": "browser.exe",
    },
    {
        "id": "operagx",
        "title": "Opera GX",
        "search_names": ["Opera GX", "Opera"],
        "aliases": ["operagx", "opera", "опера", "опера гх", "опера gx"],
        "fallback_paths": [
            f"C:/Users/{_USERNAME}/AppData/Local/Programs/Opera GX/launcher.exe",
            f"C:/Users/{_USERNAME}/AppData/Local/Programs/Opera/launcher.exe",
            "C:/Program Files/Opera GX/launcher.exe",
        ],
        "process_name": "opera.exe",
    },
    {
        "id": "edge",
        "title": "Microsoft Edge",
        "search_names": ["Microsoft Edge", "Edge"],
        "aliases": ["edge", "эдж", "микрософт эдж"],
        "fallback_paths": [
            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        ],
        "process_name": "msedge.exe",
    },
    {
        "id": "vscode",
        "title": "Visual Studio Code",
        "search_names": ["Visual Studio Code", "Code"],
        "aliases": ["vscode", "code", "визуал студио", "вс код", "код", "visual studio code"],
        "fallback_paths": [
            f"C:/Users/{_USERNAME}/AppData/Local/Programs/Microsoft VS Code/Code.exe",
            "C:/Program Files/Microsoft VS Code/Code.exe",
        ],
        "process_name": "Code.exe",
    },
    {
        "id": "spotify",
        "title": "Spotify",
        "search_names": ["Spotify"],
        "aliases": ["spotify", "спотифай", "спотик"],
        "fallback_paths": [
            f"C:/Users/{_USERNAME}/AppData/Roaming/Spotify/Spotify.exe",
        ],
        "process_name": "Spotify.exe",
    },
    {
        "id": "obs",
        "title": "OBS Studio",
        "search_names": ["OBS Studio", "OBS"],
        "aliases": ["obs", "обс", "obs studio"],
        "fallback_paths": [
            "C:/Program Files/obs-studio/bin/64bit/obs64.exe",
            "C:/Program Files (x86)/obs-studio/bin/64bit/obs64.exe",
        ],
        "process_name": "obs64.exe",
    },
    {
        "id": "qbittorrent",
        "title": "qBittorrent",
        "search_names": ["qBittorrent", "uTorrent", "BitTorrent"],
        "aliases": ["qbittorrent", "торрент", "битторрент", "кьюбитторрент"],
        "fallback_paths": [
            "C:/Program Files/qBittorrent/qbittorrent.exe",
            f"C:/Users/{_USERNAME}/AppData/Roaming/uTorrent/uTorrent.exe",
        ],
        "process_name": "qbittorrent.exe",
    },
    {
        "id": "notepad",
        "title": "Блокнот",
        "search_names": ["Notepad", "Блокнот"],
        "aliases": ["notepad", "блокнот"],
        "fallback_paths": [
            "C:/Windows/notepad.exe",
            "C:/Windows/System32/notepad.exe",
        ],
        "process_name": "notepad.exe",
    },
    {
        "id": "calc",
        "title": "Калькулятор",
        "search_names": ["Calculator", "Калькулятор"],
        "aliases": ["calc", "калькулятор"],
        "fallback_paths": [
            "C:/Windows/System32/calc.exe",
        ],
        "process_name": "CalculatorApp.exe",
    },
    {
        "id": "explorer",
        "title": "Проводник",
        "search_names": ["Explorer", "Проводник"],
        "aliases": ["explorer", "проводник"],
        "fallback_paths": [
            "C:/Windows/explorer.exe",
        ],
        "process_name": "explorer.exe",
    },
    {
        "id": "taskmgr",
        "title": "Диспетчер задач",
        "search_names": ["Task Manager", "Диспетчер задач"],
        "aliases": ["диспетчер задач", "диспетчер", "taskmgr"],
        "fallback_paths": [
            "C:/Windows/System32/taskmgr.exe",
        ],
        "process_name": "Taskmgr.exe",
    },
    {
        "id": "cmd",
        "title": "Командная строка",
        "search_names": ["Command Prompt", "Командная строка"],
        "aliases": ["терминал", "консоль", "командная строка", "cmd"],
        "fallback_paths": [
            "C:/Windows/System32/cmd.exe",
        ],
        "process_name": "cmd.exe",
    },
    {
        "id": "dota",
        "title": "Dota 2",
        "search_names": ["Dota 2", "Dota"],
        "aliases": ["дота", "доту", "дота 2", "доту 2", "dota", "dota 2"],
        "fallback_paths": [
            "E:/Games/Dota 2.url",
            "D:/Steam/steamapps/common/dota 2 beta/game/bin/win64/dota2.exe",
            "C:/Program Files (x86)/Steam/steamapps/common/dota 2 beta/game/bin/win64/dota2.exe",
        ],
        "process_name": "dota2.exe",
    },
    {
        "id": "cs2",
        "title": "Counter-Strike 2",
        "search_names": ["Counter-Strike 2", "CS2", "Counter-Strike"],
        "aliases": ["кс", "кску", "кс 2", "ксго", "ксочку", "cs", "cs2", "csgo"],
        "fallback_paths": [
            "D:/Steam/steamapps/common/Counter-Strike Global Offensive/game/bin/win64/cs2.exe",
            "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/bin/win64/cs2.exe",
        ],
        "process_name": "cs2.exe",
    },
]
