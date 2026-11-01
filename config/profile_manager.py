from config.store import load_config


class ProfileManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._config = load_config()
        self._initialized = True
        print(f"Профиль загружен: {self.name} (город: {self.city})")

    @property
    def current(self) -> dict:
        return self._config

    @property
    def honorific(self) -> str:
        return self._config.get("honorific", "сэр")

    @property
    def name(self) -> str:
        return self._config.get("name", "Денис")

    @property
    def city(self) -> str:
        return self._config.get("city", "Москва")

    @property
    def movie_source(self) -> str:
        return self._config.get("movie_source", "KinoGo")

    @property
    def anime_source(self) -> str:
        return self._config.get("anime_source", "AnimeGO")

    @property
    def music_player(self) -> str:
        return self._config.get("music_player", "YouTube Music")

    @property
    def context_timeout(self) -> float:
        return float(self._config.get("context_timeout", 5.0))

    @property
    def vad_threshold(self) -> float:
        return float(self._config.get("vad_threshold", 0.5))

    @property
    def silence_ms(self) -> int:
        return int(self._config.get("silence_ms", 400))

    @property
    def mic_gain(self) -> float:
        return float(self._config.get("mic_gain", 1.0))

    @property
    def vosk_model(self) -> str:
        return str(self._config.get("vosk_model", "model_small"))

    @property
    def honorific_chance(self) -> float:
        return max(0.0, min(1.0, float(self._config.get("honorific_chance", 0.25))))

    @property
    def voice_volume(self) -> int:
        return int(self._config.get("voice_volume", 100))

    @property
    def notify_channel(self) -> str:
        return str(self._config.get("notify_channel", "pc"))

    @property
    def telegram_token(self) -> str:
        return str(self._config.get("telegram_token", "")).strip()

    @property
    def telegram_chat_id(self) -> str:
        return str(self._config.get("telegram_chat_id", "")).strip()

    @property
    def projects_root(self) -> str:
        return str(self._config.get("projects_root", "")).strip()

    @property
    def default_ide(self) -> str:
        return str(self._config.get("default_ide", "idea"))

    def reload(self):
        self._config = load_config()
