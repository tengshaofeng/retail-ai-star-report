#!/usr/bin/env python3
"""Build and email a weekly GitHub Star-growth report for retail multimodal AI."""

from __future__ import annotations

import html
import json
import os
import smtplib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.message import EmailMessage
from pathlib import Path


SEARCH_QUERIES = [
    '"multimodal" retail in:name,description,readme',
    '"vision language" retail in:name,description,readme',
    '"store inspection" AI in:name,description,readme',
    '"retail inspection" vision in:name,description,readme',
    '"retail shelf" detection in:name,description,readme',
    '"product recognition" retail in:name,description,readme',
    '"e-commerce" multimodal in:name,description,readme',
    '"ecommerce understanding" in:name,description,readme',
    '"product understanding" vision in:name,description,readme',
    '"retail VLM" in:name,description,readme',
]

DATA_DIR = Path(__file__).resolve().parent / "data"
RECIPIENT = os.getenv("REPORT_RECIPIENT", "307149416@qq.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
MIN_STARS = int(os.getenv("MIN_STARS", "5"))
MAX_PER_QUERY = int(os.getenv("MAX_PER_QUERY", "100"))


@dataclass(frozen=True)
class RankedRepo:
    full_name: str
    url: str
    description: str
    stars: int
    previous_stars: int
    growth: int
    language: str
    topics: tuple[str, ...]


def github_json(url: str, token: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "retail-ai-star-report",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in {403, 429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API error {exc.code}: {detail}") from exc
    raise RuntimeError("GitHub API request failed after retries")


def discover_repositories(token: str) -> dict[str, dict]:
    repositories: dict[str, dict] = {}
    for base_query in SEARCH_QUERIES:
        query = f"{base_query} stars:>={MIN_STARS} archived:false fork:false"
        params = urllib.parse.urlencode(
            {"q": query, "sort": "updated", "order": "desc", "per_page": MAX_PER_QUERY}
        )
        payload = github_json(f"https://api.github.com/search/repositories?{params}", token)
        for item in payload.get("items", []):
            repositories[item["full_name"]] = {
                "full_name": item["full_name"],
                "url": item["html_url"],
                "description": item.get("description") or "",
                "stars": int(item["stargazers_count"]),
                "language": item.get("language") or "",
                "topics": item.get("topics") or [],
            }
        time.sleep(1)
    return repositories


def latest_snapshot(before: Path | None = None) -> tuple[Path | None, dict[str, dict]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    candidates = sorted(DATA_DIR.glob("*.json"), reverse=True)
    if before is not None:
        candidates = [path for path in candidates if path < before]
    if not candidates:
        return None, {}
    path = candidates[0]
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return path, payload.get("repositories", {})


def rank_growth(current: dict[str, dict], previous: dict[str, dict]) -> list[RankedRepo]:
    ranked = []
    for name, repo in current.items():
        if name not in previous:
            continue
        previous_stars = int(previous[name]["stars"])
        stars = int(repo["stars"])
        ranked.append(
            RankedRepo(
                full_name=name,
                url=repo["url"],
                description=repo["description"],
                stars=stars,
                previous_stars=previous_stars,
                growth=max(0, stars - previous_stars),
                language=repo["language"],
                topics=tuple(repo["topics"]),
            )
        )
    return sorted(ranked, key=lambda repo: (repo.growth, repo.stars), reverse=True)[:10]


def write_snapshot(repositories: dict[str, dict]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{date.today().isoformat()}.json"
    payload = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "query_count": len(SEARCH_QUERIES),
        "repository_count": len(repositories),
        "repositories": dict(sorted(repositories.items())),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def render_html(
    ranked: list[RankedRepo],
    current_count: int,
    previous_path: Path | None,
) -> str:
    if previous_path is None:
        return f"""
        <h2>Retail AI GitHub Star 周报：基线已建立</h2>
        <p>本次共发现并记录 {current_count} 个候选项目。</p>
        <p>由于这是首次快照，尚无上周数据可计算增长量；下周开始发送 Top 10 排名。</p>
        """

    rows = []
    for index, repo in enumerate(ranked, 1):
        description = html.escape(repo.description or "暂无简介")
        language = html.escape(repo.language or "未标注")
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f'<td><a href="{html.escape(repo.url)}">{html.escape(repo.full_name)}</a>'
            f"<br><small>{description}</small></td>"
            f"<td><strong>+{repo.growth}</strong></td>"
            f"<td>{repo.stars}</td>"
            f"<td>{language}</td>"
            "</tr>"
        )
    table = "\n".join(rows) or '<tr><td colspan="5">本周没有可比较的项目。</td></tr>'
    return f"""
    <h2>Retail AI GitHub Star 周增长 Top 10</h2>
    <p>候选项目：{current_count} 个；对比基线：{html.escape(previous_path.name)}。</p>
    <table style="border-collapse:collapse;width:100%" border="1" cellpadding="8">
      <thead><tr><th>#</th><th>项目</th><th>Star 增长</th><th>当前 Star</th><th>语言</th></tr></thead>
      <tbody>{table}</tbody>
    </table>
    <p><small>范围：多模态大模型、商超/门店巡检、零售视觉、货架与商品识别、电商理解。
    排名为本次与上次周度快照之间的 Star 差值。</small></p>
    """


def send_email(subject: str, body_html: str) -> None:
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_APP_PASSWORD"]
    message = EmailMessage()
    message["From"] = username
    message["To"] = RECIPIENT
    message["Subject"] = subject
    message.set_content("此报告包含 HTML 内容，请使用支持 HTML 的邮件客户端查看。")
    message.add_alternative(body_html, subtype="html")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as client:
        client.login(username, password)
        client.send_message(message)


def main() -> int:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2

    current = discover_repositories(token)
    snapshot_path = DATA_DIR / f"{date.today().isoformat()}.json"
    previous_path, previous = latest_snapshot(before=snapshot_path)
    ranked = rank_growth(current, previous)
    write_snapshot(current)
    report = render_html(ranked, len(current), previous_path)
    subject = (
        f"Retail AI GitHub Star 周报 | {date.today():%Y-%m-%d}"
        if previous_path
        else f"Retail AI GitHub Star 追踪基线 | {date.today():%Y-%m-%d}"
    )

    if os.getenv("DRY_RUN") == "1":
        print(report)
    else:
        send_email(subject, report)
        print(f"Report sent to {RECIPIENT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
