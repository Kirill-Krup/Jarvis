"""Слушатель микрофона: Silero VAD (ONNX) + распознавание Vosk.

Включает автоматическое восстановление аудиопотока при сбоях Bluetooth/PortAudio,
быструю загрузку модели и защиту от переполнения буфера (input overflow).
"""
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

    def __init__(self, model_path="model_small", wake_word="джарвис",
                 auto_detect_device=True, custom_device=None):
        self.q = queue.Queue()
        self.wake_word = wake_word
        self.last_alternatives: list[str] = []

        from config.profile_manager import ProfileManager
        self.profile = ProfileManager()
        self.vad_threshold = float(self.profile.vad_threshold)
        self.silence_ms = int(self.profile.silence_ms)
        self.mic_gain = float(self.profile.mic_gain)

        # Выбираем модель: по умолчанию model_small для мгновенной загрузки (0.8с вместо 2.5 мин)
        cfg_model = getattr(self.profile, "vosk_model", None)
        if cfg_model and os.path.exists(cfg_model):
            model_path = cfg_model
        elif not os.path.exists(model_path) and os.path.exists("model"):
            model_path = "model"

        # Определяем микрофон: custom -> сохранённый в профиле -> автоопределение
        self.device_manager = AudioDeviceManager()
        saved_device = custom_device if custom_device is not None else self.profile.microphone_index

        if saved_device is not None and self.device_manager.set_custom_input_device(saved_device):
            self.device = saved_device
        elif auto_detect_device:
            self.device = self.device_manager.get_best_input_device()
        else:
            self.device = self.device_manager.get_current_input_device()

        if Listener._vad_cache is None:
            Listener._vad_cache = SileroVAD()
        self.vad = Listener._vad_cache

        if Listener._vosk_cache is None:
            try:
                Listener._vosk_cache = Model(model_path)
            except Exception as e:
                # Резервная попытка загрузки другой папки модели
                fallback_path = "model" if model_path == "model_small" else "model_small"
                if os.path.exists(fallback_path):
                    Listener._vosk_cache = Model(fallback_path)
                else:
                    print(f"[ERROR] Не удалось загрузить модель Vosk: {e}")
                    sys.exit(1)

        self.recognizer = KaldiRecognizer(Listener._vosk_cache, SAMPLE_RATE)
        try:
            self.recognizer.SetMaxAlternatives(MAX_ALTERNATIVES)
        except Exception:
            pass

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
            self.stream = None

        try:
            self.stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, device=self.device,
                dtype="int16", channels=1, callback=self._callback)
            self.stream.start()
        except Exception as e:
            print(f"[ERROR] Сбой запуска микрофона [{self.device}]: {e}")

    def _ensure_stream_active(self):
        """Проверяет работоспособность потока и перезапускает его при сбое."""
        if self.stream is None or not getattr(self.stream, "active", False):
            self._start_stream()
            time.sleep(0.05)

    def _callback(self, indata, frames, time_info, status):
        if status:
            if status.input_overflow:
                self._drain_queue()
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
        self._ensure_stream_active()
        self._drain_queue()
        end = time.time() + duration_sec
        while time.time() < end:
            try:
                data = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            samples.append(np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0)
        if not samples:
            return {"threshold": 0.40, "gain": 1.0, "status": "no_data"}

        audio = np.concatenate(samples)
        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak = float(np.max(np.abs(audio)))

        if rms < 0.012:
            threshold, gain = 0.40, (1.3 if peak < 0.2 else 1.0)
        elif rms < 0.04:
            threshold, gain = 0.45, 1.0
        else:
            threshold, gain = 0.55, 0.9

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

        self._ensure_stream_active()
        self.recognizer.Reset()
        self.vad.reset()
        self._drain_queue()
        self.last_alternatives = []

        # Порог удержания речи (гистерезис VAD)
        hold_threshold = max(0.25, self.vad_threshold * 0.7)

        while True:
            try:
                data = self.q.get(timeout=2.0)
            except queue.Empty:
                if speaking:
                    break
                # Если очередь пуста, восстанавливаем поток и продолжаем ожидание
                self._ensure_stream_active()
                if timeout_sec is not None:
                    break
                continue

            samples = np.frombuffer(data, dtype=np.int16)
            if self.mic_gain != 1.0:
                samples = np.clip(samples.astype(np.float32) * self.mic_gain,
                                  -32768, 32767).astype(np.int16)
                data = samples.tobytes()
            if samples.shape[0] != BLOCK_SIZE:
                continue

            prob = self.vad(samples)

            if prob > self.vad_threshold:
                speaking = True
                silence_frames = 0
                self.recognizer.AcceptWaveform(data)
            elif speaking:
                if prob > hold_threshold:
                    silence_frames = 0
                else:
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
