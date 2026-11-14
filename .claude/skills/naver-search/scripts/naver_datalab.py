#!/usr/bin/env python3
"""
네이버 데이터랩(검색어 트렌드 / 쇼핑인사이트) + 블로그 키워드 경쟁도 조회
표준 라이브러리만 사용 → 별도 설치 불필요

사용 예:
  # 1) 검색어 트렌드: 키워드별 검색량 '상대 지수'(가장 많은 시점 = 100)
  python3 naver_datalab.py trend "스페인 신혼여행" "포르투갈 신혼여행" --months 12
  # 같은 뜻의 키워드를 한 묶음으로:  "스페인신혼여행=스페인 신혼여행,스페인 허니문"
  python3 naver_datalab.py trend "스페인신혼여행=스페인 신혼여행,스페인 허니문" --unit week

  # 2) 쇼핑인사이트: 쇼핑 분야(카테고리) 클릭 추이  (가구/인테리어 = 50000004)
  python3 naver_datalab.py shopping --category "가구/인테리어=50000004" --months 12

  # 2-1) 쇼핑 키워드 비교: 분야 안에서 키워드별 클릭 추이
  python3 naver_datalab.py shopkw --category 50000004 "패브릭 소파" "가죽 소파" "모듈 소파"

  # 3) 블로그 키워드 경쟁도: 블로그 글이 몇 개나 있는지 (적을수록 경쟁 낮음)
  python3 naver_datalab.py compete "바르셀로나 신혼여행" "세비야 맛집" "그라나다 알함브라 예약"

공통 옵션: --csv 결과.csv  (엑셀에서 바로 열림)
인증: naver_search.py 와 동일 (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET, .env 가능)
"""
import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naver_search import load_env_file, search  # noqa: E402

HUB = "https://naverapihub.apigw.ntruss.com"
URLS = {
    # (HUB 주소, 기존 개발자센터 주소)
    "trend": (HUB + "/search-trend/v1/search", "https://openapi.naver.com/v1/datalab/search"),
    "shopping": (HUB + "/shopping/v1/categories", "https://openapi.naver.com/v1/datalab/shopping/categories"),
    "shopkw": (HUB + "/shopping/v1/category/keywords",
               "https://openapi.naver.com/v1/datalab/shopping/category/keywords"),
}


def is_legacy():
    return os.environ.get("NAVER_API_LEGACY", "").strip() in ("1", "true", "yes")


def post(kind, body):
    cid, secret = os.environ.get("NAVER_CLIENT_ID"), os.environ.get("NAVER_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("❌ NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 없습니다. (README 참고)")
    legacy = is_legacy()
    url = URLS[kind][1 if legacy else 0]
    headers = (
        {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret}
        if legacy
        else {"X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": secret}
    )
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"❌ API 오류 {e.code} ({url}): {e.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"❌ 네트워크 오류: {e.reason}")


def parse_groups(items):
    """'이름=키1,키2' 또는 '키워드' → [(이름, [키워드들])]"""
    groups = []
    for it in items:
        name, _, rest = it.partition("=")
        words = [w.strip() for w in (rest or name).split(",") if w.strip()]
        groups.append((name.strip(), words))
    return groups


def period(a):
    end = date.fromisoformat(a.end) if a.end else date.today() - timedelta(days=1)
    start = date.fromisoformat(a.start) if a.start else end - timedelta(days=30 * a.months)
    return start.isoformat(), end.isoformat()


def common_filters(a, body):
    if a.device:
        body["device"] = a.device
    if a.gender:
        body["gender"] = a.gender
    if a.ages:
        body["ages"] = a.ages.split(",")
    return body


def print_series(data, csv_path):
    """결과(그룹별 기간·지수)를 표로 출력 + CSV 저장"""
    results = data.get("results", [])
    names = [r["title"] for r in results]
    table = {}
    for r in results:
        for d in r.get("data", []):
            table.setdefault(d["period"], {})[r["title"]] = d["ratio"]
    rows = [[p] + [round(table[p].get(n, 0), 1) for n in names] for p in sorted(table)]

    print("| 기간 | " + " | ".join(names) + " |")
    print("|---|" + "---|" * len(names))
    for row in rows:
        print("| " + " | ".join(str(x) for x in row) + " |")
    # 요약: 그룹별 평균 / 최고 시점
    print()
    for i, n in enumerate(names, 1):
        vals = [(row[0], row[i]) for row in rows]
        if vals:
            peak = max(vals, key=lambda x: x[1])
            avg = sum(v for _, v in vals) / len(vals)
            print(f"- **{n}**: 평균 {avg:.1f} / 최고 {peak[1]} ({peak[0]})")
    print("\n※ 지수는 '조회 기간 중 가장 많이 검색된 시점 = 100' 기준의 상대값이에요 (실제 검색 횟수 아님)")

    if csv_path:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as fp:
            w = csv.writer(fp)
            w.writerow(["기간"] + names)
            w.writerows(rows)
        print(f"✅ CSV 저장: {csv_path}", file=sys.stderr)


def cmd_trend(a):
    s, e = period(a)
    groups = parse_groups(a.keywords)
    if len(groups) > 5:
        sys.exit("❌ 키워드 묶음은 한 번에 최대 5개까지예요")
    body = {"startDate": s, "endDate": e, "timeUnit": a.unit,
            "keywordGroups": [{"groupName": n, "keywords": w} for n, w in groups]}
    print(f"## 📈 검색어 트렌드 ({s} ~ {e}, {a.unit})\n")
    print_series(post("trend", common_filters(a, body)), a.csv)


def cmd_shopping(a):
    s, e = period(a)
    cats = parse_groups(a.category)
    body = {"startDate": s, "endDate": e, "timeUnit": a.unit,
            "category": [{"name": n, "param": w} for n, w in cats]}
    print(f"## 🛒 쇼핑인사이트 분야별 클릭 추이 ({s} ~ {e}, {a.unit})\n")
    print_series(post("shopping", common_filters(a, body)), a.csv)


def cmd_shopkw(a):
    s, e = period(a)
    groups = parse_groups(a.keywords)
    body = {"startDate": s, "endDate": e, "timeUnit": a.unit, "category": a.category,
            "keyword": [{"name": n, "param": w} for n, w in groups]}
    print(f"## 🛋️ 쇼핑 키워드 클릭 추이 (분야 {a.category}, {s} ~ {e}, {a.unit})\n")
    print_series(post("shopkw", common_filters(a, body)), a.csv)


def cmd_compete(a):
    rows = []
    for kw in a.keywords:
        res = search(kw, "blog", display=1)
        rows.append((kw, res.get("total", 0)))
    rows.sort(key=lambda x: x[1])
    print("## ✍️ 블로그 키워드 경쟁도 (블로그 글 수가 적을수록 경쟁 낮음)\n")
    print("| 키워드 | 블로그 글 수 |")
    print("|---|---|")
    for kw, n in rows:
        print(f"| {kw} | {n:,} |")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as fp:
            w = csv.writer(fp)
            w.writerow(["키워드", "블로그 글 수"])
            w.writerows(rows)
        print(f"✅ CSV 저장: {a.csv}", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="네이버 데이터랩 / 키워드 도구")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_period(sp):
        sp.add_argument("--months", type=int, default=12, help="최근 몇 개월 (기본 12)")
        sp.add_argument("--start", help="시작일 YYYY-MM-DD (2016-01-01 이후)")
        sp.add_argument("--end", help="종료일 YYYY-MM-DD (기본 어제)")
        sp.add_argument("--unit", default="month", choices=["date", "week", "month"], help="집계 단위")
        sp.add_argument("--device", choices=["pc", "mo"], help="기기 (기본 전체)")
        sp.add_argument("--gender", choices=["m", "f"], help="성별 (기본 전체)")
        sp.add_argument("--ages", help="연령대 코드, 예: 3,4 (3=25~29세, 4=30~34세)")
        sp.add_argument("--csv", help="CSV로 저장")

    t = sub.add_parser("trend", help="검색어 트렌드")
    t.add_argument("keywords", nargs="+", help="키워드 또는 '묶음이름=키워드1,키워드2' (최대 5개)")
    add_period(t)
    t.set_defaults(func=cmd_trend)

    s = sub.add_parser("shopping", help="쇼핑인사이트 분야별 추이")
    s.add_argument("--category", nargs="+", required=True, help="'이름=카테고리ID' (최대 3개)")
    add_period(s)
    s.set_defaults(func=cmd_shopping)

    k = sub.add_parser("shopkw", help="쇼핑 분야 안에서 키워드별 클릭 추이")
    k.add_argument("--category", required=True, help="카테고리 ID 1개 (예: 50000004 가구/인테리어)")
    k.add_argument("keywords", nargs="+", help="키워드 또는 '이름=키워드1,키워드2' (최대 5개)")
    add_period(k)
    k.set_defaults(func=cmd_shopkw)

    c = sub.add_parser("compete", help="블로그 키워드 경쟁도")
    c.add_argument("keywords", nargs="+")
    c.add_argument("--csv")
    c.set_defaults(func=cmd_compete)

    a = p.parse_args()
    load_env_file()
    a.func(a)


if __name__ == "__main__":
    main()
