import os
import random
import sounddevice as sd
import soundfile as sf


class JarvisVoicePlayer:
    def __init__(self, base_dir: str = "voice_samples/jarvis_ru/"):
        self.base_dir = base_dir

        self._greeting_group = [
            "Джарвис - приветствие.wav",
            "Мы подключены и готовы.wav"
        ]

        self._second_display = [
            "Первый экран деактивирован.mp3",
        ]

        self._first_display = [
            "Второй экран деактивирован.mp3",
        ]

        self._extend_display = [
            "Экраны расширены.mp3",
        ]

        self._duplicate_display = [
            "Дублирование экранов активировано.mp3",
        ]

        self._affirmation_group = [
            "К вашим услугам сэр.wav"
        ]

        self._loading_group = [
            "Загружаю сэр.wav",
            "Как пожелаете .wav",
            "Запрос выполнен сэр .wav"
        ]
        
        self._diagnostics_group = [
            "Начинаю диагностику системы.wav",
        ]

        self.diagnostics_done = [
            "Проверка завершена.wav"
        ]

        self._reboot_group = [
            "Я перезагрузился сэр.wav"
        ]
        
        self._shutdown_group = [
            "Отключаю питание.wav"
        ]

    def _play_wav(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        try:
            data, samplerate = sf.read(path, dtype="float32")
            sd.play(data, samplerate)
            sd.wait()
            return True
        except Exception:
            return False

    def _play_random(self, group: list) -> bool:
        if not group:
            return False
        filename = random.choice(group)
        full_path = os.path.join(self.base_dir, filename)
        return self._play_wav(full_path)

    def play_greeting(self) -> bool:
        return self._play_random(self._greeting_group)

    def play_affirmation(self) -> bool:
        return self._play_random(self._affirmation_group)

    def play_loading(self) -> bool:
        return self._play_random(self._loading_group)

    def play_diagnostics(self) -> bool:
        return self._play_random(self._diagnostics_group)

    def play_reboot(self) -> bool:
        return self._play_random(self._reboot_group)

    def play_shutdown(self) -> bool:
        return self._play_random(self._shutdown_group)

    def play_diagnostics_done(self) -> bool:
        return self._play_random(self.diagnostics_done)

    def play_second_display_active(self) -> bool:
        return self._play_random(self._second_display)

    def play_first_display_active(self) -> bool:
        return self._play_random(self._first_display)

    def play_duplicate_display(self) -> bool:
        return self._play_random(self._duplicate_display)

    def play_extend_display(self) -> bool:
        return self._play_random(self._extend_display)

    def play_layout_scan_complete(self) -> bool:
        return self._play_wav(os.path.join(self.base_dir, "Импортирую установки, начинаю калибровку виртуальной среды.wav"))

    def play_low_batery(self) -> bool:
        return self._play_wav(os.path.join(self.base_dir, "Включилось аварийное резервное питание.wav"))
