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
        print(f"Профиль загружен: {self._config.get('name', 'Денис')}")

    @property
    def current(self) -> dict:
        return self._config

    @property
    def honorific(self) -> str:
        return self._config.get("honorific", "сэр")

    @property
    def name(self) -> str:
        return self._config.get("name", "Денис")

    def reload(self):
        self._config = load_config()
