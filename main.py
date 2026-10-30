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


CONTEXT_TIMEOUT_SEC = 5.0  # Джарвис ждет продолжения диалога ровно 5 секунд без wake-word


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
    in_context = False

    print("\nГоворите 'Джарвис' чтобы активировать")
    print("Ctrl+C для выхода\n")

    while True:
        try:
            if sleeping:
                print("[SLEEP] Режим сна... (скажите 'Джарвис, проснись')")
                time.sleep(3)
                text = listener.listen(timeout_sec=4.0)
                if text and WAKE_WORD in text and "проснись" in text:
                    sleeping = False
                    speaker.speak(f"Снова на связи, {profile.honorific}")
                continue

            if waiting_for_shutdown_confirm:
                print("Жду подтверждения...")
                confirm_text = listener.listen(timeout_sec=6.0)
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

            # Контекстный режим: слушаем строго 5 секунд без wake word
            if in_context:
                print("[CONTEXT] Слушаю продолжение разговора (5 сек)...")
                command_text = listener.listen(timeout_sec=CONTEXT_TIMEOUT_SEC)
                if not command_text:
                    in_context = False
                    print("[CONTEXT] Время контекста (5 сек) истекло, ожидаю 'Джарвис'")
                    continue

                if WAKE_WORD in command_text.lower():
                    command_text = command_text.lower().replace(WAKE_WORD, "").strip()

                if len(command_text.strip()) < 2:
                    in_context = False
                    continue

            else:
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
                    command_text = listener.listen(timeout_sec=5.0)

                if not command_text:
                    speaker.speak(f"Не расслышал, {profile.honorific}")
                    in_context = False
                    continue

            response = commands.handle(command_text)

            if response == "SHUTDOWN":
                farewell = get_farewell()
                speaker.speak(f"{farewell}, {profile.honorific}")
                break

            elif response == "CONFIRM_SHUTDOWN_PC":
                waiting_for_shutdown_confirm = True
                in_context = False
                speaker.speak(
                    f"Вы уверены, {profile.honorific}? "
                    f"Это выключит компьютер"
                )

            elif response == "SLEEP_MODE":
                sleeping = True
                in_context = False
                speaker.speak(
                    f"Ухожу в режим сна, {profile.honorific}. "
                    f"Скажите 'Джарвис, проснись' когда понадоблюсь"
                )

            else:
                speaker.speak(response)
                # Продлеваем контекстный режим на следующие 5 секунд
                in_context = True

        except KeyboardInterrupt:
            farewell = get_farewell()
            speaker.speak(f"{farewell}, {profile.honorific}")
            break

        except Exception as e:
            print(f"Ошибка: {e}")
            in_context = False
            continue


if __name__ == "__main__":
    if "--no-gui" in sys.argv:
        main()
    else:
        from app.jarvis_app import JarvisApp
        from core.logging_utils import log
        try:
            JarvisApp().start()
        except SystemExit as e:
            log(f"SystemExit: code={e.code}")
        except BaseException:
            log(f"Критическая ошибка:\n{traceback.format_exc()}")
            sys.exit(1)
