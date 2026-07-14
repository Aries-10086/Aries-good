from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AIFlavorRule:
    name: str
    pattern: str
    suggestion: str
    weight: float = 0.45


@dataclass(frozen=True)
class AIFlavorHit:
    rule: str
    matched: str
    start: int
    end: int
    weight: float
    suggestion: str


BLACKLIST_RULES = (
    AIFlavorRule("时代套话", r"在当今", "直接说明具体时间或背景"),
    AIFlavorRule("商业黑话", r"赋能", "改成具体动作，例如“帮助”“让”"),
    AIFlavorRule("商业黑话", r"抓手", "直接写采用的办法"),
    AIFlavorRule("总结套话", r"综上所述", "删除或直接写结论"),
    AIFlavorRule("总结套话", r"总而言之", "删除或直接写结论"),
    AIFlavorRule("空泛判断", r"不难发现", "给出事实或数据"),
    AIFlavorRule("空泛强调", r"值得注意的是", "直接写需要注意的事情"),
    AIFlavorRule("绝对化表达", r"毋庸置疑", "说明判断依据"),
    AIFlavorRule("空泛共识", r"众所周知", "补充来源或删除"),
    AIFlavorRule("宏大背景", r"随着.{0,20}(?:发展|进步|普及)", "改成具体变化"),
    AIFlavorRule("机械结构", r"首先.{0,80}其次.{0,80}最后", "改用自然段落组织"),
    AIFlavorRule("机械结构", r"一方面.{0,80}另一方面", "直接陈述两点差异"),
    AIFlavorRule("机械递进", r"不仅.{0,40}(?:而且|更|还)", "减少模板式递进"),
    AIFlavorRule("空泛价值", r"具有(?:十分|非常|极其)?重要意义", "说明具体影响"),
    AIFlavorRule("宏大措辞", r"注入新动能", "写清楚带来的具体变化"),
    AIFlavorRule("宏大措辞", r"构建.{0,20}新格局", "描述具体目标状态"),
    AIFlavorRule("宏大措辞", r"高质量发展", "改成可衡量的目标"),
    AIFlavorRule("宏大措辞", r"实现.{0,20}新突破", "写明突破了什么指标"),
    AIFlavorRule("宏大措辞", r"保驾护航", "说明提供的具体保障"),
    AIFlavorRule("空泛动作", r"充分发挥", "直接说明谁做什么"),
    AIFlavorRule("空泛动作", r"持续推进", "给出下一步动作和时间"),
    AIFlavorRule("商业黑话", r"生态闭环", "说明参与方和实际流程"),
    AIFlavorRule("商业黑话", r"深度融合", "说明如何结合"),
    AIFlavorRule("空泛范围", r"全方位", "列出具体覆盖范围"),
    AIFlavorRule("空泛范围", r"多维度", "列出具体维度"),
    AIFlavorRule("商业黑话", r"助力", "改成具体结果"),
)


def detect_ai_flavor(text: str) -> tuple[float, list[AIFlavorHit]]:
    """Return an AI-flavor score and explainable hits without rewriting text."""
    if not text or not text.strip():
        return 0.0, []

    hits: list[AIFlavorHit] = []

    for rule in BLACKLIST_RULES:
        match = re.search(rule.pattern, text, flags=re.DOTALL)
        if match is None:
            continue

        hits.append(
            AIFlavorHit(
                rule=rule.name,
                matched=match.group(0),
                start=match.start(),
                end=match.end(),
                weight=rule.weight,
                suggestion=rule.suggestion,
            )
        )

    weight_sum = sum(hit.weight for hit in hits)
    score = 1 - math.exp(-weight_sum)
    return round(min(score, 1.0), 4), hits


def build_warnings(hits: list[AIFlavorHit]) -> list[str]:
    """Build optional human-readable warnings; the source text remains unchanged."""
    return [
        f"“{hit.matched}”可能显得模板化：{hit.suggestion}"
        for hit in hits
    ]
