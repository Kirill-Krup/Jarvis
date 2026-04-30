from config.profile_manager import ProfileManager
from core.speakers.neutts_speaker import NeuTTSSpeaker
from core.speakers.utrobin_speaker import UtrobinSpeaker


class Speaker:
    def __init__(self):
        self.profile = ProfileManager()
        self.engine_name = getattr(self.profile, "tts_engine", None) or "utrobin"

        if self.engine_name == "neutts":
            try:
                self.engine = NeuTTSSpeaker(
                    ref_audio_path="voice_samples/jarvis_ref.wav",
                    ref_text_path="voice_samples/jarvis_ref.txt",
                    backbone_repo="neuphonic/neutts-air-q4-gguf",
                    codec_repo="neuphonic/neucodec",
                    device="cpu",
                )
            except Exception as e:
                print(f"⚠ NeuTTS не загрузился, откатываюсь на UtrobinTTS: {e}")
                self.engine = UtrobinSpeaker()
                self.engine_name = "utrobin"
        else:
            self.engine = UtrobinSpeaker()
            self.engine_name = "utrobin"

        print(f"Speaker готов ✓ backend={self.engine_name}")

    def speak(self, text: str):
        self.engine.speak(text)