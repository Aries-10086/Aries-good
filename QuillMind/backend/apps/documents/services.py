from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from core.deai import generate_with_deai_retry
from core.inference import DocumentReviewer, InferenceError
from core.llm import gateway as default_gateway
from core.prompts import engine as default_prompt_engine
from core.style.preprocess import preprocess_text

from .models import DocumentReview


ALLOWED_FILE_SUFFIXES = {".txt", ".md", ".docx"}


class DocumentReviewValidationError(ValueError):
    pass


class DocumentReviewService:
    def __init__(self, *, reviewer=None, llm_gateway=None, prompt_engine=None):
        self.reviewer = reviewer or DocumentReviewer()
        self.llm_gateway = llm_gateway or default_gateway
        self.prompt_engine = prompt_engine or default_prompt_engine

    def review(
        self,
        *,
        review: DocumentReview,
        user_id,
        model_version: str | None = None,
    ) -> DocumentReview:
        raw_text = review.raw_text
        doc_type = review.doc_type
        span_risks = self.reviewer.review(
            raw_text,
            model_version=model_version,
            user_id=user_id,
            document_type=dict(DocumentReview.DocType.choices).get(
                doc_type,
                doc_type,
            ),
        )
        risks = enrich_risks(raw_text, span_risks)
        report = self.generate_report(
            raw_text=raw_text,
            doc_type=doc_type,
            risks=risks,
            user_id=user_id,
        )
        review.risks = risks
        review.report = report
        review.model_version = model_version or settings.DOCUMENT_REVIEW_MODEL_VERSION
        review.save(update_fields=("risks", "report", "model_version", "updated_at"))
        return review

    def generate_report(
        self,
        *,
        raw_text: str,
        doc_type: str,
        risks: list[dict],
        user_id,
    ) -> str:
        document_type = dict(DocumentReview.DocType.choices).get(doc_type, doc_type)
        summary = preprocess_text(raw_text)[:240]

        def generator(**context):
            prompt = self.prompt_engine.render(
                "documents/report",
                version=None,
                user_id=user_id,
                document_type=document_type,
                document_summary=summary,
                risks=risks,
            )
            response = self.llm_gateway.complete(
                prompt,
                user_id=user_id,
                temperature=context.get("temperature", 0.45),
            )
            return response.text.strip()

        result = generate_with_deai_retry(
            generator,
            threshold=settings.DEAI_SCORE_THRESHOLD,
            max_retries=settings.STYLE_GENERATION_MAX_RETRIES,
            base_temperature=0.45,
            temperature_step=0.15,
        )
        if not result.text:
            raise InferenceError("报告生成失败。")
        return result.text


def enrich_risks(raw_text: str, risks: list[dict]) -> list[dict]:
    enriched: list[dict] = []
    for risk in risks:
        start = int(risk["start"])
        end = int(risk["end"])
        quote = raw_text[start:end]
        enriched.append(
            {
                **risk,
                "quote": quote,
                "reason": f"该片段可能存在「{risk['type']}」相关风险，需结合上下文确认。",
                "suggestion": "建议补充更明确的条件、责任边界或例外情形，避免歧义。",
            }
        )
    return enriched


def normalize_review_text(text: str) -> str:
    cleaned = preprocess_text(text)
    if not cleaned:
        raise DocumentReviewValidationError("待审文本不能为空。")
    if len(cleaned) > settings.DOCUMENT_REVIEW_MAX_CHARS:
        raise DocumentReviewValidationError(
            f"待审文本不能超过 {settings.DOCUMENT_REVIEW_MAX_CHARS} 字。"
        )
    return cleaned


def read_review_upload(uploaded_file: UploadedFile) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_FILE_SUFFIXES:
        raise DocumentReviewValidationError("仅支持 txt、md 或 docx 文件。")
    if uploaded_file.size > settings.STYLE_SAMPLE_MAX_FILE_BYTES:
        raise DocumentReviewValidationError(
            f"单个文件不能超过 {settings.STYLE_SAMPLE_MAX_FILE_BYTES} 字节。"
        )

    raw = uploaded_file.read()
    if suffix == ".docx":
        try:
            from docx import Document

            document = Document(BytesIO(raw))
        except Exception as exc:
            raise DocumentReviewValidationError("无法读取 docx 文件。") from exc
        return normalize_review_text(
            "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            )
        )

    try:
        return normalize_review_text(raw.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise DocumentReviewValidationError("文本文件必须使用 UTF-8 编码。") from exc
