import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from config.profile_manager import ProfileManager
from core.speakers.utrobin_speaker import UtrobinSpeaker
from core.jarvice_voice_player import JarvisVoicePlayer


class Speaker:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.profile = ProfileManager()
        self.engine_name = getattr(self.profile, "tts_engine", None) or "utrobin"
        self.engine = UtrobinSpeaker()
        self.voice_player = JarvisVoicePlayer()
        self.engine_name = "utrobin"
        self._initialized = True

        print(f"Speaker готов [OK] backend={self.engine_name}")

    def speak(self, text: str):
        if not text or not str(text).strip():
            return
        self.engine.speak(text)

    def speak_greeting(self):
        if not self.voice_player.play_greeting():
            self.speak(f"Все системы в норме. Добро пожаловать, {self.profile.name}. Чем могу помочь, {self.profile.honorific}?")

    def speak_affirmation(self):
        if not self.voice_player.play_affirmation():
            self.speak(f"Слушаю, {self.profile.honorific}")

    def speak_loading(self):
        if not self.voice_player.play_loading():
            self.speak(f"Загружаю, {self.profile.honorific}")

    def speak_diagnostics(self):
        if not self.voice_player.play_diagnostics():
            self.speak("Начинаю диагностику системы")

    def speak_reboot(self):
        if not self.voice_player.play_reboot():
            self.speak(f"Снова в строю, {self.profile.honorific}")

    def speak_shutdown(self):
        if not self.voice_player.play_shutdown():
            self.speak(f"Отключаю питание. До встречи, {self.profile.honorific}")

    def speak_second_display_active(self):
        if not self.voice_player.play_second_display_active():
            self.speak("Первый экран деактивирован")

    def speak_first_display_active(self):
        if not self.voice_player.play_first_display_active():
            self.speak("Второй экран деактивирован")

    def speak_duplicate_display(self):
        if not self.voice_player.play_duplicate_display():
            self.speak("Дублирование экранов активировано")

    def speak_extend_display(self):
        if not self.voice_player.play_extend_display():
            self.speak("Экраны расширены")

    def speak_import(self):
        if not self.voice_player.play_layout_scan_complete():
            self.speak("Импортирую настройки, системы в норме")
