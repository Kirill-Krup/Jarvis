"""Каталог нейросетевых голосов для Джарвиса.

Позволяет прослушивать, тестировать и выбирать голоса синтеза речи.
Запуск из консоли:
    python -m core.speakers.catalog           # список голосов и ссылки
    python -m core.speakers.catalog --test    # генерирует образцы всех голосов в папку voice_samples/
    python -m core.speakers.catalog --play brian
"""
import argparse
import asyncio
import io
import os
import sys

RECOMMENDED_VOICES = {
    "brian": {
        "id": "en-US-BrianMultilingualNeural",
        "name": "Brian Multilingual (Кино-Джарвис)",
        "gender": "Мужской",
        "lang": "Мультиязычный (русский/английский)",
        "desc": "Идеален для Джарвиса: сдержанный, харизматичный, кинематографичный мужской голос дворецкого/ИИ.",
    },
    "svetlana": {
        "id": "ru-RU-SvetlanaNeural",
        "name": "Светлана (Svetlana Neural)",
        "gender": "Женский",
        "lang": "Русский (РФ)",
        "desc": "Очень чистая, естественная дикция, приятный тембр, безупречно читает любые русские фразы.",
    },
    "andrew": {
        "id": "en-US-AndrewMultilingualNeural",
        "name": "Andrew Multilingual",
        "gender": "Мужской",
        "lang": "Мультиязычный (русский/английский)",
        "desc": "Мягкий, спокойный, деловой мужской голос для комфортной работы.",
    },
    "william": {
        "id": "en-AU-WilliamMultilingualNeural",
        "name": "William Multilingual",
        "gender": "Мужской",
        "lang": "Мультиязычный (русский/английский)",
        "desc": "Уверенный голос с легким британско-австралийским оттенком.",
    },
    "dmitry": {
        "id": "ru-RU-DmitryNeural",
        "name": "Дмитрий (Dmitry Neural)",
        "gender": "Мужской",
        "lang": "Русский (РФ)",
        "desc": "Классический русский диктор. (Внимание: на серверах Microsoft иногда дает сбой на некоторых словах).",
    },
    "utrobin": {
        "id": "utrobin",
        "name": "Офлайн VITS (Utrobin Local)",
        "gender": "Мужской",
        "lang": "Русский (офлайн)",
        "desc": "Локальная нейросеть VITS ONNX на процессоре, работает полностью автономно без интернета.",
    },
}

ONLINE_GALLERY_URL = "https://speech.microsoft.com/portal/voicegallery"


def print_catalog():
    print("=" * 65)
    print("      🎙️ КАТАЛОГ ГОЛОСОВ ДЛЯ ДЖАРВИСА (Microsoft Neural TTS)")
    print("=" * 65)
    for key, info in RECOMMENDED_VOICES.items():
        print(f"\n[{key.upper()}] {info['name']}")
        print(f"  ID в настройках : {info['id']}")
        print(f"  Пол/Язык        : {info['gender']} | {info['lang']}")
        print(f"  Описание        : {info['desc']}")

    print("\n" + "-" * 65)
    print("🌐 Онлайн-галерея всех голосов Microsoft Azure:")
    print(f"   {ONLINE_GALLERY_URL}")
    print("   (Там можно вбить любой текст и послушать любой голос в браузере)")
    print("-" * 65)
    print("\nКак сменить голос:")
    print("  1. В графическом окне Джарвиса: вкладка «Настройки» -> «Голос Джарвиса».")
    print("  2. В файле config/user_config.json: параметр \"voice\": \"ID_голоса\"")
    print("=" * 65)


async def generate_samples(text="Все системы JARVIS активированы. С возвращением, сэр."):
    import edge_tts
    os.makedirs("voice_samples", exist_ok=True)
    print("\nГенерация аудио-образцов в папку voice_samples/ ...")
    for key, info in RECOMMENDED_VOICES.items():
        if info["id"] == "utrobin":
            continue
        filepath = f"voice_samples/preview_{key}.mp3"
        try:
            c = edge_tts.Communicate(text, voice=info["id"])
            await c.save(filepath)
            print(f"  [OK] {info['name']} -> {filepath}")
        except Exception as e:
            print(f"  [!] {info['name']} ошибка: {e}")


def play_voice(key: str, text="Все системы в норме. Слушаю вас, сэр."):
    key = key.lower().strip()
    if key not in RECOMMENDED_VOICES:
        print(f"Неизвестный голос '{key}'. Доступные: {list(RECOMMENDED_VOICES.keys())}")
        return
    voice_id = RECOMMENDED_VOICES[key]["id"]
    from core.speakers.edge_speaker import EdgeSpeaker
    print(f"Воспроизвожу голос: {RECOMMENDED_VOICES[key]['name']} ...")
    speaker = EdgeSpeaker(voice=voice_id)
    speaker.speak(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Каталог голосов Джарвиса")
    parser.add_argument("--test", action="store_true", help="Сгенерировать MP3-файлы образцов")
    parser.add_argument("--play", type=str, help="Проиграть голос вслух (brian, svetlana, andrew, william, dmitry)")
    args = parser.parse_args()

    if args.play:
        play_voice(args.play)
    elif args.test:
        asyncio.run(generate_samples())
    else:
        print_catalog()
