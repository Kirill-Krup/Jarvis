"""Проигрывание заранее записанных фраз Джарвиса (если файлы есть в
voice_samples/jarvis_ru/). Если файла нет, Speaker озвучит фразу через TTS."""
import os
import random

import soundfile as sf

from core import audio_out

GROUPS = {
    "greeting": ["Джарвис - приветствие.wav", "Мы подключены и готовы.wav"],
    "second_display": ["Первый экран деактивирован.mp3"],
    "first_display": ["Второй экран деактивирован.mp3"],
    "extend_display": ["Экраны расширены.mp3"],
    "duplicate_display": ["Дублирование экранов активировано.mp3"],
    "affirmation": ["К вашим услугам сэр.wav"],
    "loading": ["Загружаю сэр.wav", "Как пожелаете .wav", "Запрос выполнен сэр .wav"],
    "reboot": ["Я перезагрузился сэр.wav"],
    "shutdown": ["Отключаю питание.wav"],
    "layout_scan": ["Импортирую установки, начинаю калибровку виртуальной среды.wav"],
}


class JarvisVoicePlayer:
    def __init__(self, base_dir: str = "voice_samples/jarvis_ru/"):
        self.base_dir = base_dir

    def _play(self, group: str) -> bool:
        path = os.path.join(self.base_dir, random.choice(GROUPS[group]))
        if not os.path.exists(path):
            return False
        try:
            data, rate = sf.read(path, dtype="float32")
            audio_out.play(data, rate)
            return True
        except Exception:
            return False

    def play_greeting(self): return self._play("greeting")
    def play_affirmation(self): return self._play("affirmation")
    def play_loading(self): return self._play("loading")
    def play_reboot(self): return self._play("reboot")
    def play_shutdown(self): return self._play("shutdown")
    def play_second_display_active(self): return self._play("second_display")
    def play_first_display_active(self): return self._play("first_display")
    def play_duplicate_display(self): return self._play("duplicate_display")
    def play_extend_display(self): return self._play("extend_display")
    def play_layout_scan_complete(self): return self._play("layout_scan")
