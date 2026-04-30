import json
import os


USER_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "user_config.json"
)

DEFAULT_CONFIG = {
    "name": "Кирилл",
    "honorific": "сэр",
    "voice": "en-GB-RyanNeural",
    "speed": "-5%",
    "pitch": "-10Hz",
    "extra_drives": [
        "D:/",
        "E:/"
    ],
    "autostart": False
}


def _normalize_config(data: dict) -> dict:
    config = DEFAULT_CONFIG.copy()
    config.update(data or {})

    autostart = config.get("autostart", False)
    if isinstance(autostart, str):
        config["autostart"] = autostart.strip().lower() == "true"
    else:
        config["autostart"] = bool(autostart)

    if not isinstance(config.get("extra_drives"), list):
        config["extra_drives"] = DEFAULT_CONFIG["extra_drives"][:]

    return config


def load_config() -> dict:
    if not os.path.exists(USER_CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    return _normalize_config(data)


def save_config(config: dict):
    normalized = _normalize_config(config)

    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)