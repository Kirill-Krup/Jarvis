import numpy as np
import sounddevice as sd
import json
import queue
import sys
import torch
from vosk import Model, KaldiRecognizer
from config.audio_device_manager import AudioDeviceManager


class Listener:
    BLOCK_SIZE  = 512
    SAMPLE_RATE = 16000

    _vad_model_cache = None

    def __init__(self, model_path="model", wake_word="джарвис",
                 auto_detect_device=True, custom_device=None):
        self.q         = queue.Queue()
        self.wake_word = wake_word
        self.device_manager = AudioDeviceManager()
        if custom_device is not None:
            self.device_manager.set_custom_input_device(custom_device)
        elif auto_detect_device:
            self.device_manager.get_best_input_device()
        self.device = self.device_manager.get_current_input_device()
        self.device_manager.print_devices_status()

        if Listener._vad_model_cache is None:
            print("Загрузка Silero VAD...")
            vad_model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                verbose=False
            )
            vad_model.eval()
            Listener._vad_model_cache = vad_model
            print("✅ VAD готов!")
        else:
            print("✅ VAD готов! (из кеша)")

        self.vad_model = Listener._vad_model_cache

        print("Загрузка акустической модели Vosk...")
        try:
            self.model = Model(model_path)
        except Exception as e:
            print(f"❌ Ошибка загрузки модели Vosk: {e}")
            print("Убедитесь, что папка 'model' находится в корне проекта!")
            sys.exit(1)

        self.recognizer = KaldiRecognizer(self.model, self.SAMPLE_RATE)
        self._rebuild_wake_recognizer()

        print(f"✅ Listener готов! ({self.SAMPLE_RATE}Hz)")
        print(f"🎤 Микрофон: {sd.query_devices(self.device)['name']}")

    def _rebuild_wake_recognizer(self):
        self.wake_recognizer = KaldiRecognizer(self.model, self.SAMPLE_RATE)
        self.wake_recognizer.SetGrammar(
            json.dumps(
                [self.wake_word, "гарвис", "дарвис", "жарвис",
                 "просыпайся", "проснись", "[unk]"],
                ensure_ascii=False
            )
        )

    def _callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def _vad_listen(self, recognizer: KaldiRecognizer,
                    silence_ms: int = 400,
                    threshold: float = 0.5) -> str:

        silence_needed = int(silence_ms / ((self.BLOCK_SIZE / self.SAMPLE_RATE) * 1000))
        audio_buffer   = []
        silence_frames = 0
        speaking       = False

        with sd.RawInputStream(
            samplerate=self.SAMPLE_RATE,
            blocksize=self.BLOCK_SIZE,
            device=self.device,
            dtype='int16',
            channels=1,
            callback=self._callback
        ):
            while not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    break

            while True:
                data = self.q.get()

                chunk = torch.from_numpy(
                    np.frombuffer(data, dtype=np.int16).copy()
                ).float() / 32768.0

                if chunk.shape[0] != self.BLOCK_SIZE:
                    continue

                with torch.no_grad():
                    speech_prob = self.vad_model(chunk, self.SAMPLE_RATE).item()

                if speech_prob > threshold:
                    if not speaking:
                        print("🗣️  Говорите...", end="\r")
                    speaking       = True
                    silence_frames = 0
                    audio_buffer.append(data)
                elif speaking:
                    silence_frames += 1
                    audio_buffer.append(data)
                    if silence_frames >= silence_needed:
                        break
        if not audio_buffer:
            return ""

        full_audio = b"".join(audio_buffer)
        recognizer.AcceptWaveform(full_audio)
        result = json.loads(recognizer.FinalResult())
        return result.get("text", "").strip()

    def listen_wake(self) -> str | None:

        self._rebuild_wake_recognizer()

        text = self._vad_listen(
            recognizer=self.wake_recognizer,
            silence_ms=300,
            threshold=0.6
        )

        if not text:
            return None

        if any(w in text for w in (self.wake_word, "гарвис", "дарвис", "жарвис",
                                    "просыпайся", "проснись")):
            print(f"🔔 Wake detected: '{text}'")

        if self.wake_word in text or any(w in text for w in ("гарвис", "дарвис", "жарвис")):
            return "wake"
        if any(w in text for w in ("просыпайся", "проснись")):
            return "wakeup"

        return None

    def listen(self) -> str | None:
        print("\n🎤 Слушаю команду...")
        text = self._vad_listen(
            recognizer=self.recognizer,
            silence_ms=500,
            threshold=0.5
        )
        if text:
            print(f"\n[ФИНАЛ] Джарвис услышал: '{text}'")
        return text or None

    def switch_device(self, device_index: int) -> bool:
        if self.device_manager.set_custom_input_device(device_index):
            self.device = device_index
            print(f"🔄 Переключено: {sd.query_devices(self.device)['name']}")
            return True
        return False