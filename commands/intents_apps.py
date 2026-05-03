import os


def _extract_folder_name(text: str) -> str:
    return (
        text.lower()
        .replace("открой папку", "")
        .replace("закрой папку", "")
        .replace("закрыть папку", "")
        .replace("папку", "")
        .replace("папка", "")
        .replace("пожалуйста", "")
        .strip()
    )


def handle_open(cmd, ctx):
    from commands.web.web_handler import KNOWN_SITES, APP_WEB_FALLBACK

    text = cmd.text_lower
    app_name = (
        text.replace("открой", "")
            .replace("запусти", "")
            .replace("включи", "")
            .strip()
    )

    if not app_name:
        return ctx.reply("Что именно открыть?")

    if app_name in ["браузер", "интернет", "сеть"]:
        import webbrowser
        webbrowser.open("https://google.com")
        return ctx.reply("Открываю браузер")

    if app_name in KNOWN_SITES:
        import webbrowser
        webbrowser.open(KNOWN_SITES[app_name])
        return ctx.reply(f"Открываю {app_name}")

    if app_name in APP_WEB_FALLBACK:
        result = ctx.app_launcher.launch(app_name, ctx.profile.honorific)

        if "не удалось найти" in result.lower():
            fallback = ctx.web_handler.open_web_fallback(app_name, ctx.profile.honorific)
            return fallback if fallback else ctx.reply(f"Не удалось открыть {app_name}")

        return result

    return ctx.app_launcher.launch(app_name, ctx.profile.honorific)


def handle_close(cmd, ctx):
    text = cmd.text_lower
    app_name = (
        text.replace("закрой", "")
            .replace("закрыть", "")
            .replace("выключи приложение", "")
            .replace("пожалуйста", "")
            .strip()
    )

    if not app_name:
        return ctx.reply("Что именно закрыть?")

    if "папк" in app_name:
        return handle_close_folder(cmd, ctx)

    if app_name == "проводник":
        os.system(
            'powershell -Command "'
            '$sh = New-Object -ComObject Shell.Application; '
            '$sh.Windows() | ForEach-Object { $_.Quit() }"'
        )
        return ctx.reply("Закрываю проводник")

    return ctx.app_launcher.close(app_name, ctx.profile.honorific)

def handle_folder(cmd, ctx):
    text = cmd.text_lower
    folder_name = _extract_folder_name(text)

    if not folder_name:
        return ctx.reply("Какую именно папку открыть?")

    folder_key = f"folder:{folder_name}"
    cached_path = ctx.app_launcher.memory.get("apps", {}).get(folder_key)
    if cached_path and os.path.exists(cached_path):
        print(f"[CMD] Папка из кэша: {cached_path}")
        os.startfile(cached_path)
        return ctx.reply(f"Открываю папку {folder_name}")

    print(f"🔍 Ищу папку: {folder_name}...")
    path = ctx.file_search.find_folder(folder_name)

    if path:
        ctx.app_launcher.memory.setdefault("apps", {})[folder_key] = path
        ctx.app_launcher._save_memory()
        os.startfile(path)
        return ctx.reply(f"Открываю папку {folder_name}")

    return ctx.reply(f"Папка {folder_name} не найдена")


def handle_close_folder(cmd, ctx):
    text = cmd.text_lower
    folder_name = _extract_folder_name(text)

    if not folder_name:
        return ctx.reply("Какую именно папку закрыть?")

    folder_key = f"folder:{folder_name}"
    path = ctx.app_launcher.memory.get("apps", {}).get(folder_key)

    if not path:
        path = ctx.file_search.find_folder(folder_name)

    if path:
        window_title = os.path.basename(path.rstrip("/\\"))
        result = os.system(
            f'taskkill /F /FI "IMAGENAME eq explorer.exe" '
            f'/FI "WINDOWTITLE eq {window_title}"'
        )
        if result == 0:
            return ctx.reply(f"Папка {folder_name} закрыта")
        else:
            ps_cmd = (
                f'powershell -Command "'
                f'$sh = New-Object -ComObject Shell.Application; '
                f'$sh.Windows() | Where-Object {{$_.LocationName -eq \'{window_title}\'}} '
                f'| ForEach-Object {{$_.Quit()}}"'
            )
            os.system(ps_cmd)
            return ctx.reply(f"Папка {folder_name} закрыта")

    return ctx.reply(f"Папка {folder_name} не найдена")