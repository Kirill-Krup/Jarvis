import datetime
import random
import re
import urllib.parse

from thefuzz import fuzz

from commands.app_launcher import AppLauncher
from commands.system.volume_control import VolumeControl
from commands.web.web_handler import KNOWN_SITES, WebHandler
from config.profile_manager import ProfileManager
from commands.file_search import FileSearch
from commands.system.system_handler import SystemHandler
from commands.ollama_handler import OllamaHandler
from core.browser import open_url
from core.honorific import soften

from commands.web import intents_web, intents_youtube
from commands import intents_apps, intents_media, reminders, small_talk
from commands.skills import find_skill
from commands.system import intents_system, intents_volume, intents_utils, intents_display, intents_scan, intents_connectivity
from commands import todo_handler
from commands.profanity_filter import check_profanity

from nlu.intent_service import IntentService
from nlu.router import IntentRouter
from nlu.fallback import FallbackPolicy
from nlu.speech_fix import fix_speech
from nlu import actions
from nlu.numbers import ru_numbers_to_digits

# Настройки разбора команды
SYSTEM_MAX_WORDS = 4     # SystemHandler (подстрока) только для коротких фраз
FUZZY_MAX_WORDS = 3      # нечёткое совпадение только для коротких фраз
FUZZY_MIN_SCORE = 85     # порог fuzz.ratio (0-100)
ACT_MIN_CONFIDENCE = 0.50   # выше: выполняем команду по намерению
CHAT_MIN_CONFIDENCE = 0.8  # выше: это разговор, ключевые слова не проверяем


CONTROL_REPLIES = {"SHUTDOWN", "CONFIRM_SHUTDOWN_PC", "SLEEP_MODE"}
LAUNCH_VERBS = ("открой", "запусти", "включи", "запускай", "вруби", "загрузи")
GREETINGS = {"привет", "здравствуй", "здравствуйте", "доброе утро", "добрый день",
             "добрый вечер", "хай", "салют"}
GREETING_REPLIES = [
    "Здравствуйте, {name}. Рад вас слышать.",
    "Привет, {name}! Чем займёмся?",
    "Добро пожаловать, {name}. Всё готово к работе.",
    "О, {name}! А я уже начал скучать по вашим командам.",
]


class CommandContext:
    def __init__(self, speaker, file_search, system_handler,
                 app_launcher, web_handler, volume_control, profile):
        self.speaker = speaker
        self.file_search = file_search
        self.system_handler = system_handler
        self.app_launcher = app_launcher
        self.web_handler = web_handler
        self.volume_control = volume_control
        self.profile = profile

    def speak(self, text: str) -> str:
        self.speaker.speak(text)
        return text

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
        self.app_launcher = AppLauncher(self.file_search, speaker=speaker)
        self.web_handler = WebHandler()
        self.volume_control = VolumeControl()
        self.profile = ProfileManager()
        self.speaker = speaker

        self.ollama = OllamaHandler()
        self.intent_service = IntentService()
        self.fallback = FallbackPolicy()
        self.last_was_chat = False   # последний ответ был разговором (продлеваем диалог)

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
        reminders.start_scheduler(speaker)

        self.command_map = [
            # Поиск / информация
            ("найди информацию по запросу", intents_web.handle_info_search),
            ("найди информацию", intents_web.handle_info_search),
            ("хочу узнать", intents_web.handle_info_search),

            # Веб & Мультимедиа
            ("открой сайт", intents_web.handle_web),
            ("найди сайт", intents_web.handle_web),
            ("зайди на", intents_web.handle_web),
            ("загугли", intents_web.handle_search),
            ("найди видео", intents_web.handle_video_search),
            ("найди", intents_web.handle_search),
            ("поиск", intents_web.handle_search),
            ("хочу посмотреть аниме", intents_web.handle_movie_search),
            ("посмотреть аниме", intents_web.handle_movie_search),
            ("хочу посмотреть", intents_web.handle_movie_search),
            ("давай посмотрим", intents_web.handle_movie_search),
            ("посмотреть фильм", intents_web.handle_movie_search),
            ("посмотреть сериал", intents_web.handle_movie_search),
            ("включи ютуб", intents_web.handle_youtube),
            ("включи музыку", intents_web.handle_music),
            ("поставь музыку", intents_web.handle_music),
            ("запусти музыку", intents_web.handle_music),

            # Погода
            ("какая завтра будет погода", intents_web.handle_weather),
            ("какая завтра погода", intents_web.handle_weather),
            ("какая будет погода", intents_web.handle_weather),
            ("какая погода", intents_web.handle_weather),
            ("прогноз погоды", intents_web.handle_weather),
            ("погода на завтра", intents_web.handle_weather),
            ("погода", intents_web.handle_weather),

            # To-Do list и напоминания
            ("добавь в список дел", todo_handler.handle_todo_add),
            ("добавь в список", todo_handler.handle_todo_add),
            ("добавь задачу", todo_handler.handle_todo_add),
            ("озвучь список дел", todo_handler.handle_todo_list),
            ("покажи список дел", todo_handler.handle_todo_list),
            ("список дел", todo_handler.handle_todo_list),
            ("очисти список дел", todo_handler.handle_todo_clear),
            ("напомни через", todo_handler.handle_todo_remind),
            ("напомни", todo_handler.handle_todo_remind),

            # Связь (Bluetooth, WiFi)
            ("включи блютуз", intents_connectivity.handle_bluetooth_on),
            ("включи bluetooth", intents_connectivity.handle_bluetooth_on),
            ("выключи блютуз", intents_connectivity.handle_bluetooth_off),
            ("отключи блютуз", intents_connectivity.handle_bluetooth_off),
            ("выключи bluetooth", intents_connectivity.handle_bluetooth_off),
            ("включи вай фай", intents_connectivity.handle_wifi_on),
            ("включи wifi", intents_connectivity.handle_wifi_on),
            ("выключи вай фай", intents_connectivity.handle_wifi_off),
            ("отключи вай фай", intents_connectivity.handle_wifi_off),
            ("выключи wifi", intents_connectivity.handle_wifi_off),
            ("включи точку доступа", intents_connectivity.handle_hotspot_on),
            ("режим в самолете", intents_connectivity.handle_airplane_on),
            ("режим в самолёте", intents_connectivity.handle_airplane_on),

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
            ("закрой папку", intents_apps.handle_close_folder),
            ("закрыть папку", intents_apps.handle_close_folder),
            ("открой папку", intents_apps.handle_folder),
            ("папку", intents_apps.handle_folder),
            ("папка", intents_apps.handle_folder),
            ("выключи приложение", intents_apps.handle_close),
            ("закрой программу", intents_apps.handle_close),
            ("закрой приложение", intents_apps.handle_close),
            ("закрой", intents_apps.handle_close),
            ("закрыть", intents_apps.handle_close),
            ("открой программу", intents_apps.handle_open),
            ("открой приложение", intents_apps.handle_open),
            ("открой", intents_apps.handle_open),
            ("запусти", intents_apps.handle_open),
            ("включи", intents_apps.handle_open),

            # Звук
            ("выключи звук", intents_volume.handle_mute),
            ("включи звук", intents_volume.handle_unmute),
            ("громкость на", intents_volume.handle_volume_set),
            ("громкость", intents_volume.handle_volume_set),
            ("звук на", intents_volume.handle_volume_set),
            ("звук", intents_volume.handle_volume_set),
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
            ("пауза", intents_media.handle_media_pause),
            ("продолжи", intents_media.handle_media_play),
            ("следующий трек", intents_media.handle_media_next),
            ("следующая песня", intents_media.handle_media_next),
            ("предыдущий трек", intents_media.handle_media_prev),
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

        # Длинные ключи первыми
        self._sorted_map = sorted(
            self.command_map, key=lambda item: len(item[0]), reverse=True)

        print("CommandHandler готов [OK]")

    # ------------------------------------------------------------ разбор команды

    def handle(self, text: str, alternatives=()) -> str:
        """Выполняет команду и возвращает ответ. Обращение («сэр») оставляется
        в ответе лишь иногда. alternatives — запасные варианты фразы от
        распознавателя речи."""
        reply = self._dispatch(text, alternatives)
        return reply if reply in CONTROL_REPLIES else soften(reply)

    def _dispatch(self, text: str, alternatives=()) -> str:
        """Разбор команды: маты -> навыки -> мультикоманды -> намерение -> ключевые слова."""
        self.last_was_chat = False

        profanity_reply = check_profanity(text)
        if profanity_reply:
            return self.ctx.reply(profanity_reply)

        # Навыки с однозначной формулировкой («включи песню А и Б», «выбери между…»)
        # разбирают фразу целиком, чтобы не разрезать её по союзу «и»
        phrase = self._clean(ru_numbers_to_digits(text.lower()))
        found = find_skill(self._fix(phrase, alternatives))
        if found and found.exclusive:
            reply = self._run_skill(found, self._fix(phrase, alternatives))
            if reply is not None:
                return reply

        sub_commands = self._split_multi_command(text)
        if sub_commands and len(sub_commands) > 1:
            print(f"[MULTI] Обнаружено несколько команд: {sub_commands}")
            replies = [r for r in (self._handle_single(c) for c in sub_commands) if r]
            if replies:
                return ". ".join(replies)

        return self._handle_single(text, alternatives)

    def _fix(self, clean_text: str, alternatives=()) -> str:
        """Исправляет названия программ, которые распознаватель услышал неверно."""
        return fix_speech(clean_text, [self._clean(a.lower()) for a in alternatives],
                          self.app_launcher.known_names())

    def _run_skill(self, found, clean_text: str):
        try:
            return found.handler(Command(clean_text), self.ctx)
        except Exception as e:
            print(f"[SKILL] Ошибка навыка {found.name}: {e}")
            return self.ctx.reply("Не получилось выполнить команду")

    def _split_multi_command(self, text: str) -> list[str] | None:
        """Разбивает фразу типа 'открой ютуб и телеграм' или 'включи музыку и закрой стим'."""
        text_lower = text.lower().strip()

        # Исключаем поисковые запросы, которые часто содержат "и"
        search_starts = ("найди", "поищи", "загугли", "что такое", "кто такой", "переведи", "почему", "сколько", "как", "хочу узнать")
        if any(text_lower.startswith(s) for s in search_starts):
            return None

        # Разделители команд
        delimiters = [" а также ", " затем ", " потом ", " и "]
        chosen_delim = None
        for d in delimiters:
            if d in text_lower:
                chosen_delim = d
                break

        if not chosen_delim:
            return None

        parts = [p.strip() for p in text_lower.split(chosen_delim) if p.strip()]
        if len(parts) < 2:
            return None

        # Проверяем, нужно ли унаследовать глагол действия из первой части
        # Например: "открой ютуб и телеграм" -> part 0 = "открой ютуб", part 1 = "телеграм" -> "открой телеграм"
        # "закрой стим и дискорд" -> "закрой стим", "закрой дискорд"
        verbs = [
            "открой", "запусти", "включи", "закрой", "закрыть", "выключи",
            "покажи", "сделай", "поставь", "увеличь", "уменьши", "найди"
        ]
        first_verb = None
        for v in verbs:
            if parts[0].startswith(v + " "):
                first_verb = v
                break

        final_commands = []
        for i, part in enumerate(parts):
            if i > 0 and first_verb:
                # Если часть не начинается ни с одного глагола действия, наследуем
                if not any(part.startswith(v + " ") for v in verbs):
                    part = f"{first_verb} {part}"
            final_commands.append(part)

        return final_commands

    def _handle_single(self, text: str, alternatives=()) -> str:
        """Обработка одной атомарной команды."""
        text_with_digits = ru_numbers_to_digits(text)
        clean_text = self._fix(self._clean(text_with_digits.lower()), alternatives)
        cmd = Command(clean_text)

        # Навыки: музыка, проекты, напоминания, случайности и т.д.
        found = find_skill(clean_text)
        if found:
            reply = self._run_skill(found, clean_text)
            if reply is not None:
                return reply

        # «открой ютуб / гитхаб / почту…» — сайты из списка известных
        site = re.match(r"^(?:открой|включи|запусти|зайди на|зайди в)\s+(.+)$", clean_text)
        if site and site.group(1) in KNOWN_SITES:
            return self.ctx.reply(f"Открываю {site.group(1)}") if open_url(KNOWN_SITES[site.group(1)]) is None else None

        # Приветствия и короткие реплики вежливости — без поиска и классификатора
        if clean_text in GREETINGS:
            return self.ctx.reply(random.choice(GREETING_REPLIES).format(name=self.profile.name))
        talk = small_talk.reply(clean_text) if len(clean_text.split()) <= 3 else None
        if talk:
            return self.ctx.reply(talk)

        # Команды управления громкостью («звук 10», «звук десять», «звук на 50», «громкость 30»)
        if clean_text.startswith("звук") or clean_text.startswith("громкость"):
            if any(w in clean_text for w in ("максимум", "минимум", "полную", "всю", "сто", "ноль")) or re.search(r'\d+', clean_text):
                return intents_volume.handle_volume_set(cmd, self.ctx)

        # Обработка команд закрытия / выключения (чтобы исключить ложное открытие приложений)
        close_verbs = ("закрой", "закрыть", "выключи", "выруби", "отруби", "заверши", "завершить", "останови", "убей", "убери", "погаси", "потуши")
        if any(clean_text.startswith(v + " ") or clean_text == v for v in close_verbs):
            if any(w in clean_text for w in ("музыку", "музыка", "песню", "песня", "трек", "плеер", "звуки", "воспроизведение")):
                return intents_media.handle_media_pause(cmd, self.ctx)
            if "звук" in clean_text:
                return intents_volume.handle_mute(cmd, self.ctx)
            return intents_apps.handle_close(cmd, self.ctx)

        # Сказано только название программы («телега», «стим», «дискорд»)
        apps = self.app_launcher.memory.get("apps", {})
        stem = clean_text[:-1] + "а" if clean_text.endswith("у") and len(clean_text) > 2 else None
        if clean_text in apps or (stem and stem in apps):
            return self.app_launcher.launch(clean_text, self.profile.honorific)

        # Глагол запуска + название программы где-то в фразе
        words = clean_text.split()
        if any(v in words for v in LAUNCH_VERBS):
            for name in sorted(apps, key=len, reverse=True):
                if len(name) >= 3 and f" {name} " in f" {clean_text} ":
                    return self.app_launcher.launch(name, self.profile.honorific)

        # Классификатор намерений (NLU)
        result = self.intent_service.classify(cmd.text)
        print(f"[NLU] intent={result.intent}  target={result.target_en}  "
              f"query={result.params.get('query') or result.target_ru}  "
              f"conf={result.confidence:.2f}")

        blocked_dangerous = False

        if result.intent != "chat" and result.confidence >= ACT_MIN_CONFIDENCE:
            if (self.fallback.is_dangerous(result)
                    and (result.target_en or "") != "sleep"):
                blocked_dangerous = True
            else:
                reply = self._execute_intent(cmd, result)
                if reply is not None:
                    return reply

        elif result.intent == "chat" and result.confidence >= CHAT_MIN_CONFIDENCE:
            return self._chat(cmd, result)

        # Запасной путь по ключевым словам
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

                # Защита: если классификатор определил web:music, но команда про выключение/закрытие музыки
                if label == "web:music" and any(v in cmd.text_lower for v in ("закрой", "закрыть", "выключи", "выруби", "останови", "хватит", "стоп")):
                    return intents_media.handle_media_pause(cmd, self.ctx)

                question = actions.clarification(label, query)
                if question:
                    return self.ctx.reply(question)

                handler, canonical = actions.resolve(label, query)
                print(f"[NLU] действие {label} -> «{canonical}»")
                return handler(Command(canonical), self.ctx)

            if result.intent == "system":
                cmd = Command(ru_numbers_to_digits(cmd.text))

            return self.router.route(cmd, result)
        except Exception as e:
            print(f"[NLU] ошибка выполнения {result.intent}/{result.target_en}: {e}")
            return self.ctx.reply("Не получилось выполнить команду")

    def _chat(self, cmd, result) -> str:
        """Разговор: языковая модель, а без неё — живые заготовки."""
        search_words = ("загугли", "прогугли", "погугли", "поищи", "найди в интернете",
                        "найди в сети", "поиск в гугле", "что такое", "кто такой")
        if any(w in cmd.text_lower for w in search_words):
            query = cmd.text_lower
            for w in search_words:
                query = query.replace(w, "")
            query = self._clean(query)
            open_url(f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}")
            return self.ctx.reply(f"Ищу информацию по запросу «{query}» в браузере")

        self.last_was_chat = True
        if result.chat_reply:
            return result.chat_reply
        if self.ollama.is_available():
            reply = self.ollama.chat(cmd.text)
            if reply:
                return reply
        return small_talk.reply(cmd.text_lower) or small_talk.fallback()

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

        # 3. Нечёткое совпадение
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
            print(f"[FuzzyMatch] '{match_text}' -> score={best_score}")
            return best_func
        return None
