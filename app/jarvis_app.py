import os
import subprocess
import time
import threading
import traceback
import tkinter as tk

from config.setup_wizard import is_first_run, run_setup
from config.profile_manager import ProfileManager
from config.settings import WAKE_WORD
from core.jarvice_voice_player import JarvisVoicePlayer
from ui.gui import SplashScreen, MainWindow
from ui.tray import TrayApp
from core.speaker import Speaker
from core.listener import Listener
from commands.command_handler import CommandHandler
from thefuzz import fuzz

from core.logging_utils import log
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
        log("JARVIS start")

        try:
            if is_first_run():
                run_setup()
        except SystemExit as e:
            log(f"SystemExit в setup: code={e.code}")
            return
        except BaseException:
            log(f"Ошибка setup:\n{traceback.format_exc()}")

        try:
            self._root = tk.Tk()
            self._root.report_callback_exception = self._on_tk_exception
        except BaseException:
            log(f"Ошибка инициализации Tk:\n{traceback.format_exc()}")
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
                log(f"Ошибка инициализации GUI:\n{traceback.format_exc()}")
                return

            threading.Thread(
                target=self._load_components_with_splash,
                args=(splash,),
                daemon=True
            ).start()

        try:
            self._root.mainloop()
        except BaseException:
            log(f"Ошибка mainloop:\n{traceback.format_exc()}")

        log("JARVIS stop")

    def _on_tk_exception(self, exc, val, tb):
        log(f"Ошибка Tk callback:\n{''.join(traceback.format_exception(exc, val, tb))}")

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
            log(f"Ошибка загрузки компонентов:\n{traceback.format_exc()}")
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
            log(f"Ошибка тихой загрузки:\n{traceback.format_exc()}")
            return

        self._root.after(0, self._transition_to_main, None, False)

    def _start_tray_only(self):
        self._tray = TrayApp(on_exit_callback=self._on_exit)
        self._tray.start()

    def _transition_to_main(self, splash, show_window: bool):
        try:
            if splash is not None:
                splash.destroy()

            self._main_win = MainWindow(
                root=self._root,
                profile_name=self._profile.name if self._profile else "—",
                honorific=self._profile.honorific if self._profile else "",
                on_exit=self._on_exit,
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
            log(f"Ошибка перехода к главному окну:\n{traceback.format_exc()}")

    def _jarvis_loop(self):
        try:
            if self._main_win:
                self._main_win.set_status("Ожидаю обращение...")
                self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
            if not self._start_hidden:
                self._speaker.speak_import()
                self._speaker.speak_greeting()
        except BaseException:
            log(f"Ошибка старта голосового цикла:\n{traceback.format_exc()}")
            return

        sleeping = False
        waiting_for_shutdown_confirm = False

        while self._running:
            try:
                if sleeping:
                    self._main_win.set_status("Режим сна 💤")
                    self._main_win.set_home_status("Режим сна")

                    trigger = self._listener.listen_wake()

                    if trigger == "wakeup":
                        sleeping = False
                        self._speaker.speak_reboot()
                        self._main_win.set_status("Ожидаю обращение...")
                        self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")

                    elif trigger == "wake":
                        cmd = self._listener.listen()
                        if cmd and "проснись" in cmd:
                            sleeping = False
                            self._speaker.speak_reboot()
                            self._main_win.set_status("Ожидаю обращение...")
                            self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")

                    continue

                if waiting_for_shutdown_confirm:
                    self._main_win.set_status("Жду подтверждения выключения...")
                    confirm = self._listener.listen()
                    if confirm and "да" in confirm:
                        self._speaker.speak_shutdown()
                        time.sleep(3)
                        os.system("shutdown /s /t 0")
                        break
                    else:
                        waiting_for_shutdown_confirm = False
                        self._speaker.speak(f"Отменено, {self._profile.honorific}")
                    continue

                if not self._listener.listen_wake():
                    continue

                self._main_win.log(f"Активирован wake-word")
                self._main_win.set_status("Слушаю команду...")
                self._main_win.set_home_status("Слушаю команду...")
                self._speaker.speak_loading()

                command_text = self._listener.listen()

                if not command_text:
                    self._speaker.speak(f"Не расслышал, {self._profile.honorific}")
                    self._main_win.set_status("Ожидаю обращение...")
                    self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")
                    continue

                self._main_win.log(f"Команда: '{command_text}'")
                self._main_win.set_home_status("Выполняю команду...")
                response = self._commands.handle(command_text)

                if response == "SHUTDOWN":
                    self._speaker.speak_shutdown()
                    self._main_win.log("Завершение сессии")
                    break
                elif response == "CONFIRM_SHUTDOWN_PC":
                    waiting_for_shutdown_confirm = True
                    self._speaker.speak(f"Вы уверены, {self._profile.honorific}? Это выключит компьютер")
                elif response == "SLEEP_MODE":
                    sleeping = True
                    self._speaker.speak_loading()
                    self._main_win.log("Режим сна активирован")
                    self._main_win.set_home_status("Режим сна")
                else:
                    self._speaker.speak(response)
                    self._main_win.log(f"Ответ: {response}")

                self._main_win.set_status("Ожидаю обращение...")
                self._main_win.set_home_status("Системы в норме. Ожидаю голосовую команду...")

            except BaseException:
                log(f"Ошибка в основном цикле:\n{traceback.format_exc()}")

    def ensure_ollama(self):
        try:
            import requests
            requests.get("http://localhost:11434", timeout=2)
            print("[Ollama] Сервер уже запущен ✓")
        except Exception:
            print("[Ollama] Запускаю сервер...")
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            time.sleep(3)
            print("[Ollama] Сервер запущен ✓")

        threading.Thread(target=self._warmup_ollama, daemon=True).start()

    def _warmup_ollama(self):
        try:
            import requests
            print("[Ollama] Прогрев модели в фоне...")
            requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "mistral",
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                },
                timeout=180,
            )
            print("[Ollama] Модель готова ✓")
        except Exception as e:
            print(f"[Ollama] Прогрев не удался: {e}")

    def _on_exit(self):
        log("JARVIS exit")
        self._running = False
        if self._tray:
            self._tray.stop()
        if self._root:
            self._root.after(0, self._root.destroy)