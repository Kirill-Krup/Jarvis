"""Локальный классификатор намерений (без LLM).

TF-IDF по символьным и словным n-граммам + логистическая регрессия.
Обучение занимает секунды, предсказание — миллисекунды на CPU, моделей
скачивать не нужно. Устойчив к ошибкам распознавания речи, потому что смотрит
на куски слов, а не на точные формы.

Метки описаны в nlu/intents.json:
  "system:mute", "media:pause"  -> intent="system"/"media", target_en="mute"/"pause"
  метки из nlu/actions.py        -> intent="action", target_en=<метка>, params={"query": слот}
  "chat"                         -> обычный разговор

Команды:
  python -m nlu.local_classifier --train     переобучить и показать размер датасета
  python -m nlu.local_classifier --eval      проверить на nlu/intents_holdout.json
  python -m nlu.local_classifier --try "открой стим"
"""
import argparse
import json
import pickle
import random
import time
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union

from nlu.actions import ACTION_LABELS
from nlu.normalizer import normalize_text
from nlu.schemas import IntentResult
from nlu.slots import extract_query

BASE = Path(__file__).parent
DATA_PATH = BASE / "intents.json"
HOLDOUT_PATH = BASE / "intents_holdout.json"
MODEL_PATH = BASE / "intent_model.pkl"
LOW_CONF_LOG = BASE / "low_confidence.jsonl"

LOG_BELOW = 0.65  # фразы с меньшей уверенностью пишем в лог для разметки

# Обёртки: тот же смысл, но сказанный «по-человечески». Учат модель, что
# «а можешь сделать громче» и «громче» — одно и то же, а не набор ключевых слов.
PRE_WRAPPERS = ["а можешь", "не мог бы ты", "будь добр", "мне нужно чтобы ты", "хочу чтобы ты",
                "можешь", "ты можешь", "а ты можешь", "подскажи"]
POST_WRAPPERS = ["сейчас", "быстро", "если не сложно", "прямо сейчас"]
WRAPS_PER_PHRASE = 2
SEED = 42


def _split_label(label: str):
    if ":" in label:
        intent, target = label.split(":", 1)
        return intent, target
    return label, None


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_comment")}


def build_training_set():
    data = _load_json(DATA_PATH)
    slot_lists = data.pop("_slot_lists", {})
    templates = data.pop("_templates", {})
    rng = random.Random(SEED)

    samples = set()
    for label, phrases in data.items():
        for phrase in phrases:
            samples.add((normalize_text(phrase), label))
            for _ in range(WRAPS_PER_PHRASE):
                if rng.random() < 0.7:
                    wrapped = f"{rng.choice(PRE_WRAPPERS)} {phrase}"
                else:
                    wrapped = f"{phrase} {rng.choice(POST_WRAPPERS)}"
                samples.add((normalize_text(wrapped), label))

    for label, spec in templates.items():
        names = slot_lists[spec["slots"]]
        for template in spec["templates"]:
            for name in names:
                samples.add((normalize_text(template.format(n=name)), label))

    samples = sorted((t, l) for t, l in samples if t)
    return [t for t, _ in samples], [l for _, l in samples]


def _build_pipeline():
    return make_pipeline(
        make_union(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True),
            TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True),
        ),
        LogisticRegression(C=20, max_iter=2000, class_weight="balanced"),
    )


def train(save: bool = True):
    texts, labels = build_training_set()
    t0 = time.perf_counter()
    pipe = _build_pipeline()
    pipe.fit(texts, labels)
    elapsed = time.perf_counter() - t0
    if save:
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(pipe, f)
    print(f"[NLU] обучено на {len(texts)} фразах, {len(set(labels))} классов, {elapsed:.2f} с")
    return pipe


class LocalIntentClassifier:
    def __init__(self):
        self.pipe = self._load_or_train()

    @staticmethod
    def _load_or_train():
        stale = (
            not MODEL_PATH.exists()
            or MODEL_PATH.stat().st_mtime < DATA_PATH.stat().st_mtime
        )
        if not stale:
            try:
                with open(MODEL_PATH, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"[NLU] не удалось загрузить модель ({e}), обучаю заново")
        return train(save=True)

    def predict(self, normalized_text: str):
        proba = self.pipe.predict_proba([normalized_text])[0]
        idx = int(proba.argmax())
        return self.pipe.classes_[idx], float(proba[idx])

    def classify(self, normalized_text: str) -> IntentResult:
        label, conf = self.predict(normalized_text)

        if conf < LOG_BELOW:
            self._log_low_confidence(normalized_text, label, conf)

        if label in ACTION_LABELS:
            query = extract_query(label, normalized_text)
            return IntentResult(
                intent="action", target_en=label, target_ru=query or None,
                confidence=conf, params={"query": query}, raw=normalized_text,
            )

        intent, target = _split_label(label)
        if intent == "chat":
            return IntentResult(intent="chat", confidence=conf, raw=normalized_text)
        return IntentResult(intent=intent, target_en=target, confidence=conf, raw=normalized_text)

    @staticmethod
    def _log_low_confidence(text: str, label: str, conf: float):
        try:
            with open(LOW_CONF_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(
                    {"text": text, "guess": label, "conf": round(conf, 3)},
                    ensure_ascii=False) + "\n")
        except OSError:
            pass


# ---------------------------------------------------------------------- CLI

def evaluate():
    clf = LocalIntentClassifier()
    holdout = _load_json(HOLDOUT_PATH)

    total = correct = 0
    errors = []
    good_conf, bad_conf = [], []
    t0 = time.perf_counter()
    for label, phrases in holdout.items():
        for phrase in phrases:
            pred, conf = clf.predict(normalize_text(phrase))
            total += 1
            if pred == label:
                correct += 1
                good_conf.append(conf)
            else:
                bad_conf.append(conf)
                errors.append((phrase, label, pred, conf))
    per_call_ms = (time.perf_counter() - t0) / max(total, 1) * 1000

    print(f"\nТочность на контрольных фразах: {correct}/{total} = {correct / total:.1%}")
    print(f"Время одного предсказания: {per_call_ms:.2f} мс")
    if good_conf:
        print(f"Средняя уверенность верных: {sum(good_conf) / len(good_conf):.2f}")
    if bad_conf:
        print(f"Средняя уверенность ошибочных: {sum(bad_conf) / len(bad_conf):.2f}")
    for phrase, expected, got, conf in errors:
        print(f"  ✗ «{phrase}»: ожидали {expected}, получили {got} ({conf:.2f})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="переобучить модель")
    parser.add_argument("--eval", action="store_true", help="проверить на контрольных фразах")
    parser.add_argument("--try", dest="phrase", help="разобрать одну фразу")
    args = parser.parse_args()

    if args.train:
        train(save=True)
    if args.eval:
        evaluate()
    if args.phrase:
        clf = LocalIntentClassifier()
        r = clf.classify(normalize_text(args.phrase))
        print(f"intent={r.intent} ru={r.target_ru} en={r.target_en} "
              f"url={r.url} conf={r.confidence:.2f} reply={r.chat_reply}")
    if not (args.train or args.eval or args.phrase):
        parser.print_help()


if __name__ == "__main__":
    main()