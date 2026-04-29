import re
from commands.app_launcher import AppLauncher
from commands.volume_control import VolumeControl
from config.profile_manager import ProfileManager


class CommandHandler:

    def __init__(self, speaker):
        self.app_launcher = AppLauncher()
        self.volume_control = VolumeControl()
        self.profile = ProfileManager()
        self.speaker = speaker

        self.command_map = {
            "открой":            self._handle_open,
            "запусти":           self._handle_open,
            "громче":            self._handle_volume_up,
            "тише":              self._handle_volume_down,
            "выключи звук":      self._handle_mute,
            "включи звук":       self._handle_unmute,
            "громкость":         self._handle_volume_set,
            "отдыхай":           self._handle_sleep,
            "спи":               self._handle_sleep,
            "выключись":         self._handle_shutdown,
            "завершить работу":  self._handle_shutdown,
        }
        print("CommandHandler готов ✓")

    def _reply(self, text: str) -> str:
        return f"{text}, {self.profile.honorific}"

    def handle(self, text: str) -> str:
        text_lower = text.lower().strip()
        for keyword, method in self.command_map.items():
            if keyword in text_lower:
                return method(text_lower)
        return self._handle_question(text)

    def _handle_open(self, text: str) -> str:
        app_name = (
            text.replace("открой", "")
                .replace("запусти", "")
                .strip()
        )
        if not app_name:
            return self._reply("Что именно открыть")
        return self.app_launcher.launch(app_name, self.profile.honorific)

    def _handle_volume_up(self, text: str) -> str:
        self.volume_control.change_volume(+10)
        return self._reply("Увеличиваю громкость")

    def _handle_volume_down(self, text: str) -> str:
        self.volume_control.change_volume(-10)
        return self._reply("Уменьшаю громкость")

    def _handle_mute(self, text: str) -> str:
        self.volume_control.mute()
        return self._reply("Звук выключен")

    def _handle_unmute(self, text: str) -> str:
        self.volume_control.unmute()
        return self._reply("Звук включён")

    def _handle_volume_set(self, text: str) -> str:
        numbers = re.findall(r'\d+', text)
        if numbers:
            level = int(numbers[0])
            self.volume_control.set_volume(level)
            return self._reply(f"Устанавливаю громкость {level} процентов")
        return self._reply(
            "Укажите уровень громкости, например: громкость 50"
        )

    def _handle_sleep(self, text: str) -> str:
        return "SLEEP_MODE"

    def _handle_shutdown(self, text: str) -> str:
        if "завершить работу" in text:
            return "CONFIRM_SHUTDOWN_PC"
        return "SHUTDOWN"

    def _handle_question(self, text: str) -> str:
        print(f"\n[AI ЗАГЛУШКА] Вопрос: '{text}'")
        return self._reply("AI модуль пока не подключён")