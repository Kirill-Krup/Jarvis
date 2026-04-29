import os
import torch
import sounddevice as sd
from config.profile_manager import ProfileManager


class Speaker:

    def __init__(self):
        self.profile = ProfileManager()
        self._load_model()
        print("Speaker готов ✓")

    def _load_model(self):
        print("Загружаю голосовую модель Silero...")

        self.model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="ru",
            speaker="v4_ru",
        )

        self.sample_rate = 48000

        self.speaker_voice = "eugene"

        print(f"Голос: {self.speaker_voice} ✓")

    def speak(self, text: str):
        print(f"Джарвис: {text}")
        try:
            audio = self.model.apply_tts(
                text=text,
                speaker=self.speaker_voice,
                sample_rate=self.sample_rate,
            )
            sd.play(audio.numpy(), samplerate=self.sample_rate)
            sd.wait()

        except Exception as e:
            print(f"Ошибка Speaker: {e}")