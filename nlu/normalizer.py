import re

FILLER_WORDS = {
    "пожалуйста", "джарвис", "слушай", "эй", "ну", "ка", "мне", "а", "давай"
}

PHRASE_SYNONYMS = {
    "зайди на": "открой сайт",
    "открой веб сайт": "открой сайт",
    "вруби": "включи",
    "запускай": "запусти",
    "сделай погромче": "громче",
    "сделай потише": "тише",
}

WORD_SYNONYMS = {
    "ютубчик": "ютуб",
    "телега": "телеграм",
    "тг": "телеграм",
    "хром": "google chrome",
}

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text)

    for src, dst in PHRASE_SYNONYMS.items():
        text = text.replace(src, dst)

    words = []
    for word in text.split():
        if word in FILLER_WORDS:
            continue
        words.append(WORD_SYNONYMS.get(word, word))

    return " ".join(words).strip()