"""Детектор речи Silero VAD на onnxruntime.

Раньше для VAD загружался весь PyTorch (сотни МБ ОЗУ и десятки секунд
импорта). Эта же модель в формате ONNX весит ~2 МБ и работает на уже
установленном onnxruntime.
"""
import os

import numpy as np
import onnxruntime as ort
import requests

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "silero_vad.onnx",
)

MODEL_URL = ("https://raw.githubusercontent.com/snakers4/silero-vad/"
             "master/src/silero_vad/data/silero_vad.onnx")
SAMPLE_RATE = 16000
BLOCK_SIZE = 512      # сэмплов в блоке при 16 кГц
CONTEXT_SIZE = 64     # хвост предыдущего блока, который требует модель


class SileroVAD:
    def __init__(self, model_path: str = MODEL_PATH):
        if not os.path.exists(model_path):
            self._download(model_path)
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self._session = ort.InferenceSession(
            model_path, sess_options=opts, providers=["CPUExecutionProvider"])
        self._sr = np.array(SAMPLE_RATE, dtype=np.int64)
        self.reset()

    @staticmethod
    def _download(model_path: str):
        """Модель весит ~2 МБ: при первом запуске скачиваем, если её нет в models/."""
        print(f"Скачиваю модель VAD в {model_path}...")
        try:
            response = requests.get(MODEL_URL, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise FileNotFoundError(
                f"Не найдена модель VAD: {model_path} (и скачать не удалось: {e}). "
                f"Скачайте файл вручную: {MODEL_URL}") from e
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        with open(model_path, "wb") as f:
            f.write(response.content)

    def reset(self):
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, CONTEXT_SIZE), dtype=np.float32)

    def __call__(self, chunk_int16: np.ndarray) -> float:
        """Вероятность речи (0..1) для блока из 512 int16-сэмплов."""
        chunk = chunk_int16.astype(np.float32) / 32768.0
        x = np.concatenate([self._context, chunk[None, :]], axis=1)
        out, self._state = self._session.run(
            None, {"input": x, "state": self._state, "sr": self._sr})
        self._context = x[:, -CONTEXT_SIZE:]
        return float(out[0][0])
