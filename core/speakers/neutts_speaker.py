import os
import threading
import tempfile

import numpy as np
import sounddevice as sd
import soundfile as sf

from core.base_speaker import BaseSpeaker


class NeuTTSSpeaker(BaseSpeaker):
    def __init__(
        self,
        ref_audio_path="voice_samples/jarvis_ref.wav",
        ref_text_path="voice_samples/jarvis_ref.txt",
        backbone_repo="neuphonic/neutts-air-q4-gguf",
        codec_repo="neuphonic/neucodec",
        device="cpu",
    ):
        self.ref_audio_path = ref_audio_path
        self.ref_text_path = ref_text_path
        self.backbone_repo = backbone_repo
        self.codec_repo = codec_repo
        self.device = device

        self.tts = None
        self.ref_codes = None
        self.ref_text = None
        self.sample_rate = 24000

        self._load_model()
        print("NeuTTSSpeaker готов ✓")

    def _load_model(self):
        print("Загружаю NeuTTS Air...")

        if not os.path.exists(self.ref_audio_path):
            raise FileNotFoundError(
                f"Не найден reference audio: {self.ref_audio_path}\n"
                f"Положи туда 5-15 секунд WAV с голосом."
            )

        if not os.path.exists(self.ref_text_path):
            raise FileNotFoundError(
                f"Не найден reference text: {self.ref_text_path}\n"
                f"Положи рядом точную расшифровку sample."
            )

        with open(self.ref_text_path, "r", encoding="utf-8") as f:
            self.ref_text = f.read().strip()

        try:
            from neuttsair.neutts import NeuTTSAir
        except ImportError:
            raise ImportError(
                "Не установлен NeuTTS Air.\n"
                "Установи зависимости проекта NeuTTS Air и пакет neuttsair."
            )

        self.tts = NeuTTSAir(
            backbone_repo=self.backbone_repo,
            backbone_device=self.device,
            codec_repo=self.codec_repo,
            codec_device=self.device,
        )

        self.ref_codes = self.tts.encode_reference(self.ref_audio_path)
        print("✅ NeuTTS Air загружен и reference voice закодирован")

    def speak(self, text: str):
        print(f"Джарвис: {text}")
        try:
            audio_thread = threading.Thread(target=self._generate_and_play, args=(text,))
            audio_thread.start()
            audio_thread.join()
        except Exception as e:
            print(f"Ошибка NeuTTSSpeaker: {e}")

    def _generate_and_play(self, text: str):
        try:
            wav = self.tts.infer(text, self.ref_codes, self.ref_text)

            if isinstance(wav, list):
                wav = np.array(wav, dtype=np.float32)
            elif not isinstance(wav, np.ndarray):
                wav = np.array(wav, dtype=np.float32)

            wav = np.clip(wav, -1.0, 1.0).astype(np.float32)

            sd.play(wav, samplerate=self.sample_rate)
            sd.wait()

        except Exception as e:
            print(f"Ошибка генерации речи NeuTTSSpeaker: {e}")
            import traceback
            traceback.print_exc()

    def synth_to_file(self, text: str, out_path: str):
        wav = self.tts.infer(text, self.ref_codes, self.ref_text)
        if not isinstance(wav, np.ndarray):
            wav = np.array(wav, dtype=np.float32)
        sf.write(out_path, wav, self.sample_rate)