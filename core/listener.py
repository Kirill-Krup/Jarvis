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
        self.device = 2

        self.silence_threshold = 50
        self.silence_duration = 1.5
        self.max_duration = 15
        self.chunk_duration = 0.1

        print("Listener готов ✓")

    def listen(self) -> str | None:
        try:
            chunks_per_second = int(1 / self.chunk_duration)
            chunk_size = int(self.sample_rate * self.chunk_duration)
            max_chunks = int(self.max_duration / self.chunk_duration)
            silence_chunks_needed = int(
                self.silence_duration / self.chunk_duration
            )

            audio_chunks = []
            silence_chunks = 0
            speech_started = False

            print("👂 Жду голос...", end="", flush=True)

            for i in range(max_chunks):
                chunk = sd.rec(
                    chunk_size,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="int16",
                    device=self.device,
                )
                sd.wait()

                volume = np.abs(chunk).mean()

                if volume > self.silence_threshold:
                    if not speech_started:
                        print("\n🎤 Слушаю...", end="", flush=True)
                        speech_started = True
                    silence_chunks = 0
                    audio_chunks.append(chunk)

                elif speech_started:
                    silence_chunks += 1
                    audio_chunks.append(chunk)

                    if silence_chunks % 5 == 0:
                        print(".", end="", flush=True)

                    if silence_chunks >= silence_chunks_needed:
                        print(" готово!")
                        break

            if not audio_chunks or not speech_started:
                return None


            full_audio = np.concatenate(audio_chunks, axis=0)

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".wav"
            ) as tmp:
                tmp_path = tmp.name

            sf.write(tmp_path, full_audio, self.sample_rate)

            with sr.AudioFile(tmp_path) as source:
                audio = self.recognizer.record(source)

            os.unlink(tmp_path)

            text = self.recognizer.recognize_google(
                audio, language="ru-RU"
            )
            print(f"✅ Распознано: '{text}'")
            return text.lower()

        except sr.UnknownValueError:
            print("\n❓ Не распознано")
            return None
        except sr.RequestError as e:
            print(f"\n🌐 Ошибка сети: {e}")
            return None
        except Exception as e:
            print(f"\n❌ Ошибка: {type(e).__name__}: {e}")
            return None