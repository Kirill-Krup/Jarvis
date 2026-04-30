import os
import tkinter as tk
from tkinter import ttk
from config.autostart import enable_autostart, disable_autostart, is_autostart_enabled
from config.setup_wizard import load_config, save_config

try:
    import cv2
    from PIL import Image, ImageTk
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


class SplashScreen:
    WIDTH  = 960
    HEIGHT = 540

    def __init__(self, root: tk.Tk):
        self._root    = root
        self._running = True
        self._photo   = None
        self._cap     = None

        self._root.withdraw()

        self._win = tk.Toplevel(self._root)
        self._win.overrideredirect(True)
        self._win.configure(bg="#000000")
        self._win.attributes("-topmost", True)

        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._win.geometry(
            f"{self.WIDTH}x{self.HEIGHT}"
            f"+{(sw - self.WIDTH) // 2}+{(sh - self.HEIGHT) // 2}"
        )

        self._build_ui()
        self._win.update_idletasks()
        self._start_video()

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self._win, width=self.WIDTH, height=self.HEIGHT,
            bg="#000000", highlightthickness=0,
        )
        self.canvas.place(x=0, y=0)

        # Создаём placeholder для видео один раз
        self._video_item = self.canvas.create_image(0, 0, anchor="nw", tags="video_bg")

        self.canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2 - 40,
            text="JARVIS", font=("Courier New", 110, "bold"),
            fill="#1c3352", tags="title",
        )
        self.canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2 + 75,
            text="J . A . R . V . I . S",
            font=("Courier New", 14, "bold"),
            fill="#1e3d5a", tags="subtitle",
        )
        self.canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2 + 100,
            text="Just A Rather Very Intelligent System",
            font=("Courier New", 10),
            fill="#132840", tags="tagline",
        )

        BOTTOM_H = 80
        bottom = tk.Frame(self._win, bg="#000000")
        bottom.place(x=0, y=self.HEIGHT - BOTTOM_H,
                     width=self.WIDTH, height=BOTTOM_H)
        bottom.lift()

        tk.Frame(bottom, bg="#0d2035", height=1).pack(fill="x")

        row = tk.Frame(bottom, bg="#000000")
        row.pack(fill="x", padx=30, pady=(8, 0))

        self._status_var = tk.StringVar(value="Инициализация...")
        tk.Label(
            row, textvariable=self._status_var,
            font=("Courier New", 9), fg="#2a5f82",
            bg="#000000", anchor="w",
        ).pack(side="left")

        self._percent_var = tk.StringVar(value="0 %")
        tk.Label(
            row, textvariable=self._percent_var,
            font=("Courier New", 11, "bold"), fg="#1a7fbf",
            bg="#000000", anchor="e",
        ).pack(side="right")

        style = ttk.Style(self._root)
        style.theme_use("default")
        style.configure(
            "Jarvis.Horizontal.TProgressbar",
            troughcolor="#060d16",
            background="#1a7fbf",
            bordercolor="#060d16",
            lightcolor="#2aa8f5",
            darkcolor="#0d5a8a",
            thickness=6,
        )
        self._bar = ttk.Progressbar(
            bottom, style="Jarvis.Horizontal.TProgressbar",
            orient="horizontal", maximum=100, mode="determinate",
        )
        self._bar.pack(fill="x", padx=30, pady=(6, 0))

    def _next_frame(self):
        if not self._running or not self._cap:
            return
        ret, frame = self._cap.read()
        if not ret:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._win.after(33, self._next_frame)
            return
        frame = cv2.resize(frame, (self.WIDTH, self.HEIGHT))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = (frame * 0.35).clip(0, 255).astype("uint8")
        self._photo = ImageTk.PhotoImage(Image.fromarray(frame))
        self.canvas.itemconfig(self._video_item, image=self._photo)
        self.canvas.tag_lower("video_bg")
        self._win.after(33, self._next_frame)

    def update_progress(self, percent: int, status: str):
        self._win.after(0, self._apply_update, int(percent), status)

    def _apply_update(self, percent: int, status: str):
        self._bar["value"] = percent
        self._percent_var.set(f"{percent} %")
        self._status_var.set(f"▸  {status}")

    def _start_video(self):
        path = os.path.normpath(os.path.join(_ASSETS, "backvid.mp4"))
        print(f"[VIDEO] CV2_AVAILABLE = {CV2_AVAILABLE}")
        print(f"[VIDEO] path          = {path!r}")
        print(f"[VIDEO] exists        = {os.path.exists(path)}")

        if not CV2_AVAILABLE:
            print("[VIDEO] Пропуск: cv2 не установлен (pip install opencv-python)")
            return
        if not os.path.exists(path):
            print("[VIDEO] Пропуск: файл не найден")
            return

        self._cap = cv2.VideoCapture(path)
        print(f"[VIDEO] cap.isOpened  = {self._cap.isOpened()}")
        if self._cap.isOpened():
            self._next_frame()

    def destroy(self):
        self._running = False
        if self._cap:
            self._cap.release()
        self._win.destroy()
        self._root.deiconify()


class MainWindow:
    def __init__(self, root: tk.Tk, profile_name: str,
                 honorific: str, on_exit=None):
        self.root    = root
        self.on_exit = on_exit

        self.root.title("JARVIS")
        self.root.geometry("900x520")
        self.root.configure(bg="#070d17")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self._build_ui(profile_name, honorific)

    def _build_ui(self, name: str, honorific: str):
        # общий контейнер
        container = tk.Frame(self.root, bg="#070d17")
        container.pack(fill="both", expand=True)

        # левый сайдбар
        sidebar = tk.Frame(container, bg="#040912", width=160)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="J.A.R.V.I.S",
            font=("Courier New", 13, "bold"),
            fg="#1a7fbf", bg="#040912"
        ).pack(padx=16, pady=(16, 8), anchor="w")

        tk.Label(
            sidebar, text=f"{name}\n{honorific}",
            font=("Courier New", 8),
            fg="#1e3d5a", bg="#040912", justify="left"
        ).pack(padx=16, pady=(0, 16), anchor="w")

        tk.Frame(sidebar, bg="#0d2035", height=1).pack(fill="x", pady=(0, 8))

        # правая часть – область контента
        content = tk.Frame(container, bg="#070d17")
        content.pack(side="left", fill="both", expand=True)

        # создаём три страницы
        self._pages = {}
        self._current_page = None

        self._pages["home"] = self._build_home_page(content)
        self._pages["settings"] = self._build_settings_page(content, name, honorific)
        self._pages["logs"] = self._build_logs_page(content)

        # кнопки навигации в сайдбаре
        def add_nav_button(text, page_key):
            btn = tk.Button(
                sidebar, text=text,
                font=("Courier New", 10),
                fg="#c3d4ff", bg="#040912",
                activeforeground="#ffffff",
                activebackground="#1a7fbf",
                relief="flat", anchor="w",
                command=lambda k=page_key: self.show_page(k),
                padx=16, pady=6,
            )
            btn.pack(fill="x")
            return btn

        self._nav_buttons = {}
        self._nav_buttons["home"] = add_nav_button("Главная", "home")
        self._nav_buttons["settings"] = add_nav_button("Настройки", "settings")
        self._nav_buttons["logs"] = add_nav_button("Логи", "logs")

        tk.Frame(sidebar, bg="#0d2035", height=1).pack(fill="x", pady=8)

        tk.Button(
            sidebar, text="Выход",
            font=("Courier New", 10),
            fg="#ff6b6b", bg="#040912",
            activeforeground="#ffffff",
            activebackground="#a12c2c",
            relief="flat", anchor="w",
            command=self.quit,
            padx=16, pady=6,
        ).pack(fill="x", side="bottom", pady=12)

        # по умолчанию – главная
        self.show_page("home")

    def _build_home_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")
        frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        tk.Label(
            frame, text="СИСТЕМЫ В НОРМЕ",
            font=("Courier New", 16, "bold"),
            fg="#1a7fbf", bg="#070d17"
        ).pack(pady=(32, 8))

        self._home_status = tk.StringVar(value="Ожидаю голосовую команду...")
        tk.Label(
            frame, textvariable=self._home_status,
            font=("Courier New", 10),
            fg="#9aa5c0", bg="#070d17"
        ).pack(pady=(0, 24))

        info = (
            "• Голосовой движок активен\n"
            "• Микрофон подключен\n"
            "• Модуль команд загружен\n"
            "• Скажи 'Джарвис' чтобы активировать"
        )
        tk.Label(
            frame, text=info,
            font=("Courier New", 9),
            fg="#5f6b88", bg="#070d17",
            justify="left"
        ).pack(pady=(0, 24), anchor="center")

        return frame

    def _build_settings_page(self, parent: tk.Frame,
                             name: str, honorific: str) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")
        frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        tk.Label(
            frame, text="НАСТРОЙКИ",
            font=("Courier New", 14, "bold"),
            fg="#1a7fbf", bg="#070d17"
        ).pack(pady=(24, 16))

        form = tk.Frame(frame, bg="#070d17")
        form.pack(pady=12)

        tk.Label(form, text="Имя:",
                 font=("Courier New", 9),
                 fg="#c3d4ff", bg="#070d17").grid(row=0, column=0, sticky="w", pady=8, padx=8)
        self._name_var = tk.StringVar(value=name)
        tk.Entry(form, textvariable=self._name_var,
                 font=("Courier New", 9),
                 bg="#040912", fg="#1a7fbf",
                 insertbackground="#1a7fbf",
                 relief="flat", width=26).grid(row=0, column=1, pady=8, padx=8)

        tk.Label(form, text="Обращение:",
                 font=("Courier New", 9),
                 fg="#c3d4ff", bg="#070d17").grid(row=1, column=0, sticky="w", pady=8, padx=8)
        self._honorific_var = tk.StringVar(value=honorific)
        tk.Entry(form, textvariable=self._honorific_var,
                 font=("Courier New", 9),
                 bg="#040912", fg="#1a7fbf",
                 insertbackground="#1a7fbf",
                 relief="flat", width=26).grid(row=1, column=1, pady=8, padx=8)

        cfg = load_config()
        self._autostart_var = tk.BooleanVar(
            value=bool(cfg.get("autostart", False)) or is_autostart_enabled()
        )

        tk.Checkbutton(
            frame,
            text="Запускать вместе с Windows",
            variable=self._autostart_var,
            onvalue=True,
            offvalue=False,
            font=("Courier New", 9),
            fg="#c3d4ff",
            bg="#070d17",
            activeforeground="#ffffff",
            activebackground="#070d17",
            selectcolor="#040912",
            anchor="w",
            relief="flat",
            highlightthickness=0,
            padx=8,
        ).pack(anchor="w", padx=32, pady=(8, 0))

        def save_settings():
            cfg_local = load_config()
            cfg_local["name"] = self._name_var.get().strip()
            cfg_local["honorific"] = self._honorific_var.get().strip()
            cfg_local["autostart"] = bool(self._autostart_var.get())
            save_config(cfg_local)

            if cfg_local["autostart"]:
                enable_autostart()
            else:
                disable_autostart()

        tk.Button(
            frame, text="Сохранить",
            font=("Courier New", 10),
            fg="#ffffff", bg="#1a7fbf",
            activeforeground="#ffffff",
            activebackground="#0f5c8a",
            relief="flat", padx=18, pady=6,
            command=save_settings
        ).pack(pady=16)

        return frame

    def _build_logs_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")
        frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        tk.Label(
            frame, text="ЛОГИ",
            font=("Courier New", 14, "bold"),
            fg="#1a7fbf", bg="#070d17"
        ).pack(pady=(16, 8))

        text_frame = tk.Frame(frame, bg="#040912",
                              highlightbackground="#0d2035",
                              highlightthickness=1)
        text_frame.pack(fill="both", expand=True, padx=18, pady=12)

        self._log = tk.Text(
            text_frame, bg="#040912", fg="#1a7fbf",
            font=("Courier New", 9), relief="flat",
            state="disabled", wrap="word",
            insertbackground="#1a7fbf",
            selectbackground="#0d2035",
            padx=10, pady=8,
        )
        sb = tk.Scrollbar(text_frame, command=self._log.yview,
                          bg="#040912", troughcolor="#040912",
                          activebackground="#0d2035")
        self._log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log.pack(side="left", fill="both", expand=True)

        return frame

    def show_page(self, key: str):
        if self._current_page is not None:
            self._pages[self._current_page].place_forget()
        self._current_page = key
        self._pages[key].place(relx=0, rely=0, relwidth=1, relheight=1)

    def log(self, message: str):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", f"▸  {message}\n")
            self._log.configure(state="disabled")
            self._log.see("end")
        self.root.after(0, _do)

    def set_status(self, text: str):
        self.root.after(0, lambda: self._status_var.set(f"▸  {text}"))

    def set_home_status(self, text: str):
        if hasattr(self, "_home_status"):
            self.root.after(0, lambda: self._home_status.set(text))

    def show(self):
        self.root.after(0, self._do_show)

    def _do_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()

    def quit(self):
        if self.on_exit:
            self.on_exit()