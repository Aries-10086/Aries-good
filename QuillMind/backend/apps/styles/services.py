from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from core.style import extract_style, preprocess_text


MIN_SAMPLE_COUNT = 3
MIN_SAMPLE_CHARACTERS = 100
ALLOWED_FILE_SUFFIXES = {".txt", ".md", ".docx"}


class StyleSampleValidationError(ValueError):
    pass


def prepare_samples(
    text_samples: list[str] | None = None,
    files: list[UploadedFile] | None = None,
    *,
    minimum_count: int = MIN_SAMPLE_COUNT,
) -> list[str]:
    samples = list(text_samples or [])
    samples.extend(_read_uploaded_file(uploaded_file) for uploaded_file in files or [])
    cleaned_samples = [preprocess_text(sample) for sample in samples]
    cleaned_samples = [sample for sample in cleaned_samples if sample]

    if len(cleaned_samples) < minimum_count:
        raise StyleSampleValidationError(f"至少需要 {minimum_count} 篇有效样本。")

    for index, sample in enumerate(cleaned_samples, start=1):
        character_count = sum(1 for char in sample if not char.isspace())
        if character_count < MIN_SAMPLE_CHARACTERS:
            raise StyleSampleValidationError(
                f"第 {index} 篇样本至少需要 {MIN_SAMPLE_CHARACTERS} 个非空白字符，"
                f"当前为 {character_count} 个。"
            )

    return cleaned_samples


def extract_profile_data(samples: list[str]):
    return extract_style(samples)


def _read_uploaded_file(uploaded_file: UploadedFile) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_FILE_SUFFIXES:
        raise StyleSampleValidationError("样本文件仅支持 txt、md 或 docx 文件。")
    if uploaded_file.size > settings.STYLE_SAMPLE_MAX_FILE_BYTES:
        raise StyleSampleValidationError(
            f"单个样本文件不能超过 {settings.STYLE_SAMPLE_MAX_FILE_BYTES} 字节。"
        )

    raw = uploaded_file.read()
    if suffix == ".docx":
        try:
            from docx import Document

            document = Document(BytesIO(raw))
        except Exception as exc:
            raise StyleSampleValidationError("无法读取 docx 样本文件。") from exc

        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StyleSampleValidationError("样本文件必须使用 UTF-8 编码。") from exc
