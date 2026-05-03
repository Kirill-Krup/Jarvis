import webbrowser

KNOWN_SITES = {
    "ютуб": "https://youtube.com",
    "youtube": "https://youtube.com",
    "гугл": "https://google.com",
    "google": "https://google.com",
    "гитхаб": "https://github.com",
    "github": "https://github.com",
    "твиттер": "https://twitter.com",
    "вк": "https://vk.com",
    "вконтакте": "https://vk.com",
    "gmail": "https://mail.google.com",
    "почта": "https://mail.google.com",
    "почту": "https://mail.google.com",
    "переводчик": "https://translate.google.com",
    "яндекс": "https://yandex.ru",
    "яндекс карты": "https://maps.yandex.ru",
    "spotify": "https://open.spotify.com",
    "спотифай": "https://open.spotify.com",
    "иис бгуир": "https://iis.bsuir.by",
    "иис": "https://iis.bsuir.by",
    "из": "https://iis.bsuir.by",
    "сэо": "https://lms.bsuir.by/login/auth.php?errorcode=4",
    "deepseek": "https://chat.deepseek.com",
    "дипсик": "https://chat.deepseek.com"
}

APP_WEB_FALLBACK = {
    "телеграм":  "https://web.telegram.org",
    "telegram":  "https://web.telegram.org",
    "дискорд":   "https://discord.com/app",
    "discord":   "https://discord.com/app",
    "спотифай":  "https://open.spotify.com",
    "spotify":   "https://open.spotify.com",
    "стим":      "https://store.steampowered.com",
    "steam":     "https://store.steampowered.com",
    "вайбер":    "https://web.viber.com",
    "viber":     "https://web.viber.com",
    "whatsapp":  "https://web.whatsapp.com",
    "ватсап":    "https://web.whatsapp.com",
    "вотсап":    "https://web.whatsapp.com",
}


class WebHandler:

    def open_site(self, query: str, honorific: str) -> str:
        query = query.lower().strip()

        if query in KNOWN_SITES:
            webbrowser.open(KNOWN_SITES[query])
            return f"Открываю {query}, {honorific}"

        for site_name, url in KNOWN_SITES.items():
            if site_name in query or query in site_name:
                webbrowser.open(url)
                return f"Открываю {site_name}, {honorific}"

        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(search_url)
        return f"Ищу '{query}' в браузере, {honorific}"

    def open_web_fallback(self, app_name: str, honorific: str) -> str:
        url = APP_WEB_FALLBACK.get(app_name.lower().strip())
        if url:
            webbrowser.open(url)
            return f"Приложение не найдено, открываю веб-версию {app_name}, {honorific}"
        return None
