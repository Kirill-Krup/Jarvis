"""Синтез речи высокого качества: Microsoft Edge Neural TTS.

Использует сверхреалистичные нейросетевые голоса (Brian, Svetlana, Andrew, Dmitry).
Имеет многоуровневый отказоустойчивый каскад:
1. Основной выбранный голос (Edge Neural)
2. Резервный нейросетевой голос (Edge Neural Svetlana/Brian) при сбое параметров конкретного голоса
3. Офлайн VITS-синтез (UtrobinSpeaker) при полном отсутствии интернета.
"""
import asyncio
import io
import re
import threading
import numpy as np
import soundfile as sf
import edge_tts

from core import audio_out
from core.speakers.base_speaker import BaseSpeaker
from core.speakers.utrobin_speaker import UtrobinSpeaker

DEFAULT_VOICE = "en-US-BrianMultilingualNeural"


def clean_tts_text(text: str) -> str:
    """Очищает текст от кавычек, спецсимволов и XML-тегов, сбивающих SSML парсер."""
    if not text:
        return ""
    t = str(text)
    # Заменяем кавычки-ёлочки и одинарные/двойные кавычки на пробелы
    t = re.sub(r"[«»\"'`<>]", " ", t)
    # Заменяем длинные тире на обычный дефис
    t = re.sub(r"[\u2010-\u2015—–]", "-", t)
    # Заменяем амперсанд на безопасное слово
    t = t.replace("&", " и ")
    # Схлопываем лишние пробелы
    t = re.sub(r"\s+", " ", t).strip()
    return t


class EdgeSpeaker(BaseSpeaker):
    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self._cache: dict[str, tuple[np.ndarray, int]] = {}
        self._cache_lock = threading.Lock()
        self._fallback_engine = None
        print(f"EdgeSpeaker готов [OK] (Голос: {self.voice})")

    def _get_fallback(self):
        if self._fallback_engine is None:
            try:
                self._fallback_engine = UtrobinSpeaker()
            except Exception as e:
                print(f"[TTS] Не удалось инициализировать резервный UtrobinSpeaker: {e}")
        return self._fallback_engine

    def speak(self, text: str):
        if not text or not str(text).strip():
            return
        clean_text = clean_tts_text(text)
        if not clean_text:
            return

        # Проверяем кэш коротких частых фраз (для мгновенного отклика 0 мс)
        with self._cache_lock:
            cached = self._cache.get(clean_text)
        if cached:
            audio_out.play(cached[0], cached[1])
            return

        # Попытка нейросетевого синтеза с отказоустойчивым резервом голосов
        try:
            asyncio.run(self._synth_and_play_with_fallbacks(clean_text))
            return
        except Exception as e:
            print(f"[EdgeTTS] Сетевой сбой озвучки ({e}), использую локальный офлайн-голос")

        # При полном сбое сети используем локальный офлайн VITS
        fallback = self._get_fallback()
        if fallback:
            try:
                fallback.speak(clean_text)
            except Exception as e:
                print(f"[TTS Fallback Error] {e}")

    async def _synth_and_play_with_fallbacks(self, text: str):
        voice_candidates = [self.voice]
        if self.voice != "ru-RU-SvetlanaNeural":
            voice_candidates.append("ru-RU-SvetlanaNeural")
        if "Brian" not in self.voice:
            voice_candidates.append("en-US-BrianMultilingualNeural")

        last_error = None
        for candidate_voice in voice_candidates:
            try:
                await self._synth_and_play(text, voice=candidate_voice)
                return
            except Exception as err:
                last_error = err
                continue

        if last_error:
            raise last_error

    async def _synth_and_play(self, text: str, voice: str):
        communicate = edge_tts.Communicate(
            text, voice=voice, rate=self.rate, pitch=self.pitch
        )
        buffer = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.extend(chunk["data"])

        if not buffer:
            raise ValueError(f"Пустой аудио-поток от EdgeTTS (голос: {voice})")

        data, sample_rate = sf.read(io.BytesIO(buffer), dtype="float32")

        # Кэшируем короткие подтверждения (до 40 символов)
        if len(text) <= 40:
            with self._cache_lock:
                if len(self._cache) < 200:
                    self._cache[text] = (data, sample_rate)

        audio_out.play(data, sample_rate)
