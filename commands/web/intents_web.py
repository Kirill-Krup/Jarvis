import webbrowser


def handle_web(cmd, ctx):
    """
    'открой сайт ...', 'найди сайт ...', 'зайди на ...'
    """
    text = cmd.text_lower
    query = (
        text.replace("открой сайт", "")
            .replace("найди сайт", "")
            .replace("зайди на", "")
            .strip()
    )

    if not query:
        return ctx.reply("Какой сайт открыть?")

    return ctx.web_handler.open_site(query, ctx.profile.honorific)


def handle_search(cmd, ctx):
    """
    'загугли ...', 'найди ...', 'поиск ...'
    """
    text = cmd.text_lower
    query = (
        text.replace("загугли", "")
            .replace("найди", "")
            .replace("поиск", "")
            .strip()
    )

    if not query:
        return ctx.reply("Что именно найти?")

    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(search_url)
    return ctx.reply(f"Ищу {query}")


def handle_info_search(cmd, ctx):
    """
    'найди информацию по запросу ...', 'найди информацию ...', 'хочу узнать ...'
    """
    text = cmd.text_lower
    query = (
        text.replace("найди информацию по запросу", "")
            .replace("найди информацию по", "")
            .replace("найди информацию", "")
            .replace("хочу узнать", "")
            .strip()
    )

    if not query:
        return ctx.reply("Какую информацию искать?")

    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    return ctx.reply(f"Ищу информацию по запросу {query}")


def handle_youtube(cmd, ctx):
    webbrowser.open("https://youtube.com")
    return ctx.reply("Открываю YouTube")


def handle_video_search(cmd, ctx):
    text = cmd.text_lower
    query = text.replace("найди видео", "").strip()
    if not query:
        return ctx.reply("Какое видео найти?")
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    webbrowser.open(url)
    return ctx.reply(f"Ищу видео {query}")


def handle_music(cmd, ctx):
    webbrowser.open("https://music.youtube.com")
    return ctx.reply("Открываю музыку")


def handle_movie_search(cmd, ctx):
    """
    'хочу посмотреть ...', 'давай посмотрим ...', 'посмотреть фильм/сериал ...'
    """
    text = cmd.text_lower
    cleaned = (
        text.replace("хочу посмотреть", "")
            .replace("давай посмотрим", "")
            .replace("посмотреть фильм", "")
            .replace("посмотреть сериал", "")
            .strip()
    )

    if not cleaned:
        return ctx.reply("Какой фильм или сериал вы хотите посмотреть?")

    query = cleaned.replace(" ", "+")
    url = f"https://www.kinopoisk.ru/index.php?kp_query={query}"
    webbrowser.open(url)
    return ctx.reply(f"Ищу что посмотреть по запросу {cleaned}")