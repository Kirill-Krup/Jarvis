import os
import threading
import sounddevice as sd
import numpy as np
from config.profile_manager import ProfileManager
from piper import PiperVoice


class Speaker:

    def __init__(self):
        self.profile = ProfileManager()
        self._load_model()
        print("Speaker (Piper) готов ✓")

    def _load_model(self):
        print("Загружаю голосовую модель Piper...")

        model_path = "voice_samples/ru_RU-ruslan-medium.onnx"
        config_path = "voice_samples/ru_RU-ruslan-medium.onnx.json"

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Файл модели не найден: {model_path}")

        self.model = PiperVoice.load(model_path, config_path)
        self.sample_rate = self.model.config.sample_rate
        print(f"✅ Модель загружена! Частота: {self.sample_rate} Гц ✓")

    def speak(self, text: str):
        """Главный метод озвучки (как в Silero)"""
        print(f"Джарвис: {text}")
        try:
            audio_thread = threading.Thread(target=self._generate_and_play, args=(text,))
            audio_thread.start()
            audio_thread.join()
        except Exception as e:
            print(f"Ошибка Speaker: {e}")

    def _generate_and_play(self, text: str):
        """Генерирует и воспроизводит речь (как Silero)"""
        try:
            # Собираем все аудио-чанки в один массив
            audio_parts = []

            for audio_chunk in self.model.synthesize(text):
                # AudioChunk имеет свойство audio_int16_bytes, которое возвращает bytes!
                audio_parts.append(audio_chunk.audio_int16_bytes)

            if audio_parts:
                # Объединяем все байты
                audio_bytes = b''.join(audio_parts)

                # Преобразуем в numpy array (как Silero возвращает)
                audio_numpy = np.frombuffer(audio_bytes, dtype=np.int16)

                # Воспроизводим (как в Silero, но без .numpy() т.к. это уже numpy array)
                sd.play(audio_numpy, samplerate=self.sample_rate)
                sd.wait()
            else:
                print("Не удалось получить аудио данные")

        except Exception as e:
            print(f"Ошибка генерации речи: {e}")
            import traceback
            traceback.print_exc()