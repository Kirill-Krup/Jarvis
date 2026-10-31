from config.setup_wizard import load_config


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
        print(f"Профиль загружен: {self._config.get('name', 'Денис')} (город: {self.city})")

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

    def reload(self):
        self._config = load_config()
