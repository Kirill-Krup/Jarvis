"""Слушатель микрофона: Silero VAD (ONNX) + распознавание Vosk."""
import json
import os
import queue
import re
import sys
import time

import numpy as np
import sounddevice as sd
import vosk
from thefuzz import fuzz
from vosk import KaldiRecognizer, Model

from config.audio_device_manager import AudioDeviceManager
from core.vad import BLOCK_SIZE, SAMPLE_RATE, SileroVAD

vosk.SetLogLevel(-1)

MAX_ALTERNATIVES = 3

# Как Vosk часто «слышит» слово «Джарвис»
WAKE_VARIANTS = {
    "джарвис", "жарвис", "гарвис", "дарвис", "джервис", "чарвис", "джарвиса",
    "жарвиса", "жарвес", "жарвесь", "джарис", "жарис", "варгас", "жабры",
    "барвис", "карвис", "сервис", "jarvis",
}
WAKE_PREFIXES = ("джар", "жар", "джер")
WAKE_FUZZY_SCORE = 60
GREETING_RE = re.compile(r"^(эй|привет|слушай|скажи|пожалуйста)\s+", re.IGNORECASE)


class Listener:
    _vad_cache = None
    _vosk_cache = None

    def __init__(self, model_path="model", wake_word="джарвис",
                 auto_detect_device=True, custom_device=None):
        self.q = queue.Queue()
        self.wake_word = wake_word
        self.last_alternatives: list[str] = []

        self.device_manager = AudioDeviceManager()
        if custom_device is not None:
            self.device_manager.set_custom_input_device(custom_device)
        elif auto_detect_device:
            self.device_manager.get_best_input_device()
        self.device = self.device_manager.get_current_input_device()
        self.device_manager.print_devices_status()

        if Listener._vad_cache is None:
            Listener._vad_cache = SileroVAD()
        self.vad = Listener._vad_cache

        if Listener._vosk_cache is None:
            if not os.path.exists(model_path) and os.path.exists("model_small"):
                model_path = "model_small"
            try:
                Listener._vosk_cache = Model(model_path)
            except Exception as e:
                print(f"[ERROR] Не удалось загрузить модель Vosk: {e}")
                print("Папка 'model' или 'model_small' должна лежать в корне проекта.")
                sys.exit(1)

        self.recognizer = KaldiRecognizer(Listener._vosk_cache, SAMPLE_RATE)
        try:
            self.recognizer.SetMaxAlternatives(MAX_ALTERNATIVES)
        except Exception:
            pass

        from config.profile_manager import ProfileManager
        self.profile = ProfileManager()
        self.vad_threshold = self.profile.vad_threshold
        self.silence_ms = self.profile.silence_ms
        self.mic_gain = self.profile.mic_gain

        self.stream = None
        self._start_stream()
        print(f"[OK] Listener: VAD thresh={self.vad_threshold}, "
              f"pause={self.silence_ms}ms, gain={self.mic_gain}x, "
              f"микрофон: {sd.query_devices(self.device)['name']}")

    # ------------------------------------------------------------- поток

    def _start_stream(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        self.stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, device=self.device,
            dtype="int16", channels=1, callback=self._callback)
        self.stream.start()

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def _drain_queue(self):
        while True:
            try:
                self.q.get_nowait()
            except queue.Empty:
                break

    def set_vad_params(self, threshold=None, silence_ms=None, mic_gain=None):
        if threshold is not None:
            self.vad_threshold = float(threshold)
        if silence_ms is not None:
            self.silence_ms = int(silence_ms)
        if mic_gain is not None:
            self.mic_gain = float(mic_gain)

    def switch_device(self, device_index: int) -> bool:
        if self.device_manager.set_custom_input_device(device_index):
            self.device = device_index
            self._start_stream()
            return True
        return False

    # --------------------------------------------------------- калибровка

    def calibrate(self, duration_sec: float = 2.5) -> dict:
        """Замеряет фоновый шум и подбирает порог VAD и усиление."""
        samples = []
        self._drain_queue()
        end = time.time() + duration_sec
        while time.time() < end:
            try:
                data = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            samples.append(np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0)
        if not samples:
            return {"threshold": 0.5, "gain": 1.0, "status": "no_data"}

        audio = np.concatenate(samples)
        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak = float(np.max(np.abs(audio)))

        if rms < 0.012:
            threshold, gain = 0.45, (1.3 if peak < 0.2 else 1.0)
        elif rms < 0.04:
            threshold, gain = 0.50, 1.0
        else:
            threshold, gain = 0.60, 0.9

        self.vad_threshold, self.mic_gain = threshold, gain
        try:
            from config.setup_wizard import load_config, save_config
            cfg = load_config()
            cfg["vad_threshold"], cfg["mic_gain"] = threshold, gain
            save_config(cfg)
            self.profile.reload()
        except Exception:
            pass
        return {"rms": round(rms, 4), "peak": round(peak, 4),
                "threshold": threshold, "gain": gain, "status": "ok"}

    # --------------------------------------------------------- распознавание

    def _final_texts(self) -> list[str]:
        """Варианты распознанной фразы, лучший первым."""
        result = json.loads(self.recognizer.FinalResult())
        if "alternatives" in result:
            texts = [a.get("text", "").strip() for a in result["alternatives"]]
        else:
            texts = [result.get("text", "").strip()]
        return [t for t in texts if t]

    def _vad_listen(self, timeout_sec: float | None = None) -> str:
        block_ms = BLOCK_SIZE / SAMPLE_RATE * 1000
        silence_needed = int(self.silence_ms / block_ms)
        max_wait = int(timeout_sec * SAMPLE_RATE / BLOCK_SIZE) if timeout_sec else None

        silence_frames = wait_frames = 0
        speaking = False

        self.recognizer.Reset()
        self.vad.reset()
        self._drain_queue()
        self.last_alternatives = []

        while True:
            try:
                data = self.q.get(timeout=2.0)
            except queue.Empty:
                if not speaking:
                    break
                continue

            samples = np.frombuffer(data, dtype=np.int16)
            if self.mic_gain != 1.0:
                samples = np.clip(samples.astype(np.float32) * self.mic_gain,
                                  -32768, 32767).astype(np.int16)
                data = samples.tobytes()
            if samples.shape[0] != BLOCK_SIZE:
                continue

            if self.vad(samples) > self.vad_threshold:
                speaking = True
                silence_frames = 0
                self.recognizer.AcceptWaveform(data)
            elif speaking:
                silence_frames += 1
                self.recognizer.AcceptWaveform(data)
                if silence_frames >= silence_needed:
                    break
            elif max_wait is not None:
                wait_frames += 1
                if wait_frames >= max_wait:
                    break

        if not speaking:
            return ""
        texts = self._final_texts()
        self.last_alternatives = texts
        return texts[0] if texts else ""

    def listen_wake_and_command(self) -> tuple[str, str, str] | None:
        """Слушает фразу целиком. Возвращает (trigger, команда, сырой текст)
        или None, если слова «Джарвис» не было."""
        text = self._vad_listen()
        if not text:
            return None

        if any(w in text for w in ("просыпайся", "проснись")):
            return ("wakeup", "", text)

        words = text.split()
        wake_idx = -1
        for idx, word in enumerate(words):
            w = re.sub(r"[^\w]", "", word.lower())
            score = max(fuzz.ratio(w, "джарвис"), fuzz.ratio(w, "жарвис"))
            if (w in WAKE_VARIANTS or w == self.wake_word
                    or score >= WAKE_FUZZY_SCORE or w.startswith(WAKE_PREFIXES)):
                wake_idx = idx
                break
        if wake_idx == -1:
            return None

        command = GREETING_RE.sub("", " ".join(words[wake_idx + 1:]).strip()).strip()
        # альтернативы Vosk тоже обрезаем до команды: пригодятся для исправления
        self.last_alternatives = [self._strip_wake(t) for t in self.last_alternatives]
        return ("wake", command, text)

    def _strip_wake(self, text: str) -> str:
        words = text.split()
        for idx, word in enumerate(words):
            w = re.sub(r"[^\w]", "", word.lower())
            if (w in WAKE_VARIANTS or fuzz.ratio(w, "джарвис") >= WAKE_FUZZY_SCORE
                    or w.startswith(WAKE_PREFIXES)):
                return GREETING_RE.sub("", " ".join(words[idx + 1:])).strip()
        return text

    def listen_wake(self) -> str | None:
        res = self.listen_wake_and_command()
        return res[0] if res else None

    def listen(self, timeout_sec: float | None = None) -> str | None:
        """Слушает речь. Если за timeout_sec никто не заговорил — None."""
        return self._vad_listen(timeout_sec=timeout_sec) or None
