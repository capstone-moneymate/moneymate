"""네이버 검색 API(뉴스) 샘플 20건을 받아 형식을 확인한다 (1주차 확인용).

실행: cd worker && python scripts/check_naver_news.py [--query 기준금리 --query 엔비디아]
필요: .env 의 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET (NAVER API HUB에서 발급)

제목·요약(description)만으로 카드뉴스·문제 재료가 충분한지 보려는 것이다. 판단은 사람이 docs/findings.md 에 적는다.
샘플은 레포 루트 logs/naver_news_sample.json 에 저장한다 (기사 내용이라 커밋하지 않는다. .gitignore 에 logs/ 추가를 A에게 요청함).

2026년 검색 API가 네이버 개발자센터 → NAVER API HUB(네이버 클라우드)로 이관됐다. 개발자센터 키는 쓸 수 없고
주소와 인증 헤더가 바뀌었다 (guide.ncloud-docs.com/docs/apihub-migration).
"""
import argparse
import html
import json
import os
import re
import statistics
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

import config  # noqa: E402,F401  레포 루트 .env 를 읽어 NAVER_CLIENT_ID·SECRET 을 환경변수로 올린다

ROOT = Path(__file__).resolve().parents[2]
API_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
# 감시 키워드 3종(종목·섹터·거시) 예시
DEFAULT_QUERIES = ["엔비디아", "반도체", "기준금리"]
TAG_RE = re.compile(r"<[^>]+>")


def clean(text: str) -> str:
    """검색어 강조 태그(<b>)와 HTML 엔티티를 지운다."""
    return html.unescape(TAG_RE.sub("", text)).strip()


def search(query: str, display: int) -> dict:
    resp = requests.get(
        API_URL,
        params={"query": query, "display": display, "sort": "date"},
        headers={
            "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
            "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
        },
        timeout=10,
    )
    if not resp.ok:
        print(f"[{query}] HTTP {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", action="append", help="검색어 (여러 번 지정 가능)")
    parser.add_argument("--total", type=int, default=20, help="모을 기사 수")
    args = parser.parse_args()

    if not os.environ.get("NAVER_CLIENT_ID") or not os.environ.get("NAVER_CLIENT_SECRET"):
        print("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET이 .env에 없습니다.", file=sys.stderr)
        return 1

    queries = args.query or DEFAULT_QUERIES
    per_query = -(-args.total // len(queries))  # 올림

    items = []
    for query in queries:
        data = search(query, per_query)
        print(f"[{query}] 전체 {data['total']:,}건 중 {len(data['items'])}건")
        for item in data["items"]:
            items.append(
                {
                    "query": query,
                    "title": clean(item["title"]),
                    "description": clean(item["description"]),
                    "originallink": item.get("originallink", ""),
                    "link": item["link"],
                    "pubDate": item["pubDate"],
                }
            )
    items = items[: args.total]

    out = ROOT / "logs" / "naver_news_sample.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    title_lens = [len(i["title"]) for i in items]
    desc_lens = [len(i["description"]) for i in items]
    no_original = sum(1 for i in items if not i["originallink"])
    naver_links = sum(1 for i in items if "n.news.naver.com" in i["link"])

    print()
    print(f"저장: {out.relative_to(ROOT)} ({len(items)}건)")
    print(f"제목 길이   평균 {statistics.mean(title_lens):.0f}자 (최소 {min(title_lens)}, 최대 {max(title_lens)})")
    print(f"요약 길이   평균 {statistics.mean(desc_lens):.0f}자 (최소 {min(desc_lens)}, 최대 {max(desc_lens)})")
    print(f"원문 링크 없음 {no_original}건, 네이버 뉴스 링크 {naver_links}건")
    print("언론사 필드는 응답에 없음 → originallink 도메인으로 추정해야 함")
    print()
    for i in items[:5]:
        print(f"- {i['title']}\n  {i['description']}\n  {i['pubDate']} | {i['originallink'] or i['link']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
