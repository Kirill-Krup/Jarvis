import threading
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
import comtypes
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class VolumeControl:
    _instance = None
    _lock = threading.Lock()
    _logged = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.volume = None
        self._init_endpoint()
        self._initialized = True
        if not VolumeControl._logged:
            print("VolumeControl готов [OK]")
            VolumeControl._logged = True

    def _init_endpoint(self):
        try:
            try:
                comtypes.CoInitialize()
            except Exception:
                pass
            device = AudioUtilities.GetSpeakers()
            if device and hasattr(device, "_dev") and device._dev:
                interface = device._dev.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                )
                self.volume = cast(interface, POINTER(IAudioEndpointVolume))
        except Exception as e:
            if not VolumeControl._logged:
                print(f"VolumeControl ошибка: {e}")
            self.volume = None

    def _ensure_ready(self) -> bool:
        try:
            comtypes.CoInitialize()
        except Exception:
            pass
        if not self.volume:
            self._init_endpoint()
        return self.volume is not None

    def get_volume(self) -> int:
        try:
            if not self._ensure_ready():
                return 50
            return round(self.volume.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            self.volume = None
            return 50

    def set_volume(self, percent: int):
        try:
            if not self._ensure_ready():
                return
            percent = max(0, min(100, int(percent)))
            self.volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
        except Exception:
            self.volume = None

    def change_volume(self, delta: int):
        self.set_volume(self.get_volume() + delta)

    def mute(self):
        try:
            if self._ensure_ready():
                self.volume.SetMute(1, None)
        except Exception:
            self.volume = None

    def unmute(self):
        try:
            if self._ensure_ready():
                self.volume.SetMute(0, None)
        except Exception:
            self.volume = None
