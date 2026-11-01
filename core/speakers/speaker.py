"""Единая точка озвучки: TTS + заранее записанные фразы (если есть файлы)."""
from config.profile_manager import ProfileManager
from core.honorific import soften
from core.jarvice_voice_player import JarvisVoicePlayer
from core.speakers.utrobin_speaker import UtrobinSpeaker


class Speaker:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.profile = ProfileManager()
        self.engine = UtrobinSpeaker()
        self.voice_player = JarvisVoicePlayer()
        self._initialized = True
        print("Speaker готов [OK]")

    def speak(self, text: str, soften_honorific: bool = True):
        """Озвучивает текст. Обращение («сэр») оставляется лишь иногда;
        для уже обработанных ответов передавайте soften_honorific=False."""
        if not text or not str(text).strip():
            return
        text = str(text)
        if soften_honorific:
            text = soften(text)
        self.engine.speak(text)

    def _play_or_say(self, played: bool, fallback: str):
        if not played:
            self.speak(fallback)

    def speak_greeting(self):
        p = self.profile
        self._play_or_say(
            self.voice_player.play_greeting(),
            f"Все системы в норме. Добро пожаловать, {p.name}. Чем могу помочь?")

    def speak_affirmation(self):
        self._play_or_say(self.voice_player.play_affirmation(), "Слушаю вас")

    def speak_loading(self):
        self._play_or_say(self.voice_player.play_loading(), "Загружаю")

    def speak_reboot(self):
        self._play_or_say(self.voice_player.play_reboot(), "Снова в строю")

    def speak_shutdown(self):
        self._play_or_say(self.voice_player.play_shutdown(),
                          f"Отключаю питание. До встречи, {self.profile.honorific}")

    def speak_second_display_active(self):
        self._play_or_say(self.voice_player.play_second_display_active(),
                          "Первый экран деактивирован")

    def speak_first_display_active(self):
        self._play_or_say(self.voice_player.play_first_display_active(),
                          "Второй экран деактивирован")

    def speak_duplicate_display(self):
        self._play_or_say(self.voice_player.play_duplicate_display(),
                          "Дублирование экранов активировано")

    def speak_extend_display(self):
        self._play_or_say(self.voice_player.play_extend_display(), "Экраны расширены")

    def speak_import(self):
        self._play_or_say(self.voice_player.play_layout_scan_complete(),
                          "Импортирую настройки, системы в норме")
