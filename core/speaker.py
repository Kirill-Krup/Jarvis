import pyttsx3
import threading
from config.profile_manager import ProfileManager


class Speaker:

    def __init__(self):
        self.profile = ProfileManager()
        self.engine = pyttsx3.init()
        self._setup_voice()
        print("Speaker готов ✓")

    def _setup_voice(self):
        voices = self.engine.getProperty('voices')

        honorific = self.profile.honorific
        preferred = "female" if honorific in ["мадам", "госпожа"] else "male"

        selected = None
        for voice in voices:
            name = voice.name.lower()
            if preferred == "male" and any(
                w in name for w in ["david", "mark", "george", "male", "man"]
            ):
                selected = voice
                break
            elif preferred == "female" and any(
                w in name for w in ["zira", "female", "woman", "hazel"]
            ):
                selected = voice
                break

        if selected is None and voices:
            selected = voices[0]

        if selected:
            self.engine.setProperty('voice', selected.id)
            print(f"Голос: {selected.name}")

        self.engine.setProperty('rate', 145)
        self.engine.setProperty('volume', 1.0)

    def speak(self, text: str):
        print(f"Джарвис: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Ошибка Speaker: {e}")
            self.engine = pyttsx3.init()
            self._setup_voice()