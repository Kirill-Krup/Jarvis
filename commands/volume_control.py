from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL


class VolumeControl:

    def __init__(self):
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None
        )
        self.volume = interface.QueryInterface(IAudioEndpointVolume)
        print("VolumeControl готов ✓")

    def get_volume(self) -> int:
        return round(self.volume.GetMasterVolumeLevelScalar() * 100)

    def set_volume(self, percent: int):
        percent = max(0, min(100, percent))
        self.volume.SetMasterVolumeLevelScalar(percent / 100, None)

    def change_volume(self, delta: int):
        self.set_volume(self.get_volume() + delta)

    def mute(self):
        self.volume.SetMute(1, None)

    def unmute(self):
        self.volume.SetMute(0, None)