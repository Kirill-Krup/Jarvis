import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
import tempfile
import os
import numpy as np


class Listener:

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.sample_rate = 16000
        self.duration = 5

        # Показываем все устройства для диагностики
        print("\n=== Доступные аудио устройства ===")
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                print(f"  [{i}] 🎤 {dev['name']}")

        # Берём дефолтный input девайс
        default = sd.query_devices(kind='input')
        print(f"\nИспользую: {default['name']}")
        print(f"Listener готов ✓\n")

        self.device = 2

    def listen(self) -> str | None:
        try:
            print("🎤 Записываю 5 секунд...")

            audio_data = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                device=self.device,
            )
            sd.wait()

            volume = np.abs(audio_data).mean()
            print(f"📊 Громкость: {volume:.1f}")

            if volume < 50:
                print("🔇 Тишина — пропускаю")
                return None

            with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".wav"
            ) as tmp:
                tmp_path = tmp.name

            sf.write(tmp_path, audio_data, self.sample_rate)

            print("🔍 Распознаю...")
            with sr.AudioFile(tmp_path) as source:
                audio = self.recognizer.record(source)

            os.unlink(tmp_path)

            text = self.recognizer.recognize_google(
                audio, language="ru-RU"
            )
            print(f"✅ Распознано: '{text}'")
            return text.lower()

        except sr.UnknownValueError:
            print("❓ Не распознано")
            return None
        except sr.RequestError as e:
            print(f"🌐 Ошибка сети: {e}")
            return None
        except Exception as e:
            print(f"❌ Ошибка: {type(e).__name__}: {e}")
            return None