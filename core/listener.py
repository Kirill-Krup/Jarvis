import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
import tempfile
import os
import numpy as np


class Listener:
    def __init__(self):
        self.recognizer = sr.Recognizer()

        # Ставим None, чтобы Python взял микрофон "По умолчанию" из настроек Windows
        self.device = None

        # Пытаемся получить параметры дефолтного устройства
        try:
            device_info = sd.query_devices(self.device, 'input')
            self.sample_rate = int(device_info['default_samplerate'])
        except Exception:
            self.sample_rate = 44100

        self.chunk_duration = 0.1
        self.silence_duration = 1.2
        self.max_duration = 10

        # Понижаем порог до минимума для теста
        self.silence_threshold = 0.005

        print(f"✅ Listener: Использование системного микрофона ({self.sample_rate}Hz)")

    def listen(self) -> str | None:
        try:
            chunk_size = int(self.sample_rate * self.chunk_duration)
            max_chunks = int(self.max_duration / self.chunk_duration)
            silence_chunks_needed = int(self.silence_duration / self.chunk_duration)

            audio_chunks = []
            silence_chunks = 0
            speech_started = False

            print("\n--- ТЕСТ ЗВУКА (скажите что-нибудь громко) ---")

            for i in range(max_chunks):
                # Записываем 2 канала (стерео), так как некоторые драйверы не любят моно
                recording = sd.rec(chunk_size, samplerate=self.sample_rate,
                                   channels=2, dtype="float32", device=self.device)
                sd.wait()

                # Берем среднее по каналам и вычисляем громкость
                chunk = np.mean(recording, axis=1)
                volume = np.abs(chunk).mean()

                # ЭТОТ ПРИНТ ДОЛЖЕН МЕНЯТЬСЯ, КОГДА ВЫ ГОВОРИТЕ
                print(f"Уровень сигнала: {volume:.5f} (Порог: {self.silence_threshold})", end="\r")

                if volume > self.silence_threshold:
                    if not speech_started:
                        print(f"\n🎤 СИГНАЛ ПОЙМАН! Записываю... (Громкость: {volume:.4f})")
                        speech_started = True
                    silence_chunks = 0
                    audio_chunks.append(chunk)
                elif speech_started:
                    silence_chunks += 1
                    audio_chunks.append(chunk)
                    if silence_chunks >= silence_chunks_needed:
                        print("✅ Запись завершена.")
                        break

            if not audio_chunks or not speech_started:
                print(
                    "\n\n🔇 Микрофон молчит. Проверьте: Настройки Windows -> Конфиденциальность -> Микрофон (разрешить доступ приложениям).")
                return None

            full_audio = np.concatenate(audio_chunks, axis=0)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp_path = tmp.name
                sf.write(tmp_path, full_audio, self.sample_rate)

            try:
                with sr.AudioFile(tmp_path) as source:
                    audio = self.recognizer.record(source)

                print("🤖 Распознаю через Google...")
                text = self.recognizer.recognize_google(audio, language="ru-RU")
                print(f"✅ Результат: '{text}'")
                return text.lower()
            except Exception as e:
                print(f"\n❓ Ошибка распознавания: {e}")
                return None
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            return None