#!/usr/bin/env python3
"""
최신 환율 조회 + 해외결제 비교 계산 (Frankfurter API, 유럽중앙은행 기준 · 키 필요 없음)

사용 예:
    python3 fx.py rate                         # 오늘 EUR, USD, JPY → KRW
    python3 fx.py rate EUR GBP                 # 원하는 통화만
    python3 fx.py convert 807 EUR              # 807유로는 원화로 얼마?
    python3 fx.py compare --krw 1181259 --foreign 807 --cur EUR --cashback 20000
                                               # 원화 결제 vs 외화 카드결제(+수수료, -캐시백) 비교
    python3 fx.py trend EUR --days 30          # 최근 30일 추이 (최고/최저/평균)

주의
- 유럽중앙은행 기준 환율은 영업일 하루 1번(중앙유럽 기준 16시쯤) 갱신된다. 주말·공휴일에는 직전 영업일 값.
- 카드사 실제 적용 환율은 이보다 높다(은행 송금 환율 + 국제브랜드/카드사 수수료) → compare의 --fee로 반영.
"""
import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = "https://api.frankfurter.dev/v1"
# 카드 해외결제 추가 비용 어림값: 송금환율 가산(~1.0%) + 국제브랜드(~1.0~1.1%) + 카드사(~0.2~0.3%)
FEE_LOW, FEE_HIGH = 1.4, 2.4


def get(path, params=None):
    url = f"{BASE}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "fx-skill"}), timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            sys.exit(f"❌ 환율 조회 실패: {getattr(e, 'reason', e)} (api.frankfurter.dev 접속 허용 여부 확인)")


def krw_per(cur):
    """1 외화 = ? 원 (최신 영업일)"""
    d = get("latest", {"base": cur.upper(), "symbols": "KRW"})
    return d["rates"]["KRW"], d["date"]


def won(n):
    return f"{round(n):,}원"


def cmd_rate(a):
    curs = [c.upper() for c in (a.currencies or ["EUR", "USD", "JPY"])]
    print("| 통화 | 1단위 = 원화 | 기준일 |\n|---|---|---|")
    for c in curs:
        r, d = krw_per(c)
        unit = 100 if c == "JPY" else 1
        print(f"| {c}{' (100엔)' if unit == 100 else ''} | {r * unit:,.2f}원 | {d} |")
    print("\n※ 유럽중앙은행 기준(매매기준율과 비슷). 카드 결제는 여기에 약 1.4~2.4% 더 붙어요.")


def cmd_convert(a):
    r, d = krw_per(a.cur)
    base = a.amount * r
    print(f"💱 {a.amount:,.2f} {a.cur.upper()} = {won(base)}  (1 {a.cur.upper()} = {r:,.2f}원, {d} 기준)")
    print(f"💳 카드 결제 예상: {won(base * (1 + FEE_LOW / 100))} ~ {won(base * (1 + FEE_HIGH / 100))}"
          f"  (해외 수수료 등 +{FEE_LOW}~{FEE_HIGH}%)")


def cmd_compare(a):
    r, d = krw_per(a.cur)
    cur = a.cur.upper()
    fees = [a.fee] if a.fee is not None else [FEE_LOW, FEE_HIGH]
    krw_total = a.krw * (1 + a.krw_fee / 100)
    print(f"# 💱 결제 통화 비교 (1 {cur} = {r:,.2f}원, {d} 기준)\n")
    print("| 방법 | 계산 | 실제 부담 | 원화 대비 |\n|---|---|---|---|")
    note = f" + 수수료 {a.krw_fee}%" if a.krw_fee else ""
    print(f"| 🇰🇷 원화 결제 | {a.krw:,}원{note} | **{won(krw_total)}** | – |")
    for f in fees:
        v = a.foreign * r * (1 + f / 100) - a.cashback
        cb = f" − 캐시백 {a.cashback:,}원" if a.cashback else ""
        diff = v - krw_total
        print(f"| 💳 {cur} 카드결제 (+{f}%) | {a.foreign:,} × {r:,.2f} × {1 + f / 100:.3f}{cb} | **{won(v)}** | "
              f"{'+' if diff >= 0 else '−'}{won(abs(diff))} |")
    # 손익분기 환율: 이 환율보다 낮아지면 외화 결제가 유리
    print()
    for f in fees:
        be = (krw_total + a.cashback) / (a.foreign * (1 + f / 100))
        print(f"📉 수수료 {f}% 기준 손익분기 환율: 1 {cur} = {be:,.2f}원 "
              f"→ 지금({r:,.2f}원)은 {'원화' if r > be else cur} 결제가 유리")
    print("\n※ 카드 결제 환율은 결제일이 아니라 매입일(보통 승인 2~3일 뒤)에 확정돼요.")


def cmd_trend(a):
    cur = a.cur.upper()
    start = (date.today() - timedelta(days=a.days)).isoformat()
    d = get(f"{start}..", {"base": cur, "symbols": "KRW"})
    series = sorted((k, v["KRW"]) for k, v in d["rates"].items())
    vals = [v for _, v in series]
    hi = max(series, key=lambda x: x[1])
    lo = min(series, key=lambda x: x[1])
    print(f"# 📈 {cur}/KRW 최근 {a.days}일 ({series[0][0]} ~ {series[-1][0]})")
    print(f"- 최신: {vals[-1]:,.2f}원 | 평균: {statistics.mean(vals):,.2f}원")
    print(f"- 최고: {hi[1]:,.2f}원 ({hi[0]}) | 최저: {lo[1]:,.2f}원 ({lo[0]})")
    chg = (vals[-1] / vals[0] - 1) * 100
    print(f"- 기간 변화: {chg:+.2f}% ({vals[0]:,.2f} → {vals[-1]:,.2f})")
    if a.table:
        print("\n| 날짜 | 원화 |\n|---|---|")
        for k, v in series:
            print(f"| {k} | {v:,.2f} |")


def main():
    p = argparse.ArgumentParser(description="최신 환율 조회 · 해외결제 비교")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("rate", help="최신 환율");  s.add_argument("currencies", nargs="*")
    s = sub.add_parser("convert", help="외화 → 원화")
    s.add_argument("amount", type=float); s.add_argument("cur")
    s = sub.add_parser("compare", help="원화 결제 vs 외화 카드결제")
    s.add_argument("--krw", type=int, required=True, help="원화 결제 금액")
    s.add_argument("--foreign", type=float, required=True, help="외화 결제 금액")
    s.add_argument("--cur", default="EUR")
    s.add_argument("--fee", type=float, help="외화 카드결제 추가비용 %% (미지정 시 1.4/2.4 두 가지)")
    s.add_argument("--krw-fee", type=float, default=0, help="원화 결제 수수료 %% (간편결제·국내처리면 0)")
    s.add_argument("--cashback", type=int, default=0, help="외화 결제 시 받는 캐시백(원)")
    s = sub.add_parser("trend", help="최근 추이")
    s.add_argument("cur", nargs="?", default="EUR"); s.add_argument("--days", type=int, default=30)
    s.add_argument("--table", action="store_true", help="날짜별 표도 출력")
    a = p.parse_args()
    {"rate": cmd_rate, "convert": cmd_convert, "compare": cmd_compare, "trend": cmd_trend}[a.cmd](a)


if __name__ == "__main__":
    main()
