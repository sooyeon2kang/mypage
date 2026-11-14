#!/usr/bin/env python3
"""
구글 지도 평점 조회 (Google Places API (New) - Text Search)

장소 이름으로 검색해서 평점 / 후기 수 / 주소 / 구글지도 링크만 가져온다.
(후기 본문은 가져오지 않음 → 한국인 후기는 네이버 review_digest.py 담당)

사용 예:
    python3 google_rating.py "알함브라 궁전" "사그라다 파밀리아"
    python3 google_rating.py "그라나다 타파스 맛집" -n 5
    python3 google_rating.py "Bar Dos de Mayo Sevilla" --format json

인증: 환경변수 또는 .env 의 GOOGLE_MAPS_API_KEY
      (클라우드 세션에서는 네트워크 프록시가 키를 대신 넣어줄 수 있음)
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://places.googleapis.com/v1/places:searchText"
# 필요한 항목만 요청 (요청 항목 수에 따라 요금 등급이 달라짐)
FIELDS = ",".join([
    "places.displayName", "places.rating", "places.userRatingCount",
    "places.formattedAddress", "places.googleMapsUri",
])


def load_env_file():
    here = Path.cwd().resolve()
    for d in [here, *here.parents]:
        env = d / ".env"
        if env.is_file():
            for line in env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


def text_search(query, n, lang):
    # 키가 없으면 자리표시 값을 보냄 → 클라우드 프록시가 저장된 실제 키로 바꿔 넣음
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "proxy-injected")
    body = json.dumps({"textQuery": query, "languageCode": lang, "pageSize": n}).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": FIELDS,
    })
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8")).get("places", [])
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            msg = e.read().decode("utf-8", "replace")
            hint = {400: "요청 형식 또는 API 키 오류", 403: "키 권한 없음 / Places API (New) 미사용 설정 / 결제 미등록"}
            sys.exit(f"❌ 구글 API 오류 {e.code} ({hint.get(e.code, '')}): {msg[:300]}")
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            sys.exit(f"❌ 네트워크 오류: {getattr(e, 'reason', e)} (places.googleapis.com 접속 허용 여부 확인)")


def main():
    p = argparse.ArgumentParser(description="구글 지도 평점 조회")
    p.add_argument("queries", nargs="+", help="장소 이름 (도시명을 같이 쓰면 정확해짐)")
    p.add_argument("-n", type=int, default=1, help="검색어당 결과 수 (기본 1 = 가장 잘 맞는 장소)")
    p.add_argument("--lang", default="ko", help="장소 이름·주소 언어 (기본 ko)")
    p.add_argument("--format", "-f", default="markdown", choices=["markdown", "json"])
    a = p.parse_args()
    load_env_file()

    out = []
    for q in a.queries:
        for pl in text_search(q, a.n, a.lang):
            out.append({
                "query": q,
                "name": pl.get("displayName", {}).get("text", ""),
                "rating": pl.get("rating"),
                "reviews": pl.get("userRatingCount"),
                "address": pl.get("formattedAddress", ""),
                "url": pl.get("googleMapsUri", ""),
            })

    if a.format == "json":
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    print("| 검색어 | 장소 | ⭐ 평점 | 후기 수 | 주소 | 지도 |")
    print("|---|---|---|---|---|---|")
    for r in out:
        rating = f"{r['rating']:.1f}" if r["rating"] is not None else "-"
        cnt = f"{r['reviews']:,}" if r["reviews"] else "-"
        print(f"| {r['query']} | {r['name']} | {rating} | {cnt} | {r['address']} | [링크]({r['url']}) |")
    if not out:
        print("(검색 결과 없음 - 도시명을 붙이거나 영어/현지어 이름으로 다시 시도)")


if __name__ == "__main__":
    main()
