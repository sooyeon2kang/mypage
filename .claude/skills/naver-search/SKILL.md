---
name: naver-search
description: 네이버 검색 API(NAVER API HUB)로 블로그·카페 후기, 뉴스, 지역, 지식iN, 웹문서를 검색하고, 데이터랩(검색어 트렌드·쇼핑인사이트)과 블로그 키워드 경쟁도를 조회할 때 사용. 신혼여행(스페인 등)·결혼준비(스드메, 웨딩홀, 혼수) 찐후기와 꿀팁 찾기, 가구·인테리어 쇼핑 트렌드 비교, 블로그 포스팅 키워드 고르기에 쓴다. "네이버에서 찾아줘", "블로그 후기", "카페 후기", "검색량", "트렌드", "키워드" 요청이면 사용.
---

# 네이버 검색 스킬

스크립트 2개 (표준 라이브러리만 사용, 설치 불필요). 인증은 `.env` 또는 환경변수의
`NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` (NAVER API HUB 키). 예전 developers.naver.com 키면 `NAVER_API_LEGACY=1`.

```bash
S=.claude/skills/naver-search/scripts
python3 $S/naver_search.py  "<검색어>" -t <종류> [-n 개수] [-s sim|date] [--start N] [--csv 파일]
python3 $S/naver_datalab.py trend   "<키워드>" ["묶음=키1,키2"] [--months 12] [--unit month|week|date]
python3 $S/naver_datalab.py shopping --category "가구/인테리어=50000004" [--months 12]
python3 $S/naver_datalab.py shopkw  --category 50000004 "패브릭 소파" "가죽 소파"
python3 $S/naver_datalab.py compete "<키워드1>" "<키워드2>" ...
```

- 검색 종류(`-t`): `blog` `cafearticle` `kin` `news` `webkr` `local`(최대 5건) `image` `encyc` `errata`(오타변환)
- **쇼핑 상품검색(`shop`)·책(`book`)은 API HUB에 없음** (레거시 키 전용). 상품 가격 비교가 필요하면 그렇다고 말하고 블로그 후기·쇼핑인사이트로 대신한다.
- 데이터랩 공통 옵션: `--gender m|f`, `--ages 3,4`(3=25~29, 4=30~34, 5=35~39), `--device pc|mo`, `--csv`
- 데이터랩 지수는 **상대값**(기간 내 최대=100)이지 실제 검색 횟수가 아님을 답변에 밝힌다.

## 용도별 레시피

### ✈️ 여행·결혼준비 찐후기 / 꿀팁
1. `blog`와 `cafearticle`을 둘 다, `-s date -n 30`(최신순)으로 검색. 필요하면 `-s sim`도 한 번.
2. 검색어는 구체적으로 쪼갠다: 도시+주제+"후기/꿀팁/주의" (예: `바르셀로나 신혼여행 소매치기`, `세비야 숙소 후기`, `스드메 견적 후기`, `웨딩홀 계약 주의사항`)
3. 광고 걸러내기: "체험단", "원고료", "제공받아", "소정의", "협찬" 문구가 보이면 광고 가능성이 높다고 표시하고, 개인 경험 위주 글을 우선한다.
4. 날짜(`postdate`) 확인 → 1~2년 넘은 정보(가격·운영시간·예약 방식)는 오래됐다고 표시.
5. 답변은 주제별 꿀팁 요약 + 근거 글 링크. 여러 글에서 반복되는 내용은 "공통 의견"으로 묶는다.

### 🛋️ 가구·혼수 쇼핑
- 분야 추이: `shopping --category "가구/인테리어=50000004"`
- 같은 분야 안 키워드 비교: `shopkw --category 50000004 "모듈 소파" "리클라이너 소파"` (최대 5개)
- 실사용 후기: `blog "<제품명> 내돈내산 후기" -s date`
- 주요 카테고리 ID: 가구/인테리어 50000004, 디지털/가전 50000003, 생활/건강 50000008, 패션잡화 50000001, 식품 50000006

### ✍️ 블로그 포스팅 키워드
1. `trend`로 후보 키워드 검색 관심도와 시기별 추이 비교 (최대 5개 묶음)
2. `compete`로 블로그 글 수 확인 → 관심도는 높고 글 수는 적은 키워드를 추천
3. 결과는 표로 정리하고, 필요하면 `--csv`로 저장해서 엑셀용 파일 경로를 알려준다.

## 오류 대처
- 키 없음 → README 안내. 401 → 키 오류 또는 Application에 해당 API 미선택.
- 프록시 403/네트워크 오류 → 환경에서 `naverapihub.apigw.ntruss.com` 허용 필요.
- 429 → 호출 한도 초과.
