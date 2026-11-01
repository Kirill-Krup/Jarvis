"""Синтез речи: UtrobinTTS (VITS, ONNX) + расстановка ударений RUAccent."""
import os
import queue
import re
import threading

import numpy as np
import onnxruntime

from core import audio_out
from core.speakers.base_speaker import BaseSpeaker

try:
    import num2words
except ImportError:
    num2words = None

MODEL_PATH = "voice_samples/model.onnx"
TOKENIZER_REPO = "utrobinmv/tts_ru_free_hf_vits_low_multispeaker"
SAMPLE_RATE = 16000
SPEAKER_ID = 1
ACCENT_CACHE_LIMIT = 300

_SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")


def verbalize_numbers(text: str) -> str:
    """Числа и дроби -> русские слова, чтобы TTS их читал."""
    if not num2words:
        return text

    def frac(m):
        try:
            whole, part = m.group(0).replace(",", ".").split(".")
            return (f"{num2words.num2words(int(whole), lang='ru')} целых "
                    f"{num2words.num2words(int(part), lang='ru')} сотых")
        except Exception:
            return m.group(0)

    def integer(m):
        try:
            return num2words.num2words(int(m.group(0)), lang="ru")
        except Exception:
            return m.group(0)

    text = re.sub(r"\b\d+[.,]\d+\b", frac, text)
    return re.sub(r"\b\d+\b", integer, text)


class UtrobinSpeaker(BaseSpeaker):
    def __init__(self):
        self._accent_cache: dict[str, str] = {}
        self._lock = threading.Lock()   # одна реплика за раз
        self._load_model()
        print("UtrobinSpeaker готов [OK]")

    def _load_model(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Файл модели не найден: {MODEL_PATH}\n"
                f"Скачайте model.onnx из https://huggingface.co/{TOKENIZER_REPO}")

        opts = onnxruntime.SessionOptions()
        opts.intra_op_num_threads = 2
        self.model = onnxruntime.InferenceSession(
            MODEL_PATH, sess_options=opts, providers=["CPUExecutionProvider"])

        from transformers import AutoTokenizer
        from ruaccent import RUAccent
        self.tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_REPO)
        self.accentizer = RUAccent()
        self.accentizer.load(omograph_model_size="turbo", use_dictionary=True)

        try:  # прогрев графа, чтобы первая фраза не тормозила
            self._synthesize("пр+ивет")
        except Exception:
            pass

    # ------------------------------------------------------------------ API

    def speak(self, text: str):
        if not text or not str(text).strip():
            return
        text = verbalize_numbers(str(text))
        print(f"Джарвис: {text}")

        sentences = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
        with self._lock:
            try:
                self._speak_pipelined(sentences)
            except Exception as e:
                print(f"[TTS] Ошибка озвучки: {e}")

    # ------------------------------------------------------------- internals

    def _speak_pipelined(self, sentences: list[str]):
        """Пока играет одно предложение, готовится следующее."""
        audio_q: queue.Queue = queue.Queue(maxsize=2)

        def producer():
            for sentence in sentences:
                try:
                    audio_q.put(self._synthesize(self._accent(sentence)))
                except Exception as e:
                    print(f"[TTS] Ошибка генерации: {e}")
            audio_q.put(None)

        threading.Thread(target=producer, daemon=True).start()
        while True:
            audio = audio_q.get()
            if audio is None:
                break
            audio_out.play(audio, SAMPLE_RATE)

    def _accent(self, sentence: str) -> str:
        key = sentence.lower().strip()
        cached = self._accent_cache.get(key)
        if cached is not None:
            return cached
        try:
            accented = self.accentizer.process_all(key)
        except Exception:
            accented = key
        if len(self._accent_cache) >= ACCENT_CACHE_LIMIT:
            self._accent_cache.pop(next(iter(self._accent_cache)))
        self._accent_cache[key] = accented
        return accented

    def _synthesize(self, accented_text: str) -> np.ndarray:
        inputs = self.tokenizer(accented_text, return_tensors="np")
        output = self.model.run(None, {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
            "sid": np.array([SPEAKER_ID]),
        })[0]
        audio = output[0]
        if audio is None or len(audio) == 0:
            raise ValueError("пустой аудио-буфер")
        return np.clip(audio, -1.0, 1.0)
