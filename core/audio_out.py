"""Вывод голоса Джарвиса с учётом его собственной громкости.

Громкость задаётся в настройках («Громкость голоса», 0-100) и не влияет на
системный микшер Windows: меняется только то, насколько громко говорит
сам Джарвис.
"""
import numpy as np
import sounddevice as sd

from config.profile_manager import ProfileManager


def voice_gain() -> float:
    """Множитель громкости голоса 0.0-1.0 из текущих настроек."""
    try:
        percent = ProfileManager().voice_volume
    except Exception:
        percent = 100
    return max(0.0, min(100.0, float(percent))) / 100.0


def play(samples: np.ndarray, sample_rate: int):
    """Проигрывает float-аудио (-1..1) и ждёт окончания."""
    gain = voice_gain()
    if gain <= 0.0:
        return
    data = np.clip(samples.astype(np.float32) * gain, -1.0, 1.0)
    sd.play(data, samplerate=sample_rate)
    sd.wait()
