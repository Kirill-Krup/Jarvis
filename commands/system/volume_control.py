from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class VolumeControl:

    def __init__(self):
        try:
            device = AudioUtilities.GetSpeakers()
            interface = device._dev.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            self.volume = cast(interface, POINTER(IAudioEndpointVolume))
            print("VolumeControl готов [OK]")
        except Exception as e:
            print(f"VolumeControl ошибка: {e}")
            self.volume = None

    def get_volume(self) -> int:
        if not self.volume:
            return 50
        return round(self.volume.GetMasterVolumeLevelScalar() * 100)

    def set_volume(self, percent: int):
        if not self.volume:
            return
        percent = max(0, min(100, percent))
        self.volume.SetMasterVolumeLevelScalar(percent / 100, None)

    def change_volume(self, delta: int):
        self.set_volume(self.get_volume() + delta)

    def mute(self):
        if self.volume:
            self.volume.SetMute(1, None)

    def unmute(self):
        if self.volume:
            self.volume.SetMute(0, None)