import os
import datetime
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
            darkcolor="#1a7fbf",
            lightcolor="#2a9fd6",
            bordercolor="#060d16",
            thickness=3,
        )

        self._progress = ttk.Progressbar(
            bottom, style="Jarvis.Horizontal.TProgressbar",
            orient="horizontal", mode="determinate",
            maximum=100,
        )
        self._progress.pack(fill="x", padx=30, pady=(6, 12))

    def update_progress(self, percent: int, text: str):
        self._percent_var.set(f"{percent} %")
        self._status_var.set(text)
        self._progress["value"] = percent
        self._win.update_idletasks()

    def _start_video(self):
        print(f"[VIDEO] CV2_AVAILABLE = {CV2_AVAILABLE}")
        if not CV2_AVAILABLE:
            return

        path = os.path.normpath(os.path.join(_ASSETS, "backvid.mp4"))
        print(f"[VIDEO] path          = {path!r}")
        print(f"[VIDEO] exists        = {os.path.exists(path)}")

        if not os.path.exists(path):
            print("[VIDEO] Пропуск: файл не найден")
            return

        self._cap = cv2.VideoCapture(path)
        print(f"[VIDEO] cap.isOpened  = {self._cap.isOpened()}")
        if self._cap.isOpened():
            self._next_frame()

    def _next_frame(self):
        if not self._running or self._cap is None:
            return

        ret, frame = self._cap.read()
        if not ret:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._cap.read()
            if not ret:
                return

        frame = cv2.resize(frame, (self.WIDTH, self.HEIGHT))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        dim = frame.astype("float32") * 0.35
        frame = dim.clip(0, 255).astype("uint8")

        img = Image.fromarray(frame)
        self._photo = ImageTk.PhotoImage(image=img)

        self.canvas.itemconfig(self._video_item, image=self._photo)
        self.canvas.tag_lower(self._video_item)

        self._win.after(33, self._next_frame)

    def destroy(self):
        self._running = False
        if self._cap:
            self._cap.release()
        self._win.destroy()
        self._root.deiconify()


class MainWindow:
    def __init__(self, root: tk.Tk, profile_name: str,
                 honorific: str, on_exit=None, on_command=None):
        self.root = root
        self.on_exit = on_exit
        self.on_command = on_command

        self.root.title("JARVIS — Панель управления")
        self.root.geometry("1000x640")
        self.root.configure(bg="#070d17")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self._build_ui(profile_name, honorific)

    def _build_ui(self, name: str, honorific: str):
        self._status_var = tk.StringVar(value="")
        container = tk.Frame(self.root, bg="#070d17")
        container.pack(fill="both", expand=True)

        sidebar = tk.Frame(container, bg="#040912", width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="J.A.R.V.I.S",
            font=("Courier New", 14, "bold"),
            fg="#1a7fbf", bg="#040912"
        ).pack(padx=16, pady=(16, 4), anchor="w")

        tk.Label(
            sidebar, text=f"{name}\n{honorific}",
            font=("Courier New", 9),
            fg="#4e729a", bg="#040912", justify="left"
        ).pack(padx=16, pady=(0, 16), anchor="w")

        tk.Frame(sidebar, bg="#0d2035", height=1).pack(fill="x", pady=(0, 8))

        content = tk.Frame(container, bg="#070d17")
        content.pack(side="left", fill="both", expand=True)

        self._pages = {}
        self._current_page = None

        self._pages["home"] = self._build_home_page(content)
        self._pages["settings"] = self._build_settings_page(content, name, honorific)
        self._pages["logs"] = self._build_logs_page(content)

        def add_nav_button(text, page_key):
            btn = tk.Button(
                sidebar, text=text,
                font=("Courier New", 10),
                fg="#c3d4ff", bg="#040912",
                activeforeground="#ffffff",
                activebackground="#1a7fbf",
                relief="flat", anchor="w",
                command=lambda k=page_key: self.show_page(k),
                padx=16, pady=8,
            )
            btn.pack(fill="x")
            return btn

        self._nav_buttons = {}
        self._nav_buttons["home"] = add_nav_button("Монитор речи", "home")
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
            padx=16, pady=8,
        ).pack(fill="x", side="bottom", pady=12)

        self.show_page("home")

    def _build_home_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")

        # 1. Верхняя панель заголовка и статуса
        top_bar = tk.Frame(frame, bg="#070d17")
        top_bar.pack(fill="x", padx=16, pady=(12, 6))

        tk.Label(
            top_bar, text="МОНИТОРИНГ РЕЧИ И ВЫПОЛНЕНИЯ",
            font=("Courier New", 13, "bold"),
            fg="#1a7fbf", bg="#070d17"
        ).pack(side="left")

        self._home_status = tk.StringVar(value="Системы в норме. Ожидаю голосовую команду...")
        tk.Label(
            top_bar, textvariable=self._home_status,
            font=("Courier New", 9, "bold"),
            fg="#38d39f", bg="#070d17"
        ).pack(side="right")

        tk.Frame(frame, bg="#0d2035", height=1).pack(fill="x", padx=16, pady=(0, 8))

        # 2. Информационные карточки
        cards_frame = tk.Frame(frame, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        cards_frame.pack(fill="x", padx=16, pady=4)

        # РЯД 1: ВСЁ ЧТО СЛЫШИТ МИКРОФОН (сырая распознанная фраза Vosk)
        row1 = tk.Frame(cards_frame, bg="#040912")
        row1.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(
            row1, text="🎙️ СЛЫШИТ (микрофон):",
            font=("Courier New", 9, "bold"), fg="#ffb86c", bg="#040912", width=22, anchor="w"
        ).pack(side="left")
        self._raw_heard_var = tk.StringVar(value="—")
        tk.Label(
            row1, textvariable=self._raw_heard_var,
            font=("Courier New", 10), fg="#f1fa8c", bg="#040912", anchor="w"
        ).pack(side="left", fill="x", expand=True)

        # РЯД 2: ЧТО ВЫПОЛНЯЕТСЯ
        row2 = tk.Frame(cards_frame, bg="#040912")
        row2.pack(fill="x", padx=12, pady=4)
        tk.Label(
            row2, text="⚡ КОМАНДА:",
            font=("Courier New", 9, "bold"), fg="#50fa7b", bg="#040912", width=22, anchor="w"
        ).pack(side="left")
        self._executed_cmd_var = tk.StringVar(value="—")
        tk.Label(
            row2, textvariable=self._executed_cmd_var,
            font=("Courier New", 10, "bold"), fg="#ffffff", bg="#040912", anchor="w"
        ).pack(side="left", fill="x", expand=True)

        # РЯД 3: ОТВЕТ ДЖАРВИСА
        row3 = tk.Frame(cards_frame, bg="#040912")
        row3.pack(fill="x", padx=12, pady=(4, 8))
        tk.Label(
            row3, text="💬 ОТВЕТ:",
            font=("Courier New", 9, "bold"), fg="#8be9fd", bg="#040912", width=22, anchor="w"
        ).pack(side="left")
        self._jarvis_reply_var = tk.StringVar(value="—")
        tk.Label(
            row3, textvariable=self._jarvis_reply_var,
            font=("Courier New", 9), fg="#8be9fd", bg="#040912", anchor="w"
        ).pack(side="left", fill="x", expand=True)

        # 3. Панель ручного тестирования команд
        test_panel = tk.Frame(frame, bg="#070d17")
        test_panel.pack(fill="x", padx=16, pady=(10, 4))

        tk.Label(
            test_panel, text="РУЧНОЙ ВВОД КОМАНДЫ (ДЛЯ ТЕСТА):",
            font=("Courier New", 8, "bold"), fg="#4e729a", bg="#070d17"
        ).pack(anchor="w", pady=(0, 2))

        input_row = tk.Frame(test_panel, bg="#070d17")
        input_row.pack(fill="x")

        self._manual_cmd_var = tk.StringVar()
        self._cmd_entry = tk.Entry(
            input_row, textvariable=self._manual_cmd_var,
            font=("Courier New", 10), bg="#040912", fg="#c3d4ff",
            insertbackground="#1a7fbf", relief="flat",
            highlightbackground="#0d2035", highlightthickness=1
        )
        self._cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)
        self._cmd_entry.bind("<Return>", lambda e: self._on_send_manual_cmd())

        tk.Button(
            input_row, text="Выполнить",
            font=("Courier New", 9, "bold"), fg="#ffffff", bg="#1a7fbf",
            activeforeground="#ffffff", activebackground="#0f5c8a",
            relief="flat", padx=14, pady=4,
            command=self._on_send_manual_cmd
        ).pack(side="right")

        # 4. Быстрые кнопки тестирования
        quick_frame = tk.Frame(frame, bg="#070d17")
        quick_frame.pack(fill="x", padx=16, pady=(6, 8))

        quick_cmds = [
            ("📂 Проводник", "открой проводник"),
            ("🌐 Браузер", "открой браузер"),
            ("💬 Телеграм", "открой телегу"),
            ("💲 Курс доллара", "курс доллара"),
            ("🔊 Звук 10%", "звук 10"),
            ("🔊 Звук 50%", "звук 50"),
            ("🔊 Звук 100%", "звук 100"),
        ]
        for label, qcmd in quick_cmds:
            b = tk.Button(
                quick_frame, text=label,
                font=("Courier New", 8), fg="#c3d4ff", bg="#0a1628",
                activeforeground="#ffffff", activebackground="#1a7fbf",
                relief="flat", padx=6, pady=3,
                command=lambda c=qcmd: self._send_quick_cmd(c)
            )
            b.pack(side="left", padx=2)

        # 5. Журнал событий
        tk.Label(
            frame, text="ЖУРНАЛ СОБЫТИЙ И РАСПОЗНАВАНИЯ:",
            font=("Courier New", 8, "bold"), fg="#4e729a", bg="#070d17"
        ).pack(anchor="w", padx=16, pady=(4, 2))

        history_frame = tk.Frame(frame, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        history_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self._history_text = tk.Text(
            history_frame, bg="#040912", fg="#1a7fbf",
            font=("Courier New", 9), relief="flat", state="disabled",
            wrap="word", padx=10, pady=8,
        )
        sb = tk.Scrollbar(history_frame, command=self._history_text.yview, bg="#040912")
        self._history_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._history_text.pack(side="left", fill="both", expand=True)

        return frame

    def _on_send_manual_cmd(self):
        cmd = self._manual_cmd_var.get().strip()
        if not cmd:
            return
        self._manual_cmd_var.set("")
        if self.on_command:
            self.on_command(cmd)

    def _send_quick_cmd(self, cmd_text: str):
        if self.on_command:
            self.on_command(cmd_text)

    def update_speech_info(self, raw_text: str, command: str = ""):
        def _do():
            self._raw_heard_var.set(raw_text or "—")
            self._executed_cmd_var.set(command or "—")
            t_now = datetime.datetime.now().strftime("%H:%M:%S")
            self._append_history(f"[{t_now}] 🎙️ СЛЫШАЛ: '{raw_text}'  ->  КОМАНДА: '{command}'")
        self.root.after(0, _do)

    def update_execution_info(self, response: str, intent_info: str = ""):
        def _do():
            self._jarvis_reply_var.set(response or "—")
            t_now = datetime.datetime.now().strftime("%H:%M:%S")
            self._append_history(f"[{t_now}] 💬 ОТВЕТ: {response}")
        self.root.after(0, _do)

    def _append_history(self, line: str):
        self._history_text.configure(state="normal")
        self._history_text.insert("end", f"{line}\n")
        self._history_text.configure(state="disabled")
        self._history_text.see("end")

    def _build_settings_page(self, parent: tk.Frame,
                             name: str, honorific: str) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")
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
            onvalue=True, offvalue=False,
            font=("Courier New", 9),
            fg="#c3d4ff", bg="#070d17",
            activeforeground="#ffffff",
            activebackground="#070d17",
            selectcolor="#040912",
            anchor="w", relief="flat",
            highlightthickness=0, padx=8,
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

        tk.Label(
            frame, text="ЛОГИ СИСТЕМЫ",
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
        for k, page in self._pages.items():
            page.place_forget()

        self._pages[key].place(relx=0, rely=0, relwidth=1, relheight=1)
        self._current_page = key

        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg="#1a7fbf", bg="#0a1628")
            else:
                btn.configure(fg="#c3d4ff", bg="#040912")

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
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        self.root.after(800, lambda: self.root.attributes("-topmost", False))

    def hide(self):
        self.root.withdraw()

    def quit(self):
        if self.on_exit:
            self.on_exit()
