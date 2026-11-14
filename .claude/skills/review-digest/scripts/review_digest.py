#!/usr/bin/env python3
"""
블로그·카페 후기 수집기 (최근 3개월 우선 → 최대 1년, 1년 넘은 글은 버림)

여러 검색어 × (blog, cafearticle)를 최신순으로 훑어서
  1) 중복 링크 제거
  2) 기간별로 나누기: 최근 3개월 / 3~12개월 / (카페) 날짜 미상
  3) 광고 의심 글 표시
  4) 여러 글에 반복해서 나오는 단어 집계 (공통 의견 찾기용)
결과를 마크다운(기본) 또는 JSON으로 출력한다.

사용 예:
    python3 review_digest.py "스페인 렌트카 후기" "스페인 렌트카 주의사항"
    python3 review_digest.py "알함브라 예약" --keywords 환불,취소,매진,여권
    python3 review_digest.py "세비야 숙소 후기" --types blog --format json

검색 API 자체는 ../../naver-search/scripts/naver_search.py 를 그대로 사용한다.
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

# 기존 naver-search 스킬의 검색 함수 재사용
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "naver-search" / "scripts"))
from naver_search import clean, load_env_file, search  # noqa: E402

RECENT_DAYS = 92     # 최근 3개월
MAX_DAYS = 365       # 이보다 오래된 글은 버림
PAGE = 100           # API 한 번에 최대 100건
MAX_START = 1000     # API 시작 위치 최대값

AD_WORDS = ["체험단", "원고료", "제공받아", "제공 받아", "소정의", "협찬", "광고",
            "할인코드", "쿠폰코드", "파트너스", "수수료를 제공",
            "할인 특가", "할인 프로모션", "최대 20% 할인", "보러가기", "쿠폰 적용가", "예약하러 가기"]
# 공통 단어 집계에서 뺄 흔한 말
STOP = set("""
여행 후기 꿀팁 정리 방법 추천 그리고 정말 너무 진짜 이번 오늘 저희 제가 우리 있어요 있습니다
합니다 했어요 했는데 하는 하고 해서 그냥 조금 많이 같아요 같은 위한 대한 있는 없는 하면 경우
때문에 이렇게 그래서 하지만 부분 사람 생각 다녀온 다녀왔습니다 가는 가는법 포스팅 블로그 카페
""".split())
WORD_RE = re.compile(r"[가-힣A-Za-z]{2,}")
# 검색어 중 '관련 글 판별'에 쓰지 않을 일반 단어
GENERIC = set("후기 꿀팁 주의 주의사항 정리 추천 방법 예약 팁 총정리 필수 비교 가격 비용 일정 코스 준비 준비물".split())
JOSA = ("에서는", "으로", "에서", "까지", "부터", "에는", "을", "를", "이", "가", "은", "는", "로", "에", "의", "도", "와", "과")


def stem(w):
    """'렌트카를' → '렌트카' 처럼 끝 조사 떼기 (너무 짧아지면 그대로)"""
    for j in JOSA:
        if w.endswith(j) and len(w) - len(j) >= 2:
            return w[: -len(j)]
    return w


def ymd(s):
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except (ValueError, TypeError):
        return None


def collect(query, type_, today, max_pages, sort, must):
    """페이지를 넘기며 수집. 최신순(date)이면 1년 넘은 글이 나오는 순간 멈춘다."""
    out = []
    for p in range(max_pages):
        start = 1 + p * PAGE
        if start > MAX_START:
            break
        items = search(query, type_, PAGE, start, sort).get("items", [])
        time.sleep(0.15)  # 호출 한도 배려
        stop = False
        for it in items:
            row = {k: clean(v) for k, v in it.items()}
            row["type"], row["query"] = type_, query
            text = row.get("title", "") + " " + row.get("description", "")
            if not all(m in text for m in must):
                continue  # 핵심 단어가 하나라도 빠지면 관련 없는 글로 보고 버림
            d = ymd(row.get("postdate", "")) if type_ == "blog" else None
            if d:
                age = (today - d).days
                if age > MAX_DAYS:
                    stop = sort == "date"  # 최신순이면 이후는 전부 더 오래된 글
                    continue
                row["age_days"] = age
                row["period"] = "recent" if age <= RECENT_DAYS else "year"
            else:
                # 카페 글은 API가 날짜를 안 준다 → 최신순 상위권만 '날짜 미상'으로 보관
                row["period"] = "nodate"
            out.append(row)
        if stop or len(items) < PAGE:
            break
    return out


def is_ad(r):
    text = r.get("title", "") + " " + r.get("description", "")
    return any(w in text for w in AD_WORDS)


def common_words(rows, query_words, top):
    """몇 개의 '서로 다른 글'에 나오는지(문서 빈도)로 센다."""
    c = Counter()
    for r in rows:
        words = {stem(w) for w in WORD_RE.findall(r.get("title", "") + " " + r.get("description", ""))}
        c.update(w for w in words if w not in STOP and w not in query_words)
    return c.most_common(top)


def keyword_hits(rows, keywords):
    res = {}
    for k in keywords:
        hit = [r for r in rows if k in r.get("title", "") + r.get("description", "")]
        res[k] = {"count": len(hit), "links": [r["link"] for r in hit[:5]]}
    return dict(sorted(res.items(), key=lambda x: -x[1]["count"]))


def main():
    p = argparse.ArgumentParser(description="블로그·카페 후기 수집 (최근 3개월 우선, 최대 1년)")
    p.add_argument("queries", nargs="+", help="검색어 여러 개 (도시+주제+후기/꿀팁/주의)")
    p.add_argument("--types", default="blog,cafearticle", help="blog,cafearticle 중 선택")
    p.add_argument("--pages", type=int, default=3, help="검색어·종류별 최대 페이지(1페이지=100건)")
    p.add_argument("--cafe-pages", type=int, default=1, help="카페는 날짜를 몰라서 최신순 몇 페이지만")
    p.add_argument("--must", default=None,
                   help="콤마 구분. 글에 꼭 있어야 하는 단어 (기본: 검색어에서 '후기/꿀팁' 같은 일반어 뺀 단어)")
    p.add_argument("--keywords", default="", help="콤마로 구분, 몇 개 글에 나오는지 확인할 단어")
    p.add_argument("--aspects", default="",
                   help="콤마 구분 세부 주제. '검색어+주제'로 다시 검색해서 글마다 그 주제 문장을 모은다 (본문 대신 요약문 여러 개)")
    p.add_argument("--aspect-show", type=int, default=12, help="주제별로 보여줄 문장 수")
    p.add_argument("--top", type=int, default=40, help="공통 단어 상위 몇 개")
    p.add_argument("--show", type=int, default=40, help="기간별로 출력할 글 수")
    p.add_argument("--format", "-f", default="markdown", choices=["markdown", "json"])
    p.add_argument("--save", help="전체 결과를 JSON 파일로 저장")
    a = p.parse_args()

    load_env_file()
    today = date.today()
    rows, by_link = [], {}

    def add(r, aspect=None):
        """같은 글이 다시 나오면 버리지 않고 '새 문장(요약문)'만 덧붙인다."""
        link = r.get("link")
        if link not in by_link:
            r["ad"] = is_ad(r)
            r["snips"] = {}
            by_link[link] = r
            rows.append(r)
        base = by_link[link]
        if aspect and r.get("description") and r["description"] != base.get("description"):
            base["snips"].setdefault(aspect, r["description"])
            base["ad"] = base["ad"] or is_ad(r)

    aspects = [x.strip() for x in a.aspects.split(",") if x.strip()]
    types = [x.strip() for x in a.types.split(",") if x.strip()]
    for q in a.queries:
        if a.must is not None:
            must = [m.strip() for m in a.must.split(",") if m.strip()]
        else:
            must = [w for w in q.split() if w not in GENERIC]
        for t in types:
            # 최신순 = 최근 글 확보, 정확도순 = 3~12개월 사이의 좋은 글 확보
            plan = [("date", a.cafe_pages if t == "cafearticle" else a.pages), ("sim", 1)]
            for sort, pages in plan:
                for r in collect(q, t, today, pages, sort, must):
                    add(r)
            # 세부 주제별 재검색: 요약문이 그 주제 문장 주변으로 바뀌어서 나온다
            for asp in aspects:
                for sort in ("date", "sim"):
                    for r in collect(f"{q} {asp}", t, today, 1, sort, must + [asp]):
                        if r.get("link") not in by_link:
                            r["snips"] = {}
                        add(r)
                        by_link[r["link"]]["snips"].setdefault(asp, r.get("description", ""))

    order = {"recent": 0, "year": 1, "nodate": 2}
    rows.sort(key=lambda r: (order[r["period"]], r["ad"], r.get("age_days", 0)))
    qwords = {stem(w) for w in WORD_RE.findall(" ".join(a.queries))}
    non_ad = [r for r in rows if not r["ad"]]
    result = {
        "today": today.isoformat(),
        "recent_cutoff": (today - timedelta(days=RECENT_DAYS)).isoformat(),
        "year_cutoff": (today - timedelta(days=MAX_DAYS)).isoformat(),
        "counts": {k: sum(r["period"] == k for r in rows) for k in order},
        "ads": sum(r["ad"] for r in rows),
        "common_words_recent": common_words([r for r in non_ad if r["period"] != "year"], qwords, a.top),
        "common_words_all": common_words(non_ad, qwords, a.top),
        "keywords": keyword_hits(non_ad, [k.strip() for k in a.keywords.split(",") if k.strip()]),
        "aspects": {asp: [{"link": r["link"], "title": r.get("title", ""), "period": r["period"],
                           "postdate": r.get("postdate", ""), "text": r["snips"][asp]}
                          for r in non_ad if asp in r.get("snips", {})] for asp in aspects},
        "items": rows,
    }

    if a.save:
        Path(a.save).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 저장: {a.save} ({len(rows)}건)", file=sys.stderr)
    if a.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    c = result["counts"]
    print(f"# 📚 후기 수집 결과 (기준일 {result['today']})")
    print(f"- 검색어: {', '.join(a.queries)}")
    print(f"- 🟢 최근 3개월({result['recent_cutoff']}~): {c['recent']}건 | 🟡 3~12개월: {c['year']}건"
          f" | ⚪ 카페(날짜 미상): {c['nodate']}건 | 🏷️ 광고 의심: {result['ads']}건 | 1년 초과는 제외\n")
    print("## 🔁 여러 글에 반복되는 단어 (광고 제외, 숫자 = 등장한 글 수)")
    print("- 최근 3개월+카페: " + ", ".join(f"{w}({n})" for w, n in result["common_words_recent"]))
    print("- 1년 전체: " + ", ".join(f"{w}({n})" for w, n in result["common_words_all"]) + "\n")
    if result["keywords"]:
        print("## 🎯 확인 키워드")
        for k, v in result["keywords"].items():
            print(f"- {k}: {v['count']}개 글 " + " ".join(v["links"][:3]))
        print()
    if result["aspects"]:
        print("## 🧩 주제별 문장 모음 (광고 제외, 최근 글 먼저)")
        for asp, lst in result["aspects"].items():
            print(f"### {asp} — {len(lst)}개 글")
            for x in lst[: a.aspect_show]:
                mark = {"recent": "🟢", "year": "🟡", "nodate": "⚪"}[x["period"]]
                print(f"- {mark} {x['text'][:200]} ({x['postdate'] or '카페'}) {x['link']}")
        print()
        rich = sorted([r for r in non_ad if len(r.get("snips", {})) >= 2], key=lambda r: -len(r["snips"]))
        if rich:
            print("## 📌 여러 주제를 다룬 알짜 글 (주제 수 많은 순)")
            for r in rich[:15]:
                print(f"- **{r.get('title', '')}** ({r.get('postdate') or '카페'}) "
                      f"[{', '.join(r['snips'])}] {r['link']}")
            print()
    titles = {"recent": "🟢 최근 3개월", "year": "🟡 3~12개월", "nodate": "⚪ 카페 (날짜 미상, 최신순 상위)"}
    for k, title in titles.items():
        part = [r for r in rows if r["period"] == k][: a.show]
        if not part:
            continue
        print(f"## {title}")
        for r in part:
            tag = " 🏷️광고의심" if r["ad"] else ""
            meta = r.get("postdate") or r.get("cafename", "")
            print(f"- **{r.get('title', '')}**{tag} ({meta}) {r.get('link', '')}")
            print(f"  - {r.get('description', '')[:160]}")
        print()


if __name__ == "__main__":
    main()
