import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import re
import threading
import sounddevice as sd
import numpy as np
import onnxruntime
from transformers import AutoTokenizer
from ruaccent import RUAccent

try:
    import num2words
except ImportError:
    num2words = None

from core.speakers.base_speaker import BaseSpeaker


def verbalize_numbers(text: str) -> str:
    """Преобразует любые числа и дроби в тексте в русские слова для TTS."""
    if not num2words:
        return text

    def repl_float(m):
        full = m.group(0)
        try:
            parts = full.replace(',', '.').split('.')
            whole = int(parts[0])
            frac = int(parts[1])
            whole_w = num2words.num2words(whole, lang='ru')
            frac_w = num2words.num2words(frac, lang='ru')
            return f"{whole_w} целых {frac_w} сотых"
        except Exception:
            return full

    def repl_int(m):
        num = int(m.group(0))
        try:
            return num2words.num2words(num, lang='ru')
        except Exception:
            return m.group(0)

    # 1. Сначала десятичные дроби (80.68, 2,95)
    text = re.sub(r'\b\d+[.,]\d+\b', repl_float, text)
    # 2. Затем целые числа (10, 50, 100)
    text = re.sub(r'\b\d+\b', repl_int, text)
    return text


class UtrobinSpeaker(BaseSpeaker):
    def __init__(self):
        self._accent_cache = {
            "открываю проводник, сэр": "открыв+аю проводн+ик, с+эр",
            "запускаю проводник, сэр": "запуск+аю проводн+ик, с+эр",
            "запускаю телеграм, сэр": "запуск+аю телегр+ам, с+эр",
            "запускаю телега, сэр": "запуск+аю тел+ега, с+эр",
            "запускаю телегу, сэр": "запуск+аю тел+егу, с+эр",
            "запускаю стим, сэр": "запуск+аю ст+им, с+эр",
            "запускаю дискорд, сэр": "запуск+аю диск+орд, с+эр",
            "запускаю яндекс, сэр": "запуск+аю +яндекс, с+эр",
            "запускаю гугл хром, сэр": "запуск+аю г+угл хр+ом, с+эр",
            "запускаю браузер, сэр": "запуск+аю бр+аузер, с+эр",
            "запускаю калькулятор, сэр": "запуск+аю калькул+ятор, с+эр",
            "запускаю блокнот, сэр": "запуск+аю блокн+от, с+эр",
            "сделано, сэр": "сд+елано, с+эр",
            "не расслышал, сэр": "не рассл+ышал, с+эр",
            "слушаю, сэр": "сл+ушаю, с+эр",
            "аудиосистемы выключены": "аудиосист+емы в+ыключены",
            "устанавливаю громкость на 100 процентов, сэр": "устанавл+иваю гр+омкость на сто проц+ентов, с+эр",
            "устанавливаю громкость на 50 процентов, сэр": "устанавл+иваю гр+омкость на пятьдес+ят проц+ентов, с+эр",
            "все системы в норме. добро пожаловать, денис. чем могу помочь, сэр?": "все сист+емы в н+орме. добр+о пож+аловать, ден+ис. чем мог+у пом+очь, с+эр?",
            "импортирую настройки, системы в норме": "импорт+ирую настр+ойки, сист+емы в н+орме",
            "снова в строю, сэр": "сн+ова в стро+ю, с+эр",
            "загружаю, сэр": "загруж+аю, с+эр",
            "отключаю питание. до встречи, сэр": "отключ+аю пит+ание. до встр+ечи, с+эр",
        }
        self._load_model()
        print("UtrobinSpeaker готов [OK]")

    def _load_model(self):
        print("Загружаю голосовую модель UtrobinTTS...")

        model_path = "voice_samples/model.onnx"

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Файл модели не найден: {model_path}\n"
                f"Скачайте model.onnx из:\n"
                f"https://huggingface.co/utrobinmv/tts_ru_free_hf_vits_low_multispeaker"
            )

        sess_options = onnxruntime.SessionOptions()
        self.model = onnxruntime.InferenceSession(model_path, sess_options=sess_options)

        self.tokenizer = AutoTokenizer.from_pretrained(
            "utrobinmv/tts_ru_free_hf_vits_low_multispeaker"
        )

        self.accentizer = RUAccent()
        self.accentizer.load(omograph_model_size='turbo', use_dictionary=True)

        self.sample_rate = 16000
        self.speaker_id = 1

        # Мгновенный прогрев ONNX графа
        try:
            inp = self.tokenizer("пр+ивет", return_tensors="np")
            self.model.run(
                None,
                {
                    "input_ids": inp["input_ids"],
                    "attention_mask": inp["attention_mask"],
                    "sid": np.array([self.speaker_id]),
                },
            )
        except Exception:
            pass

        print(f"[OK] UtrobinTTS загружен, sample_rate={self.sample_rate}, speaker_id={self.speaker_id}")

    def speak(self, text: str):
        if not text or not str(text).strip():
            return
        text = verbalize_numbers(str(text))
        print(f"Джарвис: {text}")
        try:
            audio_thread = threading.Thread(target=self._generate_and_play, args=(text,))
            audio_thread.start()
            audio_thread.join()
        except Exception as e:
            print(f"Ошибка UtrobinSpeaker: {e}")

    def _generate_and_play(self, text: str):
        try:
            text_lower = text.lower().strip()
            if text_lower in self._accent_cache:
                text_with_accents = self._accent_cache[text_lower]
            else:
                text_with_accents = self.accentizer.process_all(text_lower)
                self._accent_cache[text_lower] = text_with_accents

            inputs = self.tokenizer(text_with_accents, return_tensors="np")
            sid = np.array([self.speaker_id])

            output = self.model.run(
                None,
                {
                    "input_ids": inputs["input_ids"],
                    "attention_mask": inputs["attention_mask"],
                    "sid": sid,
                },
            )[0]

            audio_array = output[0]
            audio_array = np.clip(audio_array, -1, 1)
            audio_int16 = (audio_array * 32767).astype(np.int16)

            sd.play(audio_int16, samplerate=self.sample_rate)
            sd.wait()

        except Exception as e:
            print(f"Ошибка генерации речи UtrobinSpeaker: {e}")
            import traceback
            traceback.print_exc()
