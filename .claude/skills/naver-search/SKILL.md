---
name: naver-search
description: 네이버 검색 Open API로 블로그·뉴스·웹문서·지역(장소)·쇼핑·카페글·지식iN·책·백과사전·이미지를 검색할 때 사용. 국내 정보, 한국 뉴스, 업체/주차장 위치, 가격 비교, 후기 조사 등 네이버 검색 결과가 필요하면 이 스킬을 쓴다. 사용자가 "네이버에서 찾아줘", "네이버 검색" 이라고 하면 반드시 사용.
---

# 네이버 검색 스킬

네이버 검색 Open API(`openapi.naver.com`)를 `scripts/naver_search.py`로 호출한다.
표준 라이브러리만 쓰므로 설치할 패키지가 없다.

## 실행 방법

```bash
python3 .claude/skills/naver-search/scripts/naver_search.py "<검색어>" --type <종류> [옵션]
```

| 옵션 | 설명 |
|---|---|
| `--type` / `-t` | `blog`(기본) `news` `webkr` `local` `shop` `cafearticle` `kin` `book` `encyc` `image` |
| `--display` / `-n` | 결과 개수 (기본 10, 최대 100 / `local`은 최대 5) |
| `--start` | 시작 위치 (페이지 넘길 때, 최대 1000) |
| `--sort` / `-s` | `sim` 정확도순(기본), `date` 최신순, 쇼핑은 `asc`/`dsc` 가격순, 지역은 `random`/`comment` |
| `--format` / `-f` | `markdown`(기본) 또는 `json` |
| `--csv <파일>` | 결과를 엑셀용 CSV(UTF-8 BOM)로 저장 |

## 종류 고르는 법

- 최근 동향·기사 → `news --sort date`
- 후기·경험담 → `blog`, `cafearticle`
- 장소·업체·주소 → `local` (최대 5건이라 검색어를 지역별로 쪼개 여러 번 호출)
- 가격 → `shop --sort asc`
- 일반 웹 정보 → `webkr`

## 작업 규칙

1. 질문에 맞는 종류를 1~3개 골라 호출한다. 필요하면 검색어를 바꿔 다시 호출한다.
2. 결과를 그대로 붙이지 말고 요약해서 답하고, 근거가 된 항목은 링크를 함께 적는다.
3. 뉴스·블로그는 날짜(`pubDate`, `postdate`)를 확인해 오래된 정보는 그렇다고 밝힌다.
4. 사용자가 엑셀/표로 원하면 `--csv`로 저장하고 파일 경로를 알려준다.

## 오류 대처

- `NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 없습니다` → 사용자에게 키 발급·설정을 안내 (README 참고).
- `401` → 키가 틀렸거나 애플리케이션에 "검색" API가 추가되지 않음.
- `429` → 일일 호출 한도(25,000회) 초과.
- `네트워크 오류` / 프록시 403 → 환경 네트워크 설정에서 `openapi.naver.com` 허용 필요.
