import sys
import traceback

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def run_console():
    """Консольный режим (без окна): python main.py --no-gui"""
    from commands.command_handler import CommandHandler
    from config.profile_manager import ProfileManager
    from config.setup_wizard import is_first_run, run_setup
    from core.listener import Listener
    from core.speakers.speaker import Speaker
    from core.voice_loop import VoiceLoop

    print("=" * 40)
    print("  Запуск системы JARVIS")
    print("=" * 40)
    if is_first_run():
        run_setup()

    profile = ProfileManager()
    speaker = Speaker()
    listener = Listener()
    commands = CommandHandler(speaker)

    speaker.speak_greeting()
    print("\nГоворите 'Джарвис' чтобы активировать. Ctrl+C для выхода\n")
    VoiceLoop(speaker, listener, commands, profile).run()


if __name__ == "__main__":
    if "--no-gui" in sys.argv:
        run_console()
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
