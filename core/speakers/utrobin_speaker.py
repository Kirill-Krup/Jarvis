import os
import threading
import sounddevice as sd
import numpy as np
import onnxruntime
from transformers import AutoTokenizer
from ruaccent import RUAccent

from core.base_speaker import BaseSpeaker


class UtrobinSpeaker(BaseSpeaker):
    def __init__(self):
        self._load_model()
        print("UtrobinSpeaker готов ✓")

    def _load_model(self):
        print("Загружаю голосовую модель UtrobinTTS...")

        model_path = "voice_samples/model.onnx"

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Файл модели не найден: {model_path}\n"
                f"Скачайте model.onnx из:\n"
                f"https://huggingface.co/utrobinmv/tts_ru_free_hf_vits_low_multispeaker"
            )

        sess_options = onnxruntime.SessionOptions()
        self.model = onnxruntime.InferenceSession(model_path, sess_options=sess_options)

        self.tokenizer = AutoTokenizer.from_pretrained(
            "utrobinmv/tts_ru_free_hf_vits_low_multispeaker"
        )

        self.accentizer = RUAccent()
        self.accentizer.load(omograph_model_size='turbo', use_dictionary=True)

        self.sample_rate = 16000
        self.speaker_id = 1

        print(f"✅ UtrobinTTS загружен, sample_rate={self.sample_rate}, speaker_id={self.speaker_id}")

    def speak(self, text: str):
        print(f"Джарвис: {text}")
        try:
            audio_thread = threading.Thread(target=self._generate_and_play, args=(text,))
            audio_thread.start()
            audio_thread.join()
        except Exception as e:
            print(f"Ошибка UtrobinSpeaker: {e}")

    def _generate_and_play(self, text: str):
        try:
            text_lower = text.lower()
            text_with_accents = self.accentizer.process_all(text_lower)

            inputs = self.tokenizer(text_with_accents, return_tensors="np")
            sid = np.array([self.speaker_id])

            output = self.model.run(
                None,
                {
                    "input_ids": inputs["input_ids"],
                    "attention_mask": inputs["attention_mask"],
                    "sid": sid,
                },
            )[0]

            audio_array = output[0]
            audio_array = np.clip(audio_array, -1, 1)
            audio_int16 = (audio_array * 32767).astype(np.int16)

            sd.play(audio_int16, samplerate=self.sample_rate)
            sd.wait()

        except Exception as e:
            print(f"Ошибка генерации речи UtrobinSpeaker: {e}")
            import traceback
            traceback.print_exc()