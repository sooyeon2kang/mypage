#!/usr/bin/env python3
"""
네이버 검색 Open API 호출 스크립트 (표준 라이브러리만 사용 → 별도 설치 불필요)

사용 예:
    python3 naver_search.py "주차장 운영 수익" --type news --display 10 --sort date
    python3 naver_search.py "강남 주차장" --type local --format json
    python3 naver_search.py "주차 관제 시스템" --type blog --csv result.csv

인증 정보(둘 중 하나):
    1) 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET
    2) 저장소 루트의 .env 파일 (NAVER_CLIENT_ID=..., NAVER_CLIENT_SECRET=...)
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://openapi.naver.com/v1/search/{type}.json"

# 검색 종류 → 출력할 주요 필드
TYPES = {
    "blog": ["title", "bloggername", "postdate", "link", "description"],
    "news": ["title", "pubDate", "originallink", "link", "description"],
    "webkr": ["title", "link", "description"],
    "local": ["title", "category", "address", "roadAddress", "telephone", "link"],
    "shop": ["title", "lprice", "hprice", "mallName", "brand", "category1", "link"],
    "cafearticle": ["title", "cafename", "link", "description"],
    "kin": ["title", "link", "description"],
    "book": ["title", "author", "publisher", "pubdate", "discount", "link"],
    "encyc": ["title", "link", "description"],
    "image": ["title", "link", "thumbnail", "sizewidth", "sizeheight"],
}
# 정렬 옵션: 대부분 sim(정확도)/date(최신), 쇼핑은 asc/dsc(가격순) 추가
SORTS = ["sim", "date", "asc", "dsc", "random", "comment"]
TAG_RE = re.compile(r"<[^>]+>")


def load_env_file() -> None:
    """현재 폴더 → 상위 폴더 순으로 .env 파일을 찾아 환경변수로 등록"""
    here = Path.cwd().resolve()
    for d in [here, *here.parents]:
        env = d / ".env"
        if env.is_file():
            for line in env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


def clean(text) -> str:
    """<b>태그, &quot; 같은 HTML 흔적 제거"""
    if text is None:
        return ""
    return html.unescape(TAG_RE.sub("", str(text))).strip()


def search(query, type_="blog", display=10, start=1, sort="sim"):
    cid = os.environ.get("NAVER_CLIENT_ID")
    secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit(
            "❌ NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 없습니다.\n"
            "   https://developers.naver.com 에서 애플리케이션을 등록하고(검색 API 선택)\n"
            "   환경변수 또는 .env 파일에 넣어주세요."
        )
    params = {"query": query, "display": display, "start": start}
    # 지역(local)은 random/comment 정렬만, 나머지는 sim/date/asc/dsc만 허용
    if (type_ == "local") == (sort in ("random", "comment")):
        params["sort"] = sort
    url = API_BASE.format(type=type_) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        sys.exit(f"❌ API 오류 {e.code}: {body}")
    except urllib.error.URLError as e:
        sys.exit(f"❌ 네트워크 오류: {e.reason} (openapi.naver.com 접속 허용 여부 확인)")


def main():
    p = argparse.ArgumentParser(description="네이버 검색 Open API")
    p.add_argument("query", help="검색어")
    p.add_argument("--type", "-t", default="blog", choices=TYPES.keys(), help="검색 종류")
    p.add_argument("--display", "-n", type=int, default=10, help="결과 개수 (최대 100, local은 5)")
    p.add_argument("--start", type=int, default=1, help="시작 위치 (최대 1000)")
    p.add_argument("--sort", "-s", default="sim", choices=SORTS, help="정렬")
    p.add_argument("--format", "-f", default="markdown", choices=["markdown", "json"], help="출력 형식")
    p.add_argument("--csv", help="결과를 CSV로 저장 (엑셀에서 바로 열림, UTF-8 BOM)")
    a = p.parse_args()

    load_env_file()
    data = search(a.query, a.type, a.display, a.start, a.sort)
    fields = TYPES[a.type]
    items = [{f: clean(it.get(f)) for f in fields} for it in data.get("items", [])]

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as fp:
            w = csv.DictWriter(fp, fieldnames=fields)
            w.writeheader()
            w.writerows(items)
        print(f"✅ CSV 저장: {a.csv} ({len(items)}건)", file=sys.stderr)

    if a.format == "json":
        print(json.dumps({"total": data.get("total"), "items": items}, ensure_ascii=False, indent=2))
        return

    print(f"## 🔎 '{a.query}' 네이버 {a.type} 검색 (전체 {data.get('total', 0):,}건 중 {len(items)}건)\n")
    for i, it in enumerate(items, a.start):
        print(f"{i}. **{it.get('title', '')}**")
        for f in fields[1:]:
            if it.get(f):
                print(f"   - {f}: {it[f]}")
        print()


if __name__ == "__main__":
    main()
