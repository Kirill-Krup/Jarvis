"""Единая точка озвучки: TTS + заранее записанные фразы (если есть файлы)."""
from config.profile_manager import ProfileManager
from core.honorific import soften
from core.jarvice_voice_player import JarvisVoicePlayer
from core.speakers.number_verbalizer import verbalize_numbers
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
        self._vc = None
        voice = getattr(self.profile, "voice", "en-US-BrianMultilingualNeural")
        if voice == "utrobin":
            self.engine = UtrobinSpeaker()
        else:
            try:
                from core.speakers.edge_speaker import EdgeSpeaker
                # Если в конфиге стоял английский en-GB-RyanNeural или пусто, используем лучший голос Brian
                chosen_voice = "en-US-BrianMultilingualNeural" if ("Ryan" in str(voice) or not voice) else str(voice)
                self.engine = EdgeSpeaker(voice=chosen_voice)
            except Exception as e:
                print(f"[SPEAKER] Ошибка EdgeSpeaker ({e}), переключаюсь на Utrobin")
                self.engine = UtrobinSpeaker()

        self.voice_player = JarvisVoicePlayer()
        self._initialized = True
        print("Speaker готов [OK]")

    def _get_vc(self):
        if self._vc is None:
            try:
                from commands.system.volume_control import VolumeControl
                self._vc = VolumeControl()
            except Exception:
                self._vc = False
        return self._vc if self._vc else None

    def speak(self, text: str, soften_honorific: bool = True):
        """Озвучивает текст. Обращение («сэр») оставляется лишь иногда;
        для уже обработанных ответов передавайте soften_honorific=False."""
        if not text or not str(text).strip():
            return
        text = str(text)
        if soften_honorific:
            text = soften(text)
        text = verbalize_numbers(text)

        # Автоприглушение фонового звука (Audio Ducking)
        prev_vol = None
        vc = self._get_vc()
        if vc:
            try:
                current_vol = vc.get_volume()
                if current_vol > 20:
                    prev_vol = current_vol
                    vc.set_volume(max(10, int(current_vol * 0.35)))
            except Exception:
                prev_vol = None

        try:
            self.engine.speak(text)
        finally:
            if prev_vol is not None and vc:
                try:
                    vc.set_volume(prev_vol)
                except Exception:
                    pass

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
                          "Все дисплеи активированы")
