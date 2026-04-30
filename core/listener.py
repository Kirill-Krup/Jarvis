import sounddevice as sd
import json
import queue
import sys
from vosk import Model, KaldiRecognizer
from config.audio_device_manager import AudioDeviceManager

class Listener:
    def __init__(self, model_path="model", auto_detect_device=True, custom_device=None):
        self.q = queue.Queue()

        self.device_manager = AudioDeviceManager()

        if custom_device is not None:
            self.device_manager.set_custom_input_device(custom_device)
        elif auto_detect_device:
            self.device_manager.get_best_input_device()
        else:
            pass

        self.device = self.device_manager.get_current_input_device()

        self.device_manager.print_devices_status()

        print("Загрузка акустической модели Vosk...")
        try:
            self.model = Model(model_path)
        except Exception as e:
            print(f"❌ Ошибка загрузки модели Vosk: {e}")
            print("Убедитесь, что папка 'model' находится в корне проекта!")
            sys.exit(1)

        self.sample_rate = 16000
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        print(f"✅ Listener (Vosk) готов к работе! ({self.sample_rate}Hz)")
        print(f"🎤 Используется микрофон: {sd.query_devices(self.device)['name']}")

    def _callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def switch_device(self, device_index: int) -> bool:
        """Динамически переключает микрофон во время работы"""
        if self.device_manager.set_custom_input_device(device_index):
            self.device = device_index
            print(f"🔄 Переключено на устройство: {sd.query_devices(self.device)['name']}")
            return True
        return False

    def listen(self) -> str | None:
        print("\n🎤 Ожидаю команду...")
        try:
            with sd.RawInputStream(samplerate=self.sample_rate,
                                   blocksize=8000,
                                   device=self.device,
                                   dtype='int16',
                                   channels=1,
                                   callback=self._callback):
                while True:
                    data = self.q.get()
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "")
                        if text:
                            print(f"\n[ФИНАЛ] Джарвис услышал: '{text}'")
                            return text
                    else:
                        partial = json.loads(self.recognizer.PartialResult())
                        partial_text = partial.get("partial", "")
                        if partial_text:
                            print(f"📡 Распознаю: {partial_text}...", end="\r")

        except Exception as e:
            print(f"\n❌ Ошибка захвата звука: {e}")
            return None