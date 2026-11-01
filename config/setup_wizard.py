import tkinter as tk
from tkinter import ttk, messagebox


from config.store import is_first_run, load_config, save_config  # noqa: F401  (is_first_run/load_config реэкспортируются)

MUSIC_PLAYERS = {
    "YouTube Music": "https://music.youtube.com",
    "Spotify": "https://open.spotify.com",
    "Яндекс Музыка": "https://music.yandex.ru",
    "VK Музыка": "https://vk.com/audio",
    "SoundCloud": "https://soundcloud.com",
    "Apple Music": "https://music.apple.com",
    "Deezer": "https://www.deezer.com",
}

MOVIE_SOURCES = {
    "KinoGo": {"url": "https://kinogo-film.fm/index.php?do=search&subaction=search&story=", "name": "KinoGo"},
    "КиноПоиск": {"url": "https://www.kinopoisk.ru/index.php?kp_query=", "name": "КиноПоиск"},
    "HDRezka": {"url": "https://rezka.ag/search/?q=", "name": "HDRezka"},
    "Иви (Ivi)": {"url": "https://www.ivi.ru/search?q=", "name": "Иви"},
    "Okko": {"url": "https://okko.tv/search/", "name": "Okko"},
    "Kinokrad": {"url": "https://kinokrad.cc/index.php?do=search&subaction=search&story=", "name": "Kinokrad"},
    "Яндекс (онлайн)": {"search": "https://yandex.ru/search/?text=смотреть+фильм+{q}+онлайн", "name": "Яндекс"},
}

ANIME_SOURCES = {
    "AnimeGO": {"url": "https://animego.org/search/anime?q=", "catalog": "https://animego.org/anime", "name": "AnimeGO"},
    "YummyAnime": {"url": "https://yummyanime.tv/search?q=", "catalog": "https://yummyanime.tv", "name": "YummyAnime"},
    "Jut.su": {"url": "https://jut.su/search/?q=", "catalog": "https://jut.su", "name": "Jut.su"},
    "Shikimori": {"url": "https://shikimori.one/animes?search=", "catalog": "https://shikimori.one/animes", "name": "Shikimori"},
    "AniLibria": {"url": "https://anilibria.tv/?do=search&subaction=search&story=", "catalog": "https://anilibria.tv", "name": "AniLibria"},
    "Animevost": {"url": "https://animevost.org/index.php?do=search&subaction=search&story=", "catalog": "https://animevost.org", "name": "Animevost"},
    "Яндекс (онлайн)": {"search": "https://yandex.ru/search/?text=смотреть+аниме+{q}+онлайн", "catalog": "https://yandex.ru", "name": "Яндекс"},
}

DEFAULT_CITIES = [
    "Москва",
    "Санкт-Петербург",
    "Минск",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Красноярск",
    "Самара",
    "Уфа",
    "Ростов-на-Дону",
    "Краснодар",
    "Воронеж",
    "Брест",
    "Гродно",
    "Гомель",
]


class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JARVIS — Первоначальная настройка")
        self.root.geometry("520x680")
        self.root.resizable(False, False)
        self.root.configure(bg="#070d17")

        self.name_var = tk.StringVar(value="Денис")
        self.honorific_var = tk.StringVar(value="sir")
        self.city_var = tk.StringVar(value="Москва")
        self.drives_var = tk.StringVar(value="E")
        self.music_player_var = tk.StringVar(value="YouTube Music")
        self.movie_source_var = tk.StringVar(value="KinoGo")
        self.anime_source_var = tk.StringVar(value="AnimeGO")

        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#070d17")
        header.pack(fill="x", pady=(18, 10))

        tk.Label(
            header,
            text="ИНИЦИАЛИЗАЦИЯ JARVIS",
            font=("Courier New", 14, "bold"),
            fg="#1a7fbf", bg="#070d17"
        ).pack()
        tk.Label(
            header,
            text="Настройка персонального профиля и источников данных",
            font=("Courier New", 9),
            fg="#4e729a", bg="#070d17"
        ).pack(pady=(2, 0))

        container = tk.Frame(self.root, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        container.pack(fill="both", expand=True, padx=24, pady=8)

        canvas = tk.Canvas(container, bg="#040912", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#040912")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=12, pady=12)
        scrollbar.pack(side="right", fill="y")

        def add_field(label_text, widget):
            row = tk.Frame(scroll_frame, bg="#040912")
            row.pack(fill="x", pady=6)
            tk.Label(
                row, text=label_text, font=("Courier New", 9, "bold"),
                fg="#c3d4ff", bg="#040912", width=22, anchor="w"
            ).pack(side="left")
            widget.pack(side="left", fill="x", expand=True)

        # 1. Имя
        name_entry = tk.Entry(
            scroll_frame, textvariable=self.name_var,
            font=("Courier New", 9), bg="#070d17", fg="#1a7fbf",
            insertbackground="#1a7fbf", relief="flat", highlightthickness=1, highlightbackground="#0d2035"
        )
        add_field("Ваше имя:", name_entry)

        # 2. Обращение
        honor_row = tk.Frame(scroll_frame, bg="#040912")
        honor_row.pack(fill="x", pady=6)
        tk.Label(
            honor_row, text="Обращение:", font=("Courier New", 9, "bold"),
            fg="#c3d4ff", bg="#040912", width=22, anchor="w"
        ).pack(side="left")
        
        h_box = tk.Frame(honor_row, bg="#040912")
        h_box.pack(side="left", fill="x", expand=True)
        tk.Radiobutton(h_box, text="Сэр", variable=self.honorific_var, value="sir",
                       bg="#040912", fg="#c3d4ff", selectcolor="#070d17", activebackground="#040912").pack(side="left")
        tk.Radiobutton(h_box, text="Мадам", variable=self.honorific_var, value="madam",
                       bg="#040912", fg="#c3d4ff", selectcolor="#070d17", activebackground="#040912").pack(side="left", padx=10)
        tk.Radiobutton(h_box, text="Своё:", variable=self.honorific_var, value="custom",
                       bg="#040912", fg="#c3d4ff", selectcolor="#070d17", activebackground="#040912").pack(side="left")
        self.custom_entry = tk.Entry(h_box, width=12, font=("Courier New", 9),
                                     bg="#070d17", fg="#1a7fbf", state="disabled")
        self.custom_entry.pack(side="left", padx=4)
        self.honorific_var.trace("w", self._on_honorific_change)

        # 3. Город по умолчанию
        city_cb = ttk.Combobox(
            scroll_frame, textvariable=self.city_var,
            values=DEFAULT_CITIES, font=("Courier New", 9)
        )
        add_field("Ваш город:", city_cb)

        # 4. Музыка
        music_cb = ttk.Combobox(
            scroll_frame, textvariable=self.music_player_var,
            values=list(MUSIC_PLAYERS.keys()), state="readonly", font=("Courier New", 9)
        )
        add_field("Плеер музыки:", music_cb)

        # 5. Фильмы
        movie_cb = ttk.Combobox(
            scroll_frame, textvariable=self.movie_source_var,
            values=list(MOVIE_SOURCES.keys()), state="readonly", font=("Courier New", 9)
        )
        add_field("Поиск фильмов:", movie_cb)

        # 6. Аниме
        anime_cb = ttk.Combobox(
            scroll_frame, textvariable=self.anime_source_var,
            values=list(ANIME_SOURCES.keys()), state="readonly", font=("Courier New", 9)
        )
        add_field("Поиск аниме:", anime_cb)

        # 7. Доп. диски
        drives_entry = tk.Entry(
            scroll_frame, textvariable=self.drives_var,
            font=("Courier New", 9), bg="#070d17", fg="#1a7fbf",
            insertbackground="#1a7fbf", relief="flat", highlightthickness=1, highlightbackground="#0d2035"
        )
        add_field("Диски (через запятую):", drives_entry)

        btn_frame = tk.Frame(self.root, bg="#070d17")
        btn_frame.pack(pady=14)

        tk.Button(
            btn_frame,
            text="Завершить настройку",
            command=self._finish_setup,
            bg="#1a7fbf", fg="#ffffff",
            activebackground="#0f5c8a", activeforeground="#ffffff",
            font=("Courier New", 9, "bold"),
            relief="flat", padx=16, pady=6
        ).pack(side="left", padx=8)

        tk.Button(
            btn_frame,
            text="Выход",
            command=self.root.quit,
            bg="#040912", fg="#ff6b6b",
            activebackground="#a12c2c", activeforeground="#ffffff",
            font=("Courier New", 9),
            relief="flat", padx=14, pady=6
        ).pack(side="left", padx=8)

    def _on_honorific_change(self, *args):
        if self.honorific_var.get() == "custom":
            self.custom_entry.config(state="normal")
        else:
            self.custom_entry.config(state="disabled")

    def _parse_drives(self, drives_input: str) -> list:
        extra_drives = []
        if not drives_input.strip():
            return extra_drives

        for drive in drives_input.split(","):
            drive = drive.strip().upper().replace(":", "").replace("/", "")
            if drive:
                extra_drives.append(f"{drive}:/")
        return extra_drives

    def _finish_setup(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Ошибка", "Введите ваше имя.")
            return

        honor_choice = self.honorific_var.get()
        if honor_choice == "custom":
            custom_honor = self.custom_entry.get().strip()
            if not custom_honor:
                messagebox.showwarning("Ошибка", "Введите своё обращение.")
                return
            honorific = custom_honor
        elif honor_choice == "madam":
            honorific = "мадам"
        else:
            honorific = "сэр"

        voice = "en-GB-SoniaNeural" if honorific in ["мадам", "госпожа"] else "en-GB-RyanNeural"
        pitch = "+0Hz" if voice == "en-GB-SoniaNeural" else "-10Hz"

        drives_input = self.drives_var.get()
        extra_drives = self._parse_drives(drives_input)

        city = self.city_var.get().strip() or "Москва"
        music_player = self.music_player_var.get()
        movie_source = self.movie_source_var.get()
        anime_source = self.anime_source_var.get()

        config = {
            "name": name,
            "honorific": honorific,
            "voice": voice,
            "speed": "-5%",
            "pitch": pitch,
            "city": city,
            "extra_drives": extra_drives,
            "music_player": music_player,
            "movie_source": movie_source,
            "anime_source": anime_source,
            "context_timeout": 5.0,
            "microphone_index": None,
            "autostart": False,
        }

        save_config(config)
        messagebox.showinfo("Готово", f"Системы инициализированы. Добро пожаловать, {name}!")
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def run_setup() -> dict:
    if not is_first_run():
        return load_config()

    SetupWizard().run()
    return load_config()
