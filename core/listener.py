import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
import tempfile
import os


class Listener:

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.sample_rate = 16000
        self.duration = 5
        print("Listener готов ✓")

    def listen(self) -> str | None:
        try:
            print("Слушаю...")

            audio_data = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
            )
            sd.wait()

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".wav"
            ) as tmp:
                tmp_path = tmp.name

            sf.write(tmp_path, audio_data, self.sample_rate)

            with sr.AudioFile(tmp_path) as source:
                audio = self.recognizer.record(source)

            os.unlink(tmp_path)

            text = self.recognizer.recognize_google(
                audio, language="ru-RU"
            )
            print(f"Распознано: {text}")
            return text.lower()

        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"Ошибка Listener: {e}")
            return None