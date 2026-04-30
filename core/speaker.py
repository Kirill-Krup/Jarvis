import os
import threading
import sounddevice as sd
import numpy as np
import onnxruntime
from transformers import AutoTokenizer
from ruaccent import RUAccent
from config.profile_manager import ProfileManager


class Speaker:

    def __init__(self):
        self.profile = ProfileManager()
        self._load_model()
        print("Speaker (UtrobinTTS) готов ✓")

    def _load_model(self):
        print("Загружаю голосовую модель UtrobinTTS...")

        model_path = "voice_samples/model.onnx"

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Файл модели не найден: {model_path}\n"
                f"Скачайте model.onnx из репозитория:\n"
                f"https://huggingface.co/utrobinmv/tts_ru_free_hf_vits_low_multispeaker/tree/main\n"
                f"И положите в папку voice_samples/tts_ru_free_hf_vits_low_multispeaker/"
            )

        # Загружаем ONNX модель
        sess_options = onnxruntime.SessionOptions()
        self.model = onnxruntime.InferenceSession(model_path, sess_options=sess_options)

        # Загружаем токенизатор
        self.tokenizer = AutoTokenizer.from_pretrained("utrobinmv/tts_ru_free_hf_vits_low_multispeaker")

        self.accentizer = RUAccent()
        self.accentizer.load(omograph_model_size='turbo', use_dictionary=True)

        self.sample_rate = 16000
        self.speaker_id = 1

        print(
            f"✅ Модель загружена! Частота: {self.sample_rate} Гц, голос: {'мужской' if self.speaker_id == 1 else 'женский'} ✓")

    def speak(self, text: str):
        print(f"Джарвис: {text}")
        try:
            audio_thread = threading.Thread(target=self._generate_and_play, args=(text,))
            audio_thread.start()
            audio_thread.join()
        except Exception as e:
            print(f"Ошибка Speaker: {e}")

    def _generate_and_play(self, text: str):
        try:
            text_lower = text.lower()

            text_with_accents = self.accentizer.process_all(text_lower)
            print(f"📖 С ударениями: {text_with_accents[:100]}..." if len(
                text_with_accents) > 100 else f"📖 С ударениями: {text_with_accents}")

            inputs = self.tokenizer(text_with_accents, return_tensors="np")

            sid = np.array([self.speaker_id])

            output = self.model.run(
                None,
                {
                    "input_ids": inputs['input_ids'],
                    "attention_mask": inputs['attention_mask'],
                    "sid": sid,
                },
            )[0]

            audio_array = output[0]

            audio_array = np.clip(audio_array, -1, 1)
            audio_int16 = (audio_array * 32767).astype(np.int16)

            sd.play(audio_int16, samplerate=self.sample_rate)
            sd.wait()

        except Exception as e:
            print(f"Ошибка генерации речи: {e}")
            import traceback
            traceback.print_exc()