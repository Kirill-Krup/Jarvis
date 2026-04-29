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

        # Определяем устройство автоматически
        devices = sd.query_devices()
        default_input = sd.query_devices(kind='input')

        # Находим индекс дефолтного устройства
        self.device = None
        for i, dev in enumerate(devices):
            if dev['name'] == default_input['name']:
                self.device = i
                break

        # Узнаем сколько каналов поддерживает
        self.channels = min(2, default_input['max_input_channels'])

        print(f"\n✅ Использую: {default_input['name']}")
        print(f"   device={self.device}, channels={self.channels}\n")

    def listen(self) -> str | None:
        try:
            print("🎤 Записываю 5 секунд...")

            audio_data = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,  # 1 или 2 автоматически
                dtype="int16",
                device=self.device,  # автоматический индекс
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