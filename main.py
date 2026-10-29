import time
import os
import sys
import datetime
import traceback

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config.setup_wizard import is_first_run, run_setup
from core.speakers.speaker import Speaker
from core.listener import Listener
from commands.command_handler import CommandHandler
from config.profile_manager import ProfileManager
from config.settings import WAKE_WORD


def get_farewell() -> str:
    hour = datetime.datetime.now().hour
    if 6 <= hour < 11:
        return "Доброго утра"
    elif 11 <= hour < 18:
        return "Хорошего дня"
    elif 18 <= hour < 23:
        return "Хорошего вечера"
    else:
        return "Доброй ночи"


def main():
    print("=" * 40)
    print("  Запуск системы JARVIS")
    print("=" * 40)

    if is_first_run():
        run_setup()

    profile = ProfileManager()
    speaker = Speaker()
    listener = Listener()
    commands = CommandHandler(speaker)

    greeting = (
        f"Все системы в норме. "
        f"Добро пожаловать, {profile.name}. "
        f"Чем могу помочь, {profile.honorific}?"
    )
    speaker.speak(greeting)

    sleeping = False
    waiting_for_shutdown_confirm = False

    print("\nГоворите 'Джарвис' чтобы активировать")
    print("Ctrl+C для выхода\n")

    while True:
        try:
            if sleeping:
                print("[SLEEP] Режим сна... (скажите 'Джарвис, проснись')")
                time.sleep(3)
                text = listener.listen()
                if text and WAKE_WORD in text and "проснись" in text:
                    sleeping = False
                    speaker.speak(f"Снова на связи, {profile.honorific}")
                continue

            if waiting_for_shutdown_confirm:
                print("Жду подтверждения...")
                confirm_text = listener.listen()
                if confirm_text and "да" in confirm_text:
                    farewell = get_farewell()
                    speaker.speak(
                        f"{farewell}, {profile.honorific}. "
                        f"Выключаю компьютер"
                    )
                    time.sleep(3)
                    os.system("shutdown /s /t 0")
                    break
                else:
                    waiting_for_shutdown_confirm = False
                    speaker.speak(f"Отменено, {profile.honorific}")
                continue

            trigger_data = listener.listen_wake_and_command()
            if not trigger_data:
                continue

            trigger, command_text, raw_text = trigger_data
            print(f"[VOICE] Слышал: '{raw_text}' -> Команда: '{command_text}'")

            if trigger == "wakeup":
                sleeping = False
                speaker.speak(f"Снова на связи, {profile.honorific}")
                continue

            print("Активирован!")

            if not command_text:
                speaker.speak(f"Слушаю, {profile.honorific}")
                command_text = listener.listen()

            if not command_text:
                speaker.speak(f"Не расслышал, {profile.honorific}")
                continue

            response = commands.handle(command_text)

            if response == "SHUTDOWN":
                farewell = get_farewell()
                speaker.speak(f"{farewell}, {profile.honorific}")
                break

            elif response == "CONFIRM_SHUTDOWN_PC":
                waiting_for_shutdown_confirm = True
                speaker.speak(
                    f"Вы уверены, {profile.honorific}? "
                    f"Это выключит компьютер"
                )

            elif response == "SLEEP_MODE":
                sleeping = True
                speaker.speak(
                    f"Ухожу в режим сна, {profile.honorific}. "
                    f"Скажите 'Джарвис, проснись' когда понадоблюсь"
                )

            else:
                speaker.speak(response)

        except KeyboardInterrupt:
            farewell = get_farewell()
            speaker.speak(f"{farewell}, {profile.honorific}")
            break

        except Exception as e:
            print(f"Ошибка: {e}")
            continue


if __name__ == "__main__":
    if "--gui" in sys.argv:
        from app.jarvis_app import JarvisApp
        from core.logging_utils import log
        try:
            JarvisApp().start()
        except SystemExit as e:
            log(f"SystemExit: code={e.code}")
        except BaseException:
            log(f"Критическая ошибка:\n{traceback.format_exc()}")
            sys.exit(1)
    else:
        main()
