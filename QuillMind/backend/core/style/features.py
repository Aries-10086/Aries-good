from __future__ import annotations

import math
import re
from collections import Counter
from statistics import fmean, pstdev
from typing import Any

import jieba


STOPWORDS = {
    "的",
    "了",
    "和",
    "是",
    "在",
    "也",
    "就",
    "都",
    "而",
    "及",
    "与",
    "着",
    "或",
    "一个",
    "没有",
    "我们",
    "你们",
    "他们",
    "这个",
    "那个",
    "这些",
    "那些",
    "可以",
    "因为",
    "所以",
    "如果",
    "但是",
    "然后",
    "已经",
    "还是",
    "就是",
    "什么",
    "怎么",
    "一下",
    "自己",
}

TONE_PARTICLES = ("吧", "啊", "呢", "嘛", "呀", "啦", "哦", "其实", "反正", "说白了")
TOKEN_PATTERN = re.compile(r"^[\u4e00-\u9fff]+$|^[A-Za-z][A-Za-z0-9_-]*$")
SENTENCE_SPLIT_PATTERN = re.compile(r"[。！？!?…]+")
PUNCTUATION_PATTERN = re.compile(r"[，。！？；：、,.!?;:…]")


def extract_features(samples: list[str], *, top_n: int = 30) -> dict[str, Any]:
    if not samples:
        raise ValueError("At least one non-empty sample is required.")

    combined = "\n".join(samples)
    visible_chars = [char for char in combined if not char.isspace()]
    char_count = len(visible_chars)
    sentences = _sentences(combined)
    sentence_lengths = [_sentence_length(sentence) for sentence in sentences]
    sentence_lengths = [length for length in sentence_lengths if length > 0]
    word_counts = Counter(_tokens(combined))
    top_words = [
        {"word": word, "count": count}
        for word, count in word_counts.most_common(top_n)
    ]
    tone_particles = {
        particle: {
            "count": combined.count(particle),
            "per_100_chars": _per_100(combined.count(particle), char_count),
        }
        for particle in TONE_PARTICLES
    }
    punctuation_marks = PUNCTUATION_PATTERN.findall(combined)
    punctuation_total = len(punctuation_marks)
    ellipsis_count = combined.count("…") + combined.count("......")
    exclamation_count = combined.count("！") + combined.count("!")

    return {
        "sample_count": len(samples),
        "char_count": char_count,
        "top_words": top_words,
        "average_sentence_length": round(fmean(sentence_lengths), 2)
        if sentence_lengths
        else 0.0,
        "sentence_length_std": round(pstdev(sentence_lengths), 2)
        if len(sentence_lengths) > 1
        else 0.0,
        "tone_particles": tone_particles,
        "punctuation_habits": {
            "total": punctuation_total,
            "ellipsis_count": ellipsis_count,
            "ellipsis_ratio": _rate(ellipsis_count, punctuation_total),
            "exclamation_count": exclamation_count,
            "exclamation_ratio": _rate(exclamation_count, punctuation_total),
        },
    }


def _tokens(text: str):
    for token in jieba.cut(text):
        normalized = token.strip().lower()
        if (
            normalized
            and normalized not in STOPWORDS
            and normalized not in TONE_PARTICLES
            and TOKEN_PATTERN.fullmatch(normalized)
        ):
            yield normalized


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(text) if part.strip()]


def _sentence_length(sentence: str) -> int:
    return sum(
        1
        for char in sentence
        if not char.isspace() and not PUNCTUATION_PATTERN.fullmatch(char)
    )


def _rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    value = count / total
    return round(value if math.isfinite(value) else 0.0, 4)


def _per_100(count: int, total: int) -> float:
    return round(_rate(count, total) * 100, 2)
