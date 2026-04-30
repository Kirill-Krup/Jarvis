from config.profile_manager import ProfileManager
from core.speakers.utrobin_speaker import UtrobinSpeaker

class Speaker:
    def __init__(self):
        self.profile = ProfileManager()
        self.engine_name = getattr(self.profile, "tts_engine", None) or "utrobin"
        self.engine = UtrobinSpeaker()
        self.engine_name = "utrobin"

        print(f"Speaker готов ✓ backend={self.engine_name}")

    def speak(self, text: str):
        self.engine.speak(text)