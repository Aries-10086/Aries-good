#!/usr/bin/env python3
"""Run the module-two MVP path against a deployed Wenmo API.

Creates three disposable accounts and style profiles, then exercises:
register -> login -> create profile -> stream generation -> submit feedback.
Only run this against a development or staging environment.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = os.getenv("WENMO_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_URL = f"{BASE_URL}/api/v1"
PASSWORD = os.getenv("WENMO_E2E_PASSWORD", "")


@dataclass(frozen=True)
class DemoCase:
    slug: str
    profile_name: str
    samples: list[str]
    topic: str
    outline: str
    keywords: list[str]
    tone_slider: int


CASES = [
    DemoCase(
        slug="casual",
        profile_name="轻松生活随笔",
        samples=[
            "昨晚下班的时候突然下雨，我没带伞，就在便利店门口站了一会儿。其实也不着急，雨落在路灯下面，像一层很细的雾。店员把热咖啡递给我，还提醒杯盖有点松。那一刻觉得，普通日子也挺好。等雨小了，我慢慢走回家，鞋边还是湿了，但心情没有被打扰。",
            "周末本来想睡到中午，结果楼下早餐店的香味先把我叫醒了。反正也醒了，我就穿着拖鞋下楼，点了豆浆和刚出锅的饼。老板还是老样子，一边忙一边聊天。太阳不晒，风也刚好，吃完以后顺路买了束小花。没有特别安排的一天，反而过得很舒服。",
            "最近开始把手机放远一点。吃饭的时候认真吃饭，散步的时候就看看树和路边的小店。说白了，并不是突然变自律，只是发现注意力一直被切碎，人会莫名其妙地累。现在每天留半小时发呆，什么都不完成，也不觉得浪费。慢下来以后，很多小事反而看得更清楚。",
        ],
        topic="写一段邀请朋友周末来家里吃火锅的微信消息",
        outline="先问候近况；说明周六晚上准备火锅；语气轻松，给对方留出选择空间",
        keywords=["周六", "火锅", "有空就来"],
        tone_slider=82,
    ),
    DemoCase(
        slug="concise",
        profile_name="清晰工作表达",
        samples=[
            "今天完成了首页交互调整，登录、空状态和错误提示均已覆盖。当前还剩两项：移动端间距复核，以及接口超时场景验证。明天上午先处理移动端，下午与后端联调。若测试环境稳定，预计下班前可以提交验收版本。需要协助的地方只有测试账号权限，请在十点前确认。",
            "本周评审聚焦三个问题。第一，用户是否能快速理解入口；第二，生成过程是否有明确反馈；第三，失败后能否继续操作。讨论时请围绕实际页面和数据，不展开远期设想。会前把意见写进文档，会上只处理分歧。最终结论需要明确负责人、完成时间和验收方式。",
            "接口变更已同步到文档。请求新增关键词数组，响应增加反馈状态，原有字段保持不变。前端升级后可直接兼容旧数据。部署顺序建议先上后端，再发布前端，期间不会影响现有生成流程。回滚时只需恢复应用版本，新增字段允许为空，不需要回退数据库迁移。",
        ],
        topic="写一段项目延期一天的内部进度说明",
        outline="说明原因；列出剩余工作；给出新的交付时间；明确需要的协助",
        keywords=["联调", "明天下午", "测试环境"],
        tone_slider=22,
    ),
    DemoCase(
        slug="narrative",
        profile_name="温和叙事文风",
        samples=[
            "傍晚的风从窗缝里进来，把桌上的纸轻轻掀起一角。她停下笔，听见楼下有人收摊，铁门落下时发出短促的响声。一天就这样慢慢收拢了。杯里的茶已经凉透，她却没有急着换，只是看着天色从浅蓝变成灰紫，想起很多年前也有一个相似的黄昏。",
            "车到小站时，月台上只有两个人。老人提着布袋，孩子抱着一只旧玩偶，他们都没有说话。远处的山被晨雾遮住，只留下柔软的轮廓。列车再次启动以后，窗外的树一棵棵向后退。她忽然明白，离开并不总是响亮的决定，有时只是安静地坐上早班车。",
            "院子里的桂花开得晚，香气却很稳。母亲把洗好的衣服晾上，又弯腰拾起一片落叶。厨房里煨着汤，锅盖偶尔轻轻碰一下。这样的声音从小听到大，过去从不觉得特别。直到多年后在陌生城市醒来，她才发现，所谓想家，常常只是想再听一次那些细小的动静。",
        ],
        topic="写一段关于夏夜散步的短文",
        outline="从走出家门写起；描写街灯、晚风和路人；结尾停在一个具体画面",
        keywords=["夏夜", "晚风", "街灯"],
        tone_slider=48,
    ),
]


def request_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    token: str = "",
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} returned {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Cannot connect to {BASE_URL}: {exc.reason}") from exc


def stream_generation(
    token: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], float, float]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{API_URL}/styles/generate?stream=true",
        data=body,
        headers={
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    started = time.perf_counter()
    first_token_seconds: float | None = None
    current_event = ""
    data_lines: list[str] = []
    complete: dict[str, Any] = {}

    try:
        with urlopen(request, timeout=120) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data_lines.append(line.split(":", 1)[1].lstrip())
                elif not line and current_event and data_lines:
                    data = json.loads("\n".join(data_lines))
                    if current_event == "token" and first_token_seconds is None:
                        first_token_seconds = time.perf_counter() - started
                    elif current_event == "complete":
                        complete = data
                    elif current_event == "error":
                        raise RuntimeError(data.get("detail", "stream generation failed"))
                    current_event = ""
                    data_lines = []
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"stream generation returned {exc.code}: {detail}") from exc

    total_seconds = time.perf_counter() - started
    if not complete:
        raise RuntimeError("stream ended without a complete event")
    if first_token_seconds is None:
        raise RuntimeError("stream completed without a token event")
    return complete, first_token_seconds, total_seconds


def validate_samples() -> None:
    for case in CASES:
        if len(case.samples) != 3:
            raise RuntimeError(f"{case.slug} must contain exactly three samples")
        for index, sample in enumerate(case.samples, start=1):
            visible = len("".join(sample.split()))
            if visible < 100:
                raise RuntimeError(
                    f"{case.slug} sample {index} has only {visible} visible characters"
                )


def run_case(case: DemoCase, run_id: str) -> dict[str, Any]:
    email = f"style-e2e-{case.slug}-{run_id}@example.com"
    request_json(
        "POST",
        "/auth/register",
        {
            "email": email,
            "password": PASSWORD,
            "first_name": "Style",
            "last_name": case.slug.title(),
        },
    )
    tokens = request_json(
        "POST",
        "/auth/login",
        {"email": email, "password": PASSWORD},
    )
    token = tokens["access"]
    profile = request_json(
        "POST",
        "/styles/profiles",
        {"name": case.profile_name, "samples": case.samples},
        token=token,
    )
    complete, first_token_seconds, total_seconds = stream_generation(
        token,
        {
            "profile_id": profile["profile_id"],
            "topic": case.topic,
            "outline": case.outline,
            "keywords": case.keywords,
            "tone_slider": case.tone_slider,
        },
    )
    feedback = request_json(
        "POST",
        f"/styles/generations/{complete['generation_id']}/feedback",
        {"feedback": "up"},
        token=token,
    )
    history = request_json(
        "GET",
        f"/styles/generations?profile_id={profile['profile_id']}",
        token=token,
    )

    return {
        "email": email,
        "profile_id": profile["profile_id"],
        "sample_count": profile["sample_count"],
        "generation_id": complete["generation_id"],
        "first_token_seconds": round(first_token_seconds, 3),
        "total_seconds": round(total_seconds, 3),
        "quality": complete.get("quality", {}),
        "feedback": feedback.get("feedback"),
        "history_count": history.get("count"),
        "checks": {
            "three_samples": profile["sample_count"] == 3,
            "first_token_under_3s": first_token_seconds <= 3,
            "total_under_30s": total_seconds <= 30,
            "feedback_saved": feedback.get("feedback") == "up",
            "history_saved": history.get("count", 0) >= 1,
        },
    }


def main() -> int:
    if not PASSWORD:
        print("Set WENMO_E2E_PASSWORD to a disposable test password.", file=sys.stderr)
        return 2
    if len(PASSWORD) < 8:
        print("WENMO_E2E_PASSWORD must contain at least 8 characters.", file=sys.stderr)
        return 2

    validate_samples()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    report = {
        "base_url": BASE_URL,
        "run_id": run_id,
        "cases": [],
    }

    try:
        for case in CASES:
            print(f"Running {case.slug}...", file=sys.stderr)
            report["cases"].append(run_case(case, run_id))
    except RuntimeError as exc:
        report["error"] = str(exc)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    report["passed"] = all(
        all(result["checks"].values()) for result in report["cases"]
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
