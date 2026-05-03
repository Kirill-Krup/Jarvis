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

    def _play_wav(self, path: str):
        if not os.path.exists(path):
            print(f"[JarvisVoice] Файл не найден: {path}")
            return
        data, samplerate = sf.read(path, dtype="float32")
        sd.play(data, samplerate)
        sd.wait()

    def _play_random(self, group: list):
        filename = random.choice(group)
        full_path = os.path.join(self.base_dir, filename)
        self._play_wav(full_path)


    def play_greeting(self):
        self._play_random(self._greeting_group)

    def play_affirmation(self):
        self._play_random(self._affirmation_group)

    def play_loading(self):
        self._play_random(self._loading_group)

    def play_diagnostics(self):
        self._play_random(self._diagnostics_group)

    def play_reboot(self):
        self._play_random(self._reboot_group)

    def play_shutdown(self):
        self._play_random(self._shutdown_group)

    def play_diagnostics_done(self):
        self._play_random(self.diagnostics_done)

    def play_second_display_active(self):
        self._play_random(self._second_display)

    def play_first_display_active(self):
        self._play_random(self._first_display)

    def play_duplicate_display(self):
        self._play_random(self._duplicate_display)

    def play_extend_display(self):
        self._play_random(self._extend_display)

    def play_layout_scan_complete(self):
        self._play_wav("voice_samples/jarvis_ru/Импортирую установки, начинаю калибровку виртуальной среды.wav")

    def play_low_batery(self):
        self._play_wav("voice_samples/jarvis_ru/Включилось аварийное резервное питание.wav ")