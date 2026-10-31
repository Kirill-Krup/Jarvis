import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys
import json
import re
import queue
import time
import numpy as np
import sounddevice as sd
import torch
import vosk
from thefuzz import fuzz
from vosk import Model, KaldiRecognizer
from config.audio_device_manager import AudioDeviceManager

# Отключаем спам в логах Vosk/Kaldi для ускорения загрузки и консольного ввода-вывода
vosk.SetLogLevel(-1)


class Listener:
    BLOCK_SIZE  = 512
    SAMPLE_RATE = 16000

    _vad_model_cache = None
    _vosk_model_cache = None

    def __init__(self, model_path="model", wake_word="джарвис",
                 auto_detect_device=True, custom_device=None):
        self.q = queue.Queue()
        self.wake_word = wake_word
        self.device_manager = AudioDeviceManager()
        if custom_device is not None:
            self.device_manager.set_custom_input_device(custom_device)
        elif auto_detect_device:
            self.device_manager.get_best_input_device()
        self.device = self.device_manager.get_current_input_device()
        self.device_manager.print_devices_status()

        # 1. Загрузка Silero VAD (локальный кэш без сетевых задержек)
        if Listener._vad_model_cache is None:
            print("Загрузка Silero VAD...")
            hub_dir = torch.hub.get_dir()
            local_vad_path = os.path.join(hub_dir, "snakers4_silero-vad_master")
            if os.path.exists(local_vad_path):
                vad_model, _ = torch.hub.load(
                    local_vad_path,
                    'silero_vad',
                    source='local',
                    verbose=False
                )
            else:
                vad_model, _ = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    verbose=False,
                    trust_repo=True
                )
            vad_model.eval()
            Listener._vad_model_cache = vad_model
            print("[OK] VAD готов!")
        else:
            print("[OK] VAD готов! (из кэша)")

        self.vad_model = Listener._vad_model_cache

        # 2. Загрузка акустической модели Vosk (с кэшированием)
        if Listener._vosk_model_cache is None:
            print("Загрузка акустической модели Vosk...")
            if not os.path.exists(model_path) and os.path.exists("model_small"):
                model_path = "model_small"
            try:
                Listener._vosk_model_cache = Model(model_path)
            except Exception as e:
                print(f"❌ Ошибка загрузки модели Vosk: {e}")
                print("Убедитесь, что папка 'model' или 'model_small' находится в корне проекта!")
                sys.exit(1)

        self.model = Listener._vosk_model_cache
        self.recognizer = KaldiRecognizer(self.model, self.SAMPLE_RATE)
        self.wake_recognizer = KaldiRecognizer(self.model, self.SAMPLE_RATE)
        self.wake_recognizer.SetGrammar(
            json.dumps(
                [self.wake_word, "гарвис", "дарвис", "жарвис",
                 "просыпайся", "проснись", "[unk]"],
                ensure_ascii=False
            )
        )

        # 3. Настройки чувствительности VAD и усиления из профиля
        from config.profile_manager import ProfileManager
        self.profile = ProfileManager()
        self.vad_threshold = getattr(self.profile, "vad_threshold", 0.5)
        self.silence_ms = getattr(self.profile, "silence_ms", 400)
        self.mic_gain = getattr(self.profile, "mic_gain", 1.0)

        # 4. Постоянный поток аудио
        self.stream = None
        self._start_stream()

        print(f"[OK] Listener готов! ({self.SAMPLE_RATE}Hz) VAD: thresh={self.vad_threshold}, pause={self.silence_ms}ms, gain={self.mic_gain}x")
        print(f"[MIC] Микрофон: {sd.query_devices(self.device)['name']}")

    def _start_stream(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        self.stream = sd.RawInputStream(
            samplerate=self.SAMPLE_RATE,
            blocksize=self.BLOCK_SIZE,
            device=self.device,
            dtype='int16',
            channels=1,
            callback=self._callback
        )
        self.stream.start()

    def _callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def _drain_queue(self):
        while not self.q.empty():
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
        print(f"[VAD CONFIG] thresh={self.vad_threshold}, pause={self.silence_ms}ms, gain={self.mic_gain}x")

    def calibrate(self, duration_sec: float = 2.5) -> dict:
        """Замеряет уровень фонового шума в помещении и калибрует VAD порог."""
        print(f"[CALIBRATE] Замер шума {duration_sec}с...")
        samples = []
        self._drain_queue()
        start_time = time.time()
        while time.time() - start_time < duration_sec:
            try:
                data = self.q.get(timeout=0.2)
                arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                samples.append(arr)
            except queue.Empty:
                pass
        if not samples:
            return {"threshold": 0.5, "gain": 1.0, "status": "no_data"}

        all_audio = np.concatenate(samples)
        rms = float(np.sqrt(np.mean(all_audio ** 2)))
        peak = float(np.max(np.abs(all_audio)))

        # Автоматическая настройка порога VAD и усиления
        if rms < 0.012:
            rec_thresh = 0.45
            rec_gain = 1.3 if peak < 0.2 else 1.0
        elif rms < 0.04:
            rec_thresh = 0.50
            rec_gain = 1.0
        else:
            rec_thresh = 0.60
            rec_gain = 0.9

        self.vad_threshold = rec_thresh
        self.mic_gain = rec_gain

        try:
            from config.setup_wizard import load_config, save_config
            cfg = load_config()
            cfg["vad_threshold"] = rec_thresh
            cfg["mic_gain"] = rec_gain
            save_config(cfg)
            self.profile.reload()
        except Exception:
            pass

        return {
            "rms": round(rms, 4),
            "peak": round(peak, 4),
            "threshold": rec_thresh,
            "gain": rec_gain,
            "status": "ok"
        }

    def _vad_listen(self, recognizer: KaldiRecognizer,
                    silence_ms: int | None = None,
                    threshold: float | None = None,
                    timeout_sec: float | None = None) -> str:

        effective_silence = silence_ms if silence_ms is not None else self.silence_ms
        effective_thresh = threshold if threshold is not None else self.vad_threshold

        silence_needed = int(effective_silence / ((self.BLOCK_SIZE / self.SAMPLE_RATE) * 1000))
        silence_frames = 0
        speaking       = False
        has_audio      = False

        recognizer.Reset()
        self._drain_queue()

        # Таймаут на ожидание начала речи
        max_wait_frames = None
        if timeout_sec is not None and timeout_sec > 0:
            max_wait_frames = int(timeout_sec * (self.SAMPLE_RATE / self.BLOCK_SIZE))
        wait_frames = 0

        while True:
            try:
                data = self.q.get(timeout=2.0)
            except queue.Empty:
                if not speaking:
                    break
                continue

            raw_np = np.frombuffer(data, dtype=np.int16).copy()
            if self.mic_gain != 1.0:
                boosted = np.clip(raw_np.astype(np.float32) * self.mic_gain, -32768, 32767).astype(np.int16)
                data = boosted.tobytes()
                chunk = torch.from_numpy(boosted).float() / 32768.0
            else:
                chunk = torch.from_numpy(raw_np).float() / 32768.0

            if chunk.shape[0] != self.BLOCK_SIZE:
                continue

            with torch.no_grad():
                speech_prob = self.vad_model(chunk, self.SAMPLE_RATE).item()

            if speech_prob > effective_thresh:
                if not speaking:
                    print("[VAD]  Говорите...", end="\r", flush=True)
                speaking       = True
                has_audio      = True
                silence_frames = 0
                recognizer.AcceptWaveform(data)
            elif speaking:
                silence_frames += 1
                recognizer.AcceptWaveform(data)
                if silence_frames >= silence_needed:
                    break
            else:
                # Если речь еще не началась, проверяем лимит времени
                if max_wait_frames is not None:
                    wait_frames += 1
                    if wait_frames >= max_wait_frames:
                        break

        if not has_audio:
            return ""

        result = json.loads(recognizer.FinalResult())
        return result.get("text", "").strip()

    def listen_wake_and_command(self) -> tuple[str, str, str] | None:
        """
        Быстрое нечёткое (fuzzy) распознавание wake-word и команды в одной фразе.
        Возвращает: (trigger, command_text, raw_heard_text) или None.
        """
        text = self._vad_listen(
            recognizer=self.recognizer,
            silence_ms=self.silence_ms,
            threshold=self.vad_threshold
        )

        if not text:
            return None

        # Проверка на просыпание
        if any(w in text for w in ("просыпайся", "проснись")):
            return ("wakeup", "", text)

        wake_exact = {
            self.wake_word, "джарвис", "жарвис", "гарвис", "дарвис", "джервис",
            "чарвис", "джарвиса", "жарвиса", "жарвес", "жарвесь", "джарис", "жарис",
            "варгас", "жабры", "барвис", "карвис", "сервис", "jarvis"
        }

        words = text.split()
        wake_idx = -1

        for idx, w in enumerate(words):
            w_clean = re.sub(r'[^\w]', '', w.lower())
            score = max(fuzz.ratio(w_clean, "джарвис"), fuzz.ratio(w_clean, "жарвис"))
            if w_clean in wake_exact or score >= 60 or w_clean.startswith(("джар", "жар", "джер")):
                wake_idx = idx
                break

        if wake_idx == -1:
            return None

        # Команда — всё, что сказано ПОСЛЕ слова-триггера (отсекая предваряющий шум)
        raw_command = " ".join(words[wake_idx + 1:]).strip()
        command = re.sub(r"^(эй|привет|слушай|скажи|пожалуйста)\s+", "", raw_command, flags=re.IGNORECASE).strip()
        print(f"[WAKE] Wake detected! Полная фраза: '{text}' -> Команда: '{command}'")
        return ("wake", command, text)

    def listen_wake(self) -> str | None:
        res = self.listen_wake_and_command()
        if res:
            return res[0]
        return None

    def listen(self, timeout_sec: float | None = None) -> str | None:
        """Слушает речь с микрофона.
        
        Если задан timeout_sec и пользователь не начал говорить за это время,
        немедленно возвращает None.
        """
        if timeout_sec:
            print(f"\n[MIC] Слушаю команду (таймаут {timeout_sec:.1f}с)...")
        else:
            print("\n[MIC] Слушаю команду...")

        text = self._vad_listen(
            recognizer=self.recognizer,
            silence_ms=self.silence_ms,
            threshold=self.vad_threshold,
            timeout_sec=timeout_sec
        )
        if text:
            print(f"\n[ФИНАЛ] Джарвис услышал: '{text}'")
        return text or None

    def switch_device(self, device_index: int) -> bool:
        if self.device_manager.set_custom_input_device(device_index):
            self.device = device_index
            self._start_stream()
            print(f"[SWITCH] Переключено: {sd.query_devices(self.device)['name']}")
            return True
        return False
