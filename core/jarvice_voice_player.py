import os
import sounddevice as sd
import soundfile as sf


class JarvisVoicePlayer:
    def __init__(self, base_dir: str = "voice_samples/Jarvis Sound Pack от Jarvis Desktop"):
        self.base_dir = base_dir

    def _play_wav(self, path: str):
        if not os.path.exists(path):
            print(f"[JarvisVoice] Файл не найден: {path}")
            return
        data, samplerate = sf.read(path, dtype="float32")
        sd.play(data, samplerate)
        sd.wait()

    def play_layout_scan_complete(self):
        filename = "Джарвис - приветствие.wav"
        full_path = os.path.join(self.base_dir, filename)
        self._play_wav(full_path)