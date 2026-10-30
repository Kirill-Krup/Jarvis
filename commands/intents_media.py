import ctypes
import time
import subprocess

# Виртуальные коды мультимедийных клавиш Windows
VK_MEDIA_NEXT_TRACK = 0xB0  # 176
VK_MEDIA_PREV_TRACK = 0xB1  # 177
VK_MEDIA_STOP       = 0xB2  # 178
VK_MEDIA_PLAY_PAUSE = 0xB3  # 179

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002


def _send_media_key(vk_code: int):
    """Отправляет глобальное событие мультимедийной клавиши Windows.
    
    Работает со всеми современными браузерами (Chrome, Яндекс Браузер, Edge, Firefox),
    а также настольными плеерами (Spotify, AIMP, Windows Media, VLC и др.)
    даже когда они работают в фоновом режиме.
    """
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        time.sleep(0.05)
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        return True
    except Exception as e:
        print(f"[Media] Ошибка отправки медиа-клавиши: {e}")
        return False


def _try_browser_tab_pause():
    """Дополнительная попытка: если браузер на переднем плане, отправить пробел или 'k'."""
    try:
        import pyautogui
        # Проверяем заголовок активного окна
        user32 = ctypes.windll.user32
        h_wnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(h_wnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h_wnd, buff, length + 1)
        title = buff.value.lower()

        browser_words = ["chrome", "браузер", "edge", "firefox", "opera", "youtube", "музыка", "yandex"]
        if any(w in title for w in browser_words):
            pyautogui.press('space')
            return True
    except Exception:
        pass
    return False


def handle_media_pause(cmd, ctx):
    """Поставить на паузу."""
    _send_media_key(VK_MEDIA_PLAY_PAUSE)
    return ctx.reply("Пауза")


def handle_media_play(cmd, ctx):
    """Возобновить воспроизведение."""
    _send_media_key(VK_MEDIA_PLAY_PAUSE)
    return ctx.reply("Продолжаю воспроизведение")


def handle_media_next(cmd, ctx):
    """Следующий трек."""
    _send_media_key(VK_MEDIA_NEXT_TRACK)
    return ctx.reply("Следующий трек")


def handle_media_prev(cmd, ctx):
    """Предыдущий трек."""
    _send_media_key(VK_MEDIA_PREV_TRACK)
    return ctx.reply("Предыдущий трек")


def handle_media_stop(cmd, ctx):
    """Остановить воспроизведение."""
    _send_media_key(VK_MEDIA_STOP)
    return ctx.reply("Воспроизведение остановлено")
