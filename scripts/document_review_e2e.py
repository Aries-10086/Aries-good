#!/usr/bin/env python3
"""Run the document review path against a deployed Wenmo API.

Creates a disposable account, submits sample contract text, polls the async
task, and validates the returned report structure.
Only run this against a development or staging environment.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = os.getenv("WENMO_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_URL = f"{BASE_URL}/api/v1"
PASSWORD = os.getenv("WENMO_E2E_PASSWORD", "")
POLL_INTERVAL = float(os.getenv("WENMO_E2E_POLL_SECONDS", "2"))
POLL_TIMEOUT = float(os.getenv("WENMO_E2E_TIMEOUT_SECONDS", "90"))

SAMPLE_TEXT = """服务协议

一、费用条款
1. 用户已支付的服务费用在任何情况下均不退还。
2. 平台有权根据运营需要单方面调整收费标准，无需另行通知。

二、责任限制
3. 因系统故障、网络中断等原因造成的损失，平台不承担任何赔偿责任。
4. 用户理解并同意，平台对第三方链接内容不作任何保证。

三、争议解决
5. 本协议适用平台所在地法律；争议由平台所在地法院专属管辖。
"""


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


def poll_review(token: str, task_id: str) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    deadline = started + POLL_TIMEOUT
    last_status = ""

    while time.perf_counter() < deadline:
        payload = request_json("GET", f"/documents/review/{task_id}", token=token)
        last_status = payload.get("status", "")
        if last_status == "success":
            return payload, time.perf_counter() - started
        if last_status == "failed":
            raise RuntimeError(payload.get("error") or "document review task failed")
        time.sleep(POLL_INTERVAL)

    raise RuntimeError(
        f"task {task_id} did not finish within {POLL_TIMEOUT}s (last status={last_status})"
    )


def main() -> int:
    if not PASSWORD:
        print("Set WENMO_E2E_PASSWORD to a disposable test password.", file=sys.stderr)
        return 2
    if len(PASSWORD) < 8:
        print("WENMO_E2E_PASSWORD must contain at least 8 characters.", file=sys.stderr)
        return 2

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    email = f"doc-review-e2e-{run_id}@example.com"
    report: dict[str, Any] = {
        "base_url": BASE_URL,
        "run_id": run_id,
        "email": email,
    }

    try:
        request_json(
            "POST",
            "/auth/register",
            {
                "email": email,
                "password": PASSWORD,
                "first_name": "Doc",
                "last_name": "Review",
            },
        )
        tokens = request_json(
            "POST",
            "/auth/login",
            {"email": email, "password": PASSWORD},
        )
        token = tokens["access"]

        submit_started = time.perf_counter()
        submitted = request_json(
            "POST",
            "/documents/review",
            {"text": SAMPLE_TEXT, "doc_type": "contract"},
            token=token,
        )
        task_id = submitted["task_id"]
        review_id = submitted["review_id"]
        task_payload, elapsed = poll_review(token, task_id)
        detail = request_json("GET", f"/documents/reviews/{review_id}", token=token)
        history = request_json("GET", "/documents/reviews", token=token)

        review = task_payload.get("review") or detail
        risks = review.get("risks") or []
        report_text = review.get("report") or ""

        report.update(
            {
                "task_id": task_id,
                "review_id": review_id,
                "elapsed_seconds": round(elapsed, 3),
                "submit_seconds": round(time.perf_counter() - submit_started, 3),
                "risk_count": len(risks),
                "history_count": history.get("count", 0),
                "checks": {
                    "task_success": task_payload.get("status") == "success",
                    "has_report": bool(report_text.strip()),
                    "has_risks": len(risks) >= 1,
                    "risk_has_quote": all(r.get("quote") for r in risks),
                    "under_60s": elapsed <= 60,
                    "detail_matches": detail.get("id") == review_id,
                    "history_saved": history.get("count", 0) >= 1,
                },
            }
        )
    except RuntimeError as exc:
        report["error"] = str(exc)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    report["passed"] = all(report["checks"].values())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
