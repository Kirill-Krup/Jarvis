import os
import sys
import subprocess
import time
import threading
import traceback
import tkinter as tk

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config.setup_wizard import is_first_run, run_setup
from config.profile_manager import ProfileManager
from core.jarvice_voice_player import JarvisVoicePlayer
from ui.gui import SplashScreen, MainWindow
from ui.tray import TrayApp
from core.speakers.speaker import Speaker
from core.listener import Listener
from commands.command_handler import CommandHandler

from core.logging_utils import log, log_voice, log_action, log_system, log_error
from core.startup_mode import should_start_hidden


class JarvisApp:
    def __init__(self):
        self._profile = None
        self._speaker = None
        self._listener = None
        self._commands = None
        self._main_win = None
        self._tray = None
        self._running = False
        self._root = None
        self._start_hidden = should_start_hidden()
        self._jarvis_voice = JarvisVoicePlayer()

    def start(self):
        log_system("JARVIS запускается...")

        try:
            if is_first_run():
                run_setup()
        except SystemExit as e:
            log(f"SystemExit в setup: code={e.code}")
            return
        except BaseException:
            log_error(f"Ошибка setup:\n{traceback.format_exc()}")

        try:
            self._root = tk.Tk()
            self._root.report_callback_exception = self._on_tk_exception
        except BaseException:
            log_error(f"Ошибка инициализации Tk:\n{traceback.format_exc()}")
            return

        if self._start_hidden:
            self._root.withdraw()
            threading.Thread(
                target=self._load_components_hidden,
                daemon=True
            ).start()
        else:
            try:
                splash = SplashScreen(self._root)
            except BaseException:
                log_error(f"Ошибка инициализации GUI:\n{traceback.format_exc()}")
                return

            threading.Thread(
                target=self._load_components_with_splash,
                args=(splash,),
                daemon=True
            ).start()

        try:
            self._root.mainloop()
        except BaseException:
            log_error(f"Ошибка mainloop:\n{traceback.format_exc()}")

        log_system("JARVIS остановлен")

    def _on_tk_exception(self, exc, val, tb):
        log_error(f"Ошибка Tk callback:\n{''.join(traceback.format_exception(exc, val, tb))}")

    def _load_components_with_splash(self, splash: SplashScreen):
        steps = [
            (15, "Загрузка профиля...", lambda: setattr(self, "_profile", ProfileManager())),
            (35, "Инициализация речи...", lambda: setattr(self, "_speaker", Speaker())),
            (45, "Инициализация микрофона...", lambda: setattr(self, "_listener", Listener())),
            (65, "Загрузка команд...", lambda: setattr(self, "_commands", CommandHandler(self._speaker))),
            (80, "Запуск голосового модуля...", self.ensure_ollama),
            (90, "Запуск трея...", self._start_tray_only),
            (100, "Готово", None),
        ]

        try:
            for percent, status, fn in steps:
                splash.update_progress(percent, status)
                if fn:
                    fn()
                time.sleep(0.25)
        except SystemExit as e:
            log(f"SystemExit при загрузке компонентов: code={e.code}")
            return
        except BaseException:
            log_error(f"Ошибка загрузки компонентов:\n{traceback.format_exc()}")
            return

        self._root.after(0, self._transition_to_main, splash, True)

    def _load_components_hidden(self):
        try:
            self._profile = ProfileManager()
            self._speaker = Speaker()
            self._listener = Listener()
            self._commands = CommandHandler(self._speaker)
            self._tray = TrayApp(on_exit_callback=self._on_exit)
            self._tray.start()
        except SystemExit as e:
            log(f"SystemExit при тихой загрузке: code={e.code}")
            return
        except BaseException:
            log_error(f"Ошибка тихой загрузки:\n{traceback.format_exc()}")
            return

        self._root.after(0, self._transition_to_main, None, False)

    def _start_tray_only(self):
        self._tray = TrayApp(on_exit_callback=self._on_exit)
        self._tray.start()

    def on_manual_command(self, cmd_text: str):
        threading.Thread(target=self._run_manual_cmd, args=(cmd_text,), daemon=True).start()

    def _run_manual_cmd(self, cmd_text: str):
        try:
            self._main_win.update_speech_info(raw_text=f"[Ручной ввод]: {cmd_text}", command=cmd_text)
            self._main_win.set_home_status("Выполняю команду...")
            log_action(f"Ручная команда: '{cmd_text}'")
            response = self._commands.handle(cmd_text)
            self._main_win.update_execution_info(response=response)
            log_action(f"Ответ: {response}")
            if response == "SHUTDOWN":
                self._speaker.speak_shutdown()
                self._on_exit()
            elif response == "SLEEP_MODE":
                self._speaker.speak_loading()
            else:
                self._speaker.speak(response)
            self._main_win.set_home_status("Системы в норме. Ожидаю команду...")
        except Exception as e:
            log_error(f"Ошибка выполнения ручной команды: {e}")

    def _transition_to_main(self, splash, show_window: bool):
        try:
            if splash is not None:
                splash.destroy()

            self._main_win = MainWindow(
                root=self._root,
                profile_name=self._profile.name if self._profile else "—",
                honorific=self._profile.honorific if self._profile else "",
                on_exit=self._on_exit,
                on_command=self.on_manual_command,
                listener=self._listener,
                volume_control=self._commands.volume_control if self._commands else None,
                speaker=self._speaker,
            )

            if self._tray:
                self._tray.set_main_window(self._main_win)

            if show_window:
                self._main_win.show()
            else:
                self._main_win.hide()

            self._running = True
            threading.Thread(target=self._jarvis_loop, daemon=True).start()
        except BaseException:
            log_error(f"Ошибка перехода к главному окну:\n{traceback.format_exc()}")

    def _jarvis_loop(self):
        try:
            if self._main_win:
                self._main_win.set_status("Ожидаю обращение...")
                self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
            if not self._start_hidden:
                self._speaker.speak_import()
                self._speaker.speak_greeting()
        except BaseException:
            log_error(f"Ошибка старта голосового цикла:\n{traceback.format_exc()}")
            return

        sleeping = False
        waiting_for_shutdown_confirm = False
        in_context = False

        while self._running:
            try:
                if sleeping:
                    self._main_win.set_status("Режим сна [SLEEP]")
                    self._main_win.set_home_status("Режим сна")

                    trigger = self._listener.listen_wake()

                    if trigger == "wakeup":
                        sleeping = False
                        self._speaker.speak_reboot()
                        self._main_win.set_status("Ожидаю обращение...")
                        self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
                        log_system("Джарвис вышел из режима сна")

                    elif trigger == "wake":
                        cmd = self._listener.listen(timeout_sec=4.0)
                        if cmd and "проснись" in cmd:
                            sleeping = False
                            self._speaker.speak_reboot()
                            self._main_win.set_status("Ожидаю обращение...")
                            self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
                            log_system("Джарвис проснулся")

                    continue

                if waiting_for_shutdown_confirm:
                    self._main_win.set_status("Жду подтверждения выключения...")
                    confirm = self._listener.listen(timeout_sec=6.0)
                    if confirm and "да" in confirm:
                        self._speaker.speak_shutdown()
                        time.sleep(3)
                        os.system("shutdown /s /t 0")
                        break
                    else:
                        waiting_for_shutdown_confirm = False
                        self._speaker.speak(f"Отменено, {self._profile.honorific}")
                        self._main_win.set_status("Ожидаю обращение...")
                        self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
                        log_system("Выключение компьютера отменено")
                    continue

                # Таймаут контекста берем из настроек пользователя
                context_timeout = self._profile.context_timeout if self._profile else 5.0

                if in_context:
                    self._main_win.set_status(f"Слушаю продолжение ({int(context_timeout)} сек)...")
                    self._main_win.set_home_status("Слушаю диалог без кодового слова...")

                    command_text = self._listener.listen(timeout_sec=context_timeout)

                    # Если за время контекста речи не было — молча выходим из контекста
                    if not command_text:
                        in_context = False
                        log_voice(f"Время контекста ({int(context_timeout)}с) истекло, ожидаю «Джарвис»")
                        self._main_win.set_status("Ожидаю обращение...")
                        self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
                        continue

                    raw_text = command_text
                    from config.settings import WAKE_WORD
                    if WAKE_WORD in command_text.lower():
                        command_text = command_text.lower().replace(WAKE_WORD, "").strip()

                    # Фильтрация короткого микрофонного шума
                    if len(command_text.strip()) < 2:
                        in_context = False
                        self._main_win.set_status("Ожидаю обращение...")
                        self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
                        continue

                    self._main_win.update_speech_info(raw_text=raw_text, command=command_text)
                    log_voice(f"В контексте распознано: '{command_text}'")

                else:
                    trigger_data = self._listener.listen_wake_and_command()
                    if not trigger_data:
                        continue

                    trigger, command_text, raw_text = trigger_data
                    self._main_win.update_speech_info(raw_text=raw_text, command=command_text)
                    log_voice(f"Wake word активен: '{raw_text}'")

                    if trigger == "wakeup":
                        sleeping = False
                        self._speaker.speak_reboot()
                        self._main_win.set_status("Ожидаю обращение...")
                        self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
                        continue

                    if not command_text:
                        self._main_win.set_status("Слушаю команду...")
                        self._main_win.set_home_status("Слушаю команду...")
                        self._speaker.speak_affirmation()
                        command_text = self._listener.listen(timeout_sec=5.0)
                        if command_text:
                            self._main_win.update_speech_info(raw_text=f"{raw_text} -> {command_text}", command=command_text)
                            log_voice(f"Команда после обращения: '{command_text}'")

                    if not command_text:
                        self._speaker.speak(f"Не расслышал, {self._profile.honorific}")
                        self._main_win.set_status("Ожидаю обращение...")
                        self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
                        continue

                log_action(f"Выполняется команда: '{command_text}'")
                self._main_win.set_home_status("Выполняю команду...")
                response = self._commands.handle(command_text)
                self._main_win.update_execution_info(response=response)
                log_action(f"Ответ Джарвиса: '{response}'")

                if response == "SHUTDOWN":
                    self._speaker.speak_shutdown()
                    log_system("Завершение сессии")
                    break
                elif response == "CONFIRM_SHUTDOWN_PC":
                    waiting_for_shutdown_confirm = True
                    in_context = False
                    self._speaker.speak(f"Вы уверены, {self._profile.honorific}? Это выключит компьютер")
                elif response == "SLEEP_MODE":
                    sleeping = True
                    in_context = False
                    self._speaker.speak_loading()
                    log_system("Режим сна активирован")
                    self._main_win.set_home_status("Режим сна")
                else:
                    self._speaker.speak(response)
                    # Включаем режим контекста
                    in_context = True

                if not in_context:
                    self._main_win.set_status("Ожидаю обращение...")
                    self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")

            except BaseException:
                log_error(f"Ошибка в основном цикле:\n{traceback.format_exc()}")
                in_context = False

    def ensure_ollama(self):
        import shutil
        if not shutil.which("ollama"):
            log_system("Ollama не установлена на системе, запуск пропущен")
            return
        try:
            import requests
            requests.get("http://localhost:11434", timeout=1)
            log_system("Сервер Ollama уже запущен [OK]")
            threading.Thread(target=self._warmup_ollama, daemon=True).start()
        except Exception:
            try:
                log_system("Запускаю сервер Ollama...")
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                threading.Thread(target=self._warmup_ollama, daemon=True).start()
            except Exception as e:
                log_error(f"Не удалось запустить сервер Ollama: {e}")

    def _warmup_ollama(self):
        try:
            log_system("Прогрев модели в фоне...")
            self._commands.ollama.warmup()
            log_system("Модель готова [OK]")
        except Exception as e:
            log_error(f"Прогрев Ollama не удался: {e}")

    def _on_exit(self):
        log_system("JARVIS завершение работы")
        self._running = False
        if self._tray:
            self._tray.stop()
        if self._root:
            self._root.after(0, self._root.destroy)


if __name__ == "__main__":
    try:
        JarvisApp().start()
    except SystemExit as e:
        log(f"SystemExit: code={e.code}")
    except BaseException:
        log_error(f"Критическая ошибка:\n{traceback.format_exc()}")
        sys.exit(1)
