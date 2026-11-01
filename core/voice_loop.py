"""Главный голосовой цикл Джарвиса (общий для окна и консольного режима).

Состояния: ожидание обращения -> команда -> диалог без слова «Джарвис»
(контекст) -> сон -> подтверждение выключения компьютера.
"""
import os
import time
import traceback

from config.settings import WAKE_WORD
from core.logging_utils import log_action, log_error, log_system, log_voice

CONFIRM_TIMEOUT_SEC = 6.0
COMMAND_TIMEOUT_SEC = 5.0
SLEEP_WAKE_TIMEOUT_SEC = 4.0
CHAT_CONTEXT_FACTOR = 2     # после живой беседы ждём продолжения вдвое дольше
MIN_COMMAND_CHARS = 2

STATUS_READY = "Ожидаю обращение..."
HOME_READY = "Системы в норме. Ожидаю голосовую команду..."


class NullUI:
    """Заглушка интерфейса для консольного режима."""

    def set_status(self, text): print(f"[STATUS] {text}")
    def set_home_status(self, text): pass
    def update_speech_info(self, raw_text="", command=""): pass
    def update_execution_info(self, response=""): pass


class VoiceLoop:
    def __init__(self, speaker, listener, commands, profile, ui=None):
        self.speaker = speaker
        self.listener = listener
        self.commands = commands
        self.profile = profile
        self.ui = ui or NullUI()
        self.running = False

        self._sleeping = False
        self._confirm_shutdown = False
        self._in_context = False

    def stop(self):
        self.running = False

    # ---------------------------------------------------------------- цикл

    def run(self):
        self.running = True
        self._ready()
        while self.running:
            try:
                if self._sleeping:
                    self._sleep_step()
                elif self._confirm_shutdown:
                    if self._confirm_step():
                        break
                else:
                    if self._command_step():
                        break
            except KeyboardInterrupt:
                self.speaker.speak_shutdown()
                break
            except BaseException:
                log_error(f"Ошибка в основном цикле:\n{traceback.format_exc()}")
                self._in_context = False

    # --------------------------------------------------------------- шаги

    def _ready(self):
        self.ui.set_status(STATUS_READY)
        self.ui.set_home_status(HOME_READY)

    def _wake_up(self):
        self._sleeping = False
        self.speaker.speak_reboot()
        self._ready()
        log_system("Джарвис вышел из режима сна")

    def _sleep_step(self):
        self.ui.set_status("Режим сна [SLEEP]")
        self.ui.set_home_status("Режим сна")
        trigger = self.listener.listen_wake()
        if trigger == "wakeup":
            self._wake_up()
        elif trigger == "wake":
            heard = self.listener.listen(timeout_sec=SLEEP_WAKE_TIMEOUT_SEC)
            if heard and "проснись" in heard:
                self._wake_up()

    def _confirm_step(self) -> bool:
        """Ждёт «да» для выключения ПК. True — компьютер выключается."""
        self.ui.set_status("Жду подтверждения выключения...")
        answer = self.listener.listen(timeout_sec=CONFIRM_TIMEOUT_SEC)
        if answer and "да" in answer.split():
            self.speaker.speak_shutdown()
            time.sleep(3)
            os.system("shutdown /s /t 0")
            return True
        self._confirm_shutdown = False
        self.speaker.speak("Отменено")
        self._ready()
        log_system("Выключение компьютера отменено")
        return False

    def _command_step(self) -> bool:
        """Принимает и выполняет одну команду. True — завершить работу."""
        command_text = self._listen_command()
        if not command_text:
            return False

        log_action(f"Выполняется команда: '{command_text}'")
        self.ui.set_home_status("Выполняю команду...")
        response = self.commands.handle(
            command_text, alternatives=self.listener.last_alternatives)
        self.ui.update_execution_info(response=response)
        log_action(f"Ответ Джарвиса: '{response}'")
        return self._respond(response)

    def _listen_command(self) -> str | None:
        if self._in_context:
            return self._listen_in_context()

        heard = self.listener.listen_wake_and_command()
        if not heard:
            return None
        trigger, command_text, raw_text = heard
        self.ui.update_speech_info(raw_text=raw_text, command=command_text)
        log_voice(f"Wake word активен: '{raw_text}'")

        if trigger == "wakeup":
            self._wake_up()
            return None

        if not command_text:
            self.ui.set_status("Слушаю команду...")
            self.ui.set_home_status("Слушаю команду...")
            self.speaker.speak_affirmation()
            command_text = self.listener.listen(timeout_sec=COMMAND_TIMEOUT_SEC)
            if command_text:
                self.ui.update_speech_info(
                    raw_text=f"{raw_text} -> {command_text}", command=command_text)
                log_voice(f"Команда после обращения: '{command_text}'")

        if not command_text:
            self.speaker.speak("Не расслышал")
            self._ready()
            return None
        return command_text

    def _listen_in_context(self) -> str | None:
        timeout = self.profile.context_timeout
        if getattr(self.commands, "last_was_chat", False):
            timeout *= CHAT_CONTEXT_FACTOR
        self.ui.set_status(f"Слушаю продолжение ({int(timeout)} сек)...")
        self.ui.set_home_status("Слушаю диалог без кодового слова...")

        heard = self.listener.listen(timeout_sec=timeout)
        text = heard.replace(WAKE_WORD, "").strip() if heard else ""
        if len(text) < MIN_COMMAND_CHARS:
            self._in_context = False
            log_voice(f"Время контекста ({int(timeout)}с) истекло, ожидаю «Джарвис»")
            self._ready()
            return None

        self.ui.update_speech_info(raw_text=heard, command=text)
        log_voice(f"В контексте распознано: '{text}'")
        return text

    def _respond(self, response: str) -> bool:
        """Озвучивает ответ. True — завершить работу."""
        if response == "SHUTDOWN":
            self.speaker.speak_shutdown()
            log_system("Завершение сессии")
            return True
        if response == "CONFIRM_SHUTDOWN_PC":
            self._confirm_shutdown = True
            self._in_context = False
            self.speaker.speak("Вы уверены? Это выключит компьютер")
        elif response == "SLEEP_MODE":
            self._sleeping = True
            self._in_context = False
            self.speaker.speak_loading()
            log_system("Режим сна активирован")
            self.ui.set_home_status("Режим сна")
        else:
            self.speaker.speak(response, soften_honorific=False)
            self._in_context = True

        if not self._in_context:
            self._ready()
        return False
