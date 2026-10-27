import os
import webbrowser

from commands import intents_media
from commands.system import intents_system, intents_volume, intents_utils, intents_display


class IntentRouter:
    def __init__(self, ctx):
        self.ctx = ctx

    def route(self, cmd, result):
        intent = result.intent

        if intent == "open_website":
            return self._open_website(cmd, result)
        if intent == "open_app":
            return self._open_app(cmd, result)
        if intent == "open_folder":
            return self._open_folder(cmd, result)
        if intent == "media":
            return self._media(cmd, result)
        if intent == "system":
            return self._system(cmd, result)
        if intent == "chat":
            return result.chat_reply

        return None

    def _open_website(self, cmd, result):
        if result.url:
            webbrowser.open(result.url)
            name = result.target_ru or result.target_en or "сайт"
            return self.ctx.reply(f"Открываю {name}")

        query = result.target_en or result.target_ru or cmd.text
        return self.ctx.web_handler.open_site(query, self.ctx.profile.honorific)

    def _open_app(self, cmd, result):
        honorific = self.ctx.profile.honorific

        candidates = []
        if hasattr(result, "candidates") and result.candidates:
            candidates.extend(result.candidates)

        for name in [result.target_en, result.target_ru]:
            if name and name not in candidates:
                candidates.append(name)

        for name in candidates:
            launch_result = self.ctx.app_launcher.launch(name, honorific)
            if launch_result and "не удалось найти" not in launch_result.lower():
                return launch_result

        for name in candidates:
            fallback = self.ctx.web_handler.open_web_fallback(name, honorific)
            if fallback:
                return fallback

        target_display = result.target_ru or result.target_en or "приложение"
        return self.ctx.reply(f"Не удалось найти {target_display}")

    def _open_folder(self, cmd, result):
        folder_candidates = []

        if hasattr(result, "candidates") and result.candidates:
            folder_candidates.extend(result.candidates)

        for name in [result.target_en, result.target_ru]:
            if name and name not in folder_candidates:
                folder_candidates.append(name)

        for folder_name in folder_candidates:
            path = self.ctx.file_search.find_folder(folder_name)
            if path:
                os.startfile(path)
                return self.ctx.reply(f"Открываю папку {result.target_ru or folder_name}")

        folder_name = result.target_ru or result.target_en or "папка"
        return self.ctx.reply(f"Папка {folder_name} не найдена")

    def _media(self, cmd, result):
        media_map = {
            "pause": intents_media.handle_media_pause,
            "play": intents_media.handle_media_play,
            "next": intents_media.handle_media_next,
            "previous": intents_media.handle_media_prev,
        }

        fn = media_map.get(result.target_en or "")
        if fn:
            return fn(cmd, self.ctx)

        return self.ctx.reply("Не понял команду управления медиа")

    def _system(self, cmd, result):
        target = result.target_en or result.target_ru or ""

        if self.ctx.system_handler.execute(target):
            return self.ctx.reply("Сделано")

        system_map = {
            "volume_up": intents_volume.handle_volume_up,
            "volume_down": intents_volume.handle_volume_down,
            "mute": intents_volume.handle_mute,
            "unmute": intents_volume.handle_unmute,
            "brightness_up": intents_display.handle_brightness_up,
            "brightness_down": intents_display.handle_brightness_down,
            "brightness_set": intents_display.handle_brightness_set,
            "brightness_monitor_1": intents_display.handle_brightness_monitor,
            "brightness_monitor_2": intents_display.handle_brightness_monitor,
            "brightness_monitor_3": intents_display.handle_brightness_monitor,
            "screenshot": intents_utils.handle_screenshot,
            "lock": intents_system.handle_lock_pc,
            # "restart": intents_system.handle_restart_pc,
            # "shutdown": intents_system.handle_shutdown,
            "sleep": intents_system.handle_sleep,
            "task_manager": intents_system.handle_task_manager,
            "explorer": intents_system.handle_explorer,
            "settings": intents_system.handle_windows_settings,
            "control_panel": intents_system.handle_control_panel,
            "calculator": intents_utils.handle_calc,
            "display_extend": intents_display.handle_display_extend,
            "display_duplicate": intents_display.handle_display_duplicate,
            "display_primary": intents_display.handle_display_primary,
            "display_second": intents_display.handle_display_second,
            "display_info": intents_display.handle_display_info,
        }

        fn = system_map.get(result.target_en or "")
        if fn:
            return fn(cmd, self.ctx)

        return self.ctx.reply(f"Не знаю как выполнить: {result.target_ru or target}")