from config.profile_manager import ProfileManager
from core.speakers.utrobin_speaker import UtrobinSpeaker
from core.jarvice_voice_player import JarvisVoicePlayer


class Speaker:
    def __init__(self):
        self.profile = ProfileManager()
        self.engine_name = getattr(self.profile, "tts_engine", None) or "utrobin"
        self.engine = UtrobinSpeaker()
        self.voice_player = JarvisVoicePlayer()
        self.engine_name = "utrobin"

        print(f"Speaker готов ✓ backend={self.engine_name}")

    def speak(self, text: str):
        self.engine.speak(text)

    def speak_greeting(self):
        self.voice_player.play_greeting()

    def speak_affirmation(self):
        self.voice_player.play_affirmation()

    def speak_loading(self):
        self.voice_player.play_loading()

    def speak_diagnostics(self):
        self.voice_player.play_diagnostics()

    def speak_reboot(self):
        self.voice_player.play_reboot()

    def speak_shutdown(self):
        self.voice_player.play_shutdown()

    def speak_second_display_active(self):
        self.voice_player.play_second_display_active()

    def speak_first_display_active(self):
        self.voice_player.play_first_display_active()

    def speak_duplicate_display(self):
        self.voice_player.play_duplicate_display()

    def speak_extend_display(self):
        self.voice_player.play_extend_display()

    def speak_import(self):
        self.voice_player.play_layout_scan_complete()