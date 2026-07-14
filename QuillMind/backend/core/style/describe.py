from __future__ import annotations

from typing import Any


def describe_style(features: dict[str, Any]) -> str:
    average_length = float(features.get("average_sentence_length", 0))
    length_std = float(features.get("sentence_length_std", 0))
    sentence_style = _sentence_style(average_length)
    rhythm = "句长变化明显，节奏较灵活" if length_std >= 10 else "句长较稳定，节奏统一"

    particles = features.get("tone_particles", {})
    common_particles = [
        name
        for name, data in sorted(
            particles.items(),
            key=lambda item: item[1].get("per_100_chars", 0),
            reverse=True,
        )
        if data.get("count", 0) > 0
    ][:4]
    particle_text = (
        f"常用语气表达包括“{'、'.join(common_particles)}”，整体更偏口语"
        if common_particles
        else "语气词使用较少，表达相对克制"
    )

    punctuation = features.get("punctuation_habits", {})
    punctuation_notes = []
    if punctuation.get("exclamation_ratio", 0) >= 0.2:
        punctuation_notes.append("感叹号使用较多")
    if punctuation.get("ellipsis_ratio", 0) >= 0.15:
        punctuation_notes.append("有使用省略号留白的习惯")
    punctuation_text = "、".join(punctuation_notes) or "标点使用较平稳"

    keywords = [
        item["word"]
        for item in features.get("top_words", [])[:8]
        if item.get("word")
    ]
    keyword_text = (
        f"高频用词集中在“{'、'.join(keywords)}”"
        if keywords
        else "暂未提取到明显的高频用词"
    )

    return (
        f"该风格{sentence_style}，{rhythm}；{particle_text}；"
        f"{punctuation_text}；{keyword_text}。"
    )


def _sentence_style(average_length: float) -> str:
    if average_length <= 15:
        return "偏好短句，表达直接"
    if average_length <= 30:
        return "以中等长度句子为主，信息密度适中"
    return "偏好长句，常在一句中展开较多信息"
