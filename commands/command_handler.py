# commands/command_handler.py
import datetime

from commands.app_launcher import AppLauncher
from commands.volume_control import VolumeControl
from commands.web_handler import WebHandler
from config.profile_manager import ProfileManager
from commands.file_search import FileSearch
from commands.system_handler import SystemHandler

from commands import intents_web
from commands import intents_apps
from commands import intents_volume
from commands import intents_media
from commands import intents_system
from commands import intents_utils


class CommandContext:
    """
    Обёртка над зависимостями, чтобы удобнее передавать в intent-функции.
    """
    def __init__(self, speaker, file_search, system_handler,
                 app_launcher, web_handler, volume_control, profile):
        self.speaker = speaker
        self.file_search = file_search
        self.system_handler = system_handler
        self.app_launcher = app_launcher
        self.web_handler = web_handler
        self.volume_control = volume_control
        self.profile = profile

    def reply(self, text: str) -> str:
        return f"{text}, {self.profile.honorific}"


class Command:
    def __init__(self, text: str):
        self.text = text
        self.text_lower = text.lower().strip()
        self.created_at = datetime.datetime.now()


class CommandHandler:

    def __init__(self, speaker):
        self.file_search = FileSearch()
        self.system_handler = SystemHandler()

        self.app_launcher = AppLauncher(self.file_search)
        self.web_handler = WebHandler()
        self.volume_control = VolumeControl()
        self.profile = ProfileManager()
        self.speaker = speaker

        self.ctx = CommandContext(
            speaker=speaker,
            file_search=self.file_search,
            system_handler=self.system_handler,
            app_launcher=self.app_launcher,
            web_handler=self.web_handler,
            volume_control=self.volume_control,
            profile=self.profile,
        )

        self.command_map = [
            ("найди информацию по запросу", intents_web.handle_info_search),
            ("найди информацию",            intents_web.handle_info_search),
            ("хочу узнать",                  intents_web.handle_info_search),

            ("открой сайт", intents_web.handle_web),
            ("найди сайт", intents_web.handle_web),
            ("зайди на",   intents_web.handle_web),

            ("загугли", intents_web.handle_search),
            ("найди видео", intents_web.handle_video_search),
            ("найди",   intents_web.handle_search),
            ("поиск",   intents_web.handle_search),

            ("хочу посмотреть",   intents_web.handle_movie_search),
            ("давай посмотрим",   intents_web.handle_movie_search),
            ("посмотреть фильм",  intents_web.handle_movie_search),
            ("посмотреть сериал", intents_web.handle_movie_search),

            ("включи ютуб",   intents_web.handle_youtube),
            ("включи музыку", intents_web.handle_music),

            # Приложения и папки
            ("закрой папку",   intents_apps.handle_close_folder),
            ("закрыть папку",  intents_apps.handle_close_folder),
            ("открой папку",   intents_apps.handle_folder),
            ("папку",          intents_apps.handle_folder),
            ("папка",          intents_apps.handle_folder),

            ("открой",              intents_apps.handle_open),
            ("запусти",             intents_apps.handle_open),
            ("включи",              intents_apps.handle_open),
            ("выключи приложение",  intents_apps.handle_close),
            ("закрой",              intents_apps.handle_close),
            ("закрыть",             intents_apps.handle_close),

            # Звук
            ("выключи звук", intents_volume.handle_mute),
            ("включи звук",  intents_volume.handle_unmute),
            ("громкость",    intents_volume.handle_volume_set),
            ("громче",       intents_volume.handle_volume_up),
            ("тише",         intents_volume.handle_volume_down),

            # Медиа
            ("пауза",            intents_media.handle_media_pause),
            ("продолжи",         intents_media.handle_media_play),
            ("следующий трек",   intents_media.handle_media_next),
            ("следующая песня",  intents_media.handle_media_next),
            ("предыдущий трек",  intents_media.handle_media_prev),
            ("предыдущая песня", intents_media.handle_media_prev),

            # Система
            ("отдыхай",          intents_system.handle_sleep),
            ("спи",              intents_system.handle_sleep),
            ("выключись",        intents_system.handle_shutdown),
            ("завершить работу", intents_system.handle_shutdown),
            ("перезагрузи компьютер", intents_system.handle_restart_pc),
            ("перезагрузка",         intents_system.handle_restart_pc),
            ("заблокируй компьютер", intents_system.handle_lock_pc),
            ("блокировка",          intents_system.handle_lock_pc),
            ("диспетчер задач",     intents_system.handle_task_manager),
            ("проводник",           intents_system.handle_explorer),
            ("настройки",           intents_system.handle_windows_settings),
            ("панель управления",   intents_system.handle_control_panel),

            # Утилиты
            ("который час",        intents_utils.handle_time),
            ("сколько времени",    intents_utils.handle_time),
            ("какая дата",         intents_utils.handle_date),
            ("какой сегодня день", intents_utils.handle_date),
            ("открой калькулятор", intents_utils.handle_calc),
            ("калькулятор",        intents_utils.handle_calc),
            ("сделай скриншот",    intents_utils.handle_screenshot),
            ("скриншот",           intents_utils.handle_screenshot),
            ("открой загрузки",    intents_utils.handle_downloads),
            ("открой документы",   intents_utils.handle_documents),
            ("открой рабочий стол", intents_utils.handle_desktop),
            ("открой диск d",      intents_utils.handle_disk_d),
            ("открой диск e",      intents_utils.handle_disk_e),
        ]
        print("CommandHandler готов ✓")

    def handle(self, text: str) -> str:
        cmd = Command(text)

        if self.system_handler.execute(cmd.text_lower):
            return self.ctx.reply("Сделано")

        for keyword, func in self.command_map:
            if keyword in cmd.text_lower:
                return func(cmd, self.ctx)

        return self._handle_question(text)

    def _handle_question(self, text: str) -> str:
        print(f"\n[AI] Вопрос: '{text}'")
        return self.ctx.reply("AI модуль пока не подключён")