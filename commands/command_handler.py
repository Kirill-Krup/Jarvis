import datetime
import re

from thefuzz import fuzz

from commands.app_launcher    import AppLauncher
from commands.system.volume_control import VolumeControl
from commands.web.web_handler import WebHandler
from config.profile_manager   import ProfileManager
from commands.file_search     import FileSearch
from commands.system.system_handler import SystemHandler
from commands.ollama_handler  import OllamaHandler

from commands.web import intents_web, intents_youtube
from commands import intents_apps
from commands import intents_media
from commands.system import intents_system, intents_volume, intents_utils, intents_display, intents_scan

from nlu.intent_service import IntentService
from nlu.router import IntentRouter
from nlu.fallback import FallbackPolicy
from nlu import actions
from nlu.numbers import ru_numbers_to_digits

# Настройки разбора команды
SYSTEM_MAX_WORDS = 4     # SystemHandler (подстрока) только для коротких фраз
FUZZY_MAX_WORDS = 3      # нечёткое совпадение только для коротких фраз
FUZZY_MIN_SCORE = 85     # порог fuzz.ratio (0-100)
ACT_MIN_CONFIDENCE = 0.6   # выше: выполняем команду по намерению
CHAT_MIN_CONFIDENCE = 0.8  # выше: это разговор, ключевые слова не проверяем

class CommandContext:
    def __init__(self, speaker, file_search, system_handler,
                 app_launcher, web_handler, volume_control, profile):
        self.speaker        = speaker
        self.file_search    = file_search
        self.system_handler = system_handler
        self.app_launcher   = app_launcher
        self.web_handler    = web_handler
        self.volume_control = volume_control
        self.profile        = profile

    def speak(self, text: str) -> str:
        self.speaker.speak(text)
        return text

    def reply(self, text: str) -> str:
        return f"{text}, {self.profile.honorific}"


class Command:
    def __init__(self, text: str):
        self.text       = text
        self.text_lower = text.lower().strip()
        self.created_at = datetime.datetime.now()


class CommandHandler:

    def __init__(self, speaker):
        self.file_search    = FileSearch()
        self.system_handler = SystemHandler()
        self.app_launcher   = AppLauncher(self.file_search)
        self.web_handler    = WebHandler()
        self.volume_control = VolumeControl()
        self.profile        = ProfileManager()
        self.speaker        = speaker

        self.ollama = OllamaHandler()
        self.intent_service = IntentService(self.ollama)
        self.fallback = FallbackPolicy()

        self.ctx = CommandContext(
            speaker=speaker,
            file_search=self.file_search,
            system_handler=self.system_handler,
            app_launcher=self.app_launcher,
            web_handler=self.web_handler,
            volume_control=self.volume_control,
            profile=self.profile,
        )
        self.router = IntentRouter(self.ctx)

        self.command_map = [
            # Поиск / информация
            ("найди информацию по запросу", intents_web.handle_info_search),
            ("найди информацию", intents_web.handle_info_search),
            ("хочу узнать", intents_web.handle_info_search),

            # Веб
            ("открой сайт", intents_web.handle_web),
            ("найди сайт", intents_web.handle_web),
            ("зайди на", intents_web.handle_web),
            ("загугли", intents_web.handle_search),
            ("найди видео", intents_web.handle_video_search),
            ("найди", intents_web.handle_search),
            ("поиск", intents_web.handle_search),
            ("хочу посмотреть", intents_web.handle_movie_search),
            ("давай посмотрим", intents_web.handle_movie_search),
            ("посмотреть фильм", intents_web.handle_movie_search),
            ("посмотреть сериал", intents_web.handle_movie_search),
            ("включи ютуб", intents_web.handle_youtube),
            ("включи музыку", intents_web.handle_music),

            # Сканирование
            ("быстрая проверка", intents_scan.handle_scan_quick),
            ("быстрое сканирование", intents_scan.handle_scan_quick),
            ("быструю проверку", intents_scan.handle_scan_quick),
            ("полная проверка", intents_scan.handle_scan_full),
            ("полное сканирование", intents_scan.handle_scan_full),
            ("полную проверку", intents_scan.handle_scan_full),
            ("просканируй диск", intents_scan.handle_scan_disk),
            ("сканируй диск", intents_scan.handle_scan_disk),
            ("проверь диск", intents_scan.handle_scan_disk),
            ("просканируй папку", intents_scan.handle_scan_folder),
            ("проверь папку", intents_scan.handle_scan_folder),
            ("останови сканирование", intents_scan.handle_scan_cancel),
            ("отмени сканирование", intents_scan.handle_scan_cancel),
            ("остановить сканирование", intents_scan.handle_scan_cancel),
            ("отменить сканирование", intents_scan.handle_scan_cancel),

            # Приложения и папки
            ("закрой папку",  intents_apps.handle_close_folder),
            ("закрыть папку", intents_apps.handle_close_folder),
            ("открой папку",  intents_apps.handle_folder),
            ("папку",         intents_apps.handle_folder),
            ("папка",         intents_apps.handle_folder),
            ("открой",             intents_apps.handle_open),
            ("запусти",            intents_apps.handle_open),
            ("включи",             intents_apps.handle_open),
            ("выключи приложение", intents_apps.handle_close),
            ("закрой",             intents_apps.handle_close),
            ("закрыть",            intents_apps.handle_close),

            # Звук
            ("выключи звук", intents_volume.handle_mute),
            ("включи звук", intents_volume.handle_unmute),
            ("громкость", intents_volume.handle_volume_set),
            ("громче", intents_volume.handle_volume_up),
            ("тише", intents_volume.handle_volume_down),

            # YouTube управление
            ("открой канал", intents_youtube.handle_open_channel),
            ("перейди на канал", intents_youtube.handle_open_channel),
            ("найди на ютубе", intents_youtube.handle_youtube_search),
            ("поищи на ютубе", intents_youtube.handle_youtube_search),
            ("полный экран", intents_youtube.handle_youtube_fullscreen),
            ("перемотай вперёд", intents_youtube.handle_youtube_forward),
            ("перемотай назад", intents_youtube.handle_youtube_backward),
            ("перемотка вперёд", intents_youtube.handle_youtube_forward),
            ("перемотка назад", intents_youtube.handle_youtube_backward),

            # Медиа
            ("пауза",            intents_media.handle_media_pause),
            ("продолжи",         intents_media.handle_media_play),
            ("следующий трек",   intents_media.handle_media_next),
            ("следующая песня",  intents_media.handle_media_next),
            ("предыдущий трек",  intents_media.handle_media_prev),
            ("предыдущая песня", intents_media.handle_media_prev),

            # Система
            ("отдыхай", intents_system.handle_sleep),
            ("спи", intents_system.handle_sleep),
            ("выключись", intents_system.handle_shutdown),
            ("завершить работу", intents_system.handle_shutdown),
            ("перезагрузи компьютер", intents_system.handle_restart_pc),
            ("перезагрузка", intents_system.handle_restart_pc),
            ("заблокируй компьютер", intents_system.handle_lock_pc),
            ("блокировка", intents_system.handle_lock_pc),
            ("диспетчер задач", intents_system.handle_task_manager),
            ("проводник", intents_system.handle_explorer),
            ("настройки", intents_system.handle_windows_settings),
            ("панель управления", intents_system.handle_control_panel),

            # Утилиты
            ("который час", intents_utils.handle_time),
            ("сколько времени", intents_utils.handle_time),
            ("какая дата", intents_utils.handle_date),
            ("какой сегодня день", intents_utils.handle_date),
            ("открой калькулятор", intents_utils.handle_calc),
            ("калькулятор", intents_utils.handle_calc),
            ("сделай скриншот", intents_utils.handle_screenshot),
            ("скриншот", intents_utils.handle_screenshot),
            ("открой загрузки", intents_utils.handle_downloads),
            ("открой документы", intents_utils.handle_documents),
            ("открой рабочий стол", intents_utils.handle_desktop),
            ("открой диск d", intents_utils.handle_disk_d),
            ("открой диск e", intents_utils.handle_disk_e),

            # Дисплей
            ("расширить экраны", intents_display.handle_display_extend),
            ("расширь экраны", intents_display.handle_display_extend),
            ("расширить мониторы", intents_display.handle_display_extend),
            ("дублировать экраны", intents_display.handle_display_duplicate),
            ("повторять экраны", intents_display.handle_display_duplicate),
            ("дублируй экраны", intents_display.handle_display_duplicate),
            ("только первый экран", intents_display.handle_display_primary),
            ("первый экран", intents_display.handle_display_primary),
            ("только второй экран", intents_display.handle_display_second),
            ("второй экран", intents_display.handle_display_second),
            ("сколько мониторов", intents_display.handle_display_info),
            ("какие мониторы", intents_display.handle_display_info),
            ("яркость первого", intents_display.handle_brightness_monitor),
            ("яркость второго", intents_display.handle_brightness_monitor),
            ("яркость третьего", intents_display.handle_brightness_monitor),
            ("увеличь яркость", intents_display.handle_brightness_up),
            ("уменьши яркость", intents_display.handle_brightness_down),
            ("ярче", intents_display.handle_brightness_up),
            ("темнее", intents_display.handle_brightness_down),
            ("яркость", intents_display.handle_brightness_set),
        ]

        # Длинные (более конкретные) ключи проверяем первыми:
        # "включи звук" должно сработать раньше, чем "включи".
        self._sorted_map = sorted(
            self.command_map, key=lambda item: len(item[0]), reverse=True)

        print("CommandHandler готов ✓")

    # ------------------------------------------------------------ разбор команды

    def handle(self, text: str) -> str:
        """Сначала понимаем намерение (классификатор), ключевые слова — запасной путь."""
        cmd = Command(text)
        result = self.intent_service.classify(cmd.text)
        print(f"[NLU] intent={result.intent}  target={result.target_en}  "
              f"query={result.params.get('query') or result.target_ru}  "
              f"conf={result.confidence:.2f}")

        blocked_dangerous = False

        if result.intent != "chat" and result.confidence >= ACT_MIN_CONFIDENCE:
            # выключение и перезагрузку по догадке модели не выполняем
            if (self.fallback.is_dangerous(result)
                    and (result.target_en or "") != "sleep"):
                blocked_dangerous = True
            else:
                reply = self._execute_intent(cmd, result)
                if reply is not None:
                    return reply

        elif result.intent == "chat" and result.confidence >= CHAT_MIN_CONFIDENCE:
            return self._chat(cmd, result)

        # Классификатор не уверен: пробуем прежний разбор по ключевым словам
        reply = self._handle_by_keywords(cmd)
        if reply is not None:
            return reply

        if blocked_dangerous:
            return self.ctx.reply(
                "Для этого скажите команду прямо: "
                "«завершить работу» или «перезагрузи компьютер»")

        return self._chat(cmd, result)

    def _execute_intent(self, cmd, result):
        """Выполняет распознанное намерение. None — если выполнить нечем."""
        try:
            if result.intent == "action":
                label = result.target_en
                query = result.params.get("query", "")

                question = actions.clarification(label, query)
                if question:
                    return self.ctx.reply(question)

                handler, canonical = actions.resolve(label, query)
                print(f"[NLU] действие {label} -> «{canonical}»")
                return handler(Command(canonical), self.ctx)

            if result.intent == "system":
                # Vosk выдаёт числа словами: «громкость пятьдесят» -> «громкость 50»
                cmd = Command(ru_numbers_to_digits(cmd.text))

            return self.router.route(cmd, result)
        except Exception as e:
            print(f"[NLU] ошибка выполнения {result.intent}/{result.target_en}: {e}")
            return self.ctx.reply("Не получилось выполнить команду")

    def _chat(self, cmd, result) -> str:
        return result.chat_reply or self.ollama.chat(cmd.text)

    # --------------------------------------------- запасной разбор по ключевым словам

    def _handle_by_keywords(self, cmd):
        match_text = self._clean(cmd.text_lower)
        word_count = len(match_text.split())

        # 1. Быстрые системные команды (только для коротких фраз)
        if word_count <= SYSTEM_MAX_WORDS and self.system_handler.execute(match_text):
            return self.ctx.reply("Сделано")

        # 2. Точное совпадение по словам
        func = self._match_static(match_text)
        if func:
            return func(cmd, self.ctx)

        # 3. Нечёткое совпадение (опечатки распознавания), только короткие фразы
        if word_count <= FUZZY_MAX_WORDS:
            func = self._match_fuzzy(match_text)
            if func:
                return func(cmd, self.ctx)

        return None

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"[^\w\s]", " ", text)
        return " ".join(text.split())

    def _match_static(self, match_text: str):
        for keyword, func in self._sorted_map:
            # границы слов: "спи" не должно срабатывать на "расписание"
            if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", match_text):
                return func
        return None

    def _match_fuzzy(self, match_text: str):
        best_score, best_func = 0, None
        for keyword, func in self.command_map:
            score = fuzz.ratio(keyword, match_text)
            if score > best_score:
                best_score, best_func = score, func

        if best_score >= FUZZY_MIN_SCORE:
            print(f"[FuzzyMatch] '{match_text}' → score={best_score}")
            return best_func
        return None