"""Хранилище пользовательских настроек (config/user_config.json)."""
import json
import os

CONFIG_PATH = "config/user_config.json"


def get_default_config() -> dict:
    return {
        "name": "Денис",
        "honorific": "сэр",
        "honorific_chance": 0.25,       # как часто добавлять «сэр» в конце фразы
        "city": "Москва",
        "extra_drives": ["E:/"],
        "music_player": "YouTube Music",
        "movie_source": "KinoGo",
        "anime_source": "AnimeGO",
        "map_provider": "google",       # google | yandex
        "context_timeout": 5.0,
        "microphone_index": None,
        "vad_threshold": 0.5,
        "silence_ms": 400,
        "mic_gain": 1.0,
        "vosk_model": "model_small",
        "autostart": False,
        # громкость голоса Джарвиса (0..100), системная громкость не затрагивается
        "voice_volume": 100,
        # куда присылать напоминания: pc | telegram | both
        "notify_channel": "pc",
        "telegram_token": "",
        "telegram_chat_id": "",
        # разработка: папка с проектами и IDE по умолчанию
        "projects_root": "",
        "default_ide": "idea",
    }


def is_first_run() -> bool:
    return not os.path.exists(CONFIG_PATH)


def load_config() -> dict:
    defaults = get_default_config()
    if not os.path.exists(CONFIG_PATH):
        return defaults
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return defaults
    for key, value in defaults.items():
        cfg.setdefault(key, value)
    return cfg


def save_config(config: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    # профиль кэширует настройки: обновляем, чтобы они вступили в силу сразу
    try:
        from config.profile_manager import ProfileManager
        ProfileManager().reload()
    except Exception:
        pass
