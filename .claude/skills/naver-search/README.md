# 네이버 검색 스킬 설정 가이드

> 네이버 검색·데이터랩 API 신규 발급은 이제 **NAVER API HUB(네이버 클라우드 플랫폼)** 에서 해요.
> 스크립트는 기본으로 API HUB(`naverapihub.apigw.ntruss.com`)를 쓰고,
> 예전 developers.naver.com 키가 있으면 `NAVER_API_LEGACY=1`로 옛 방식도 쓸 수 있어요.

## 1. API 키 발급
1. https://console.ncloud.com 로그인 → **NAVER API HUB → Application 등록**
2. **① API 선택**에서 체크
   - 블로그, 카페, 지식iN, 웹문서, 지역, 뉴스, 이미지 (검색)
   - 검색어트렌드, 쇼핑인사이트 (데이터랩)
3. **② Application 정보 입력** 후 등록
4. Application에서 **Client ID / Client Secret** 확인 (+ 요금 안내 확인)

## 2. 키 넣기
- **Claude Code 클라우드 환경**: 환경 설정 → 환경변수에 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`
- **로컬 PC**: 저장소 루트에 `.env` 파일 (커밋되지 않음)
  ```
  NAVER_CLIENT_ID=발급받은ID
  NAVER_CLIENT_SECRET=발급받은Secret
  ```

## 3. 사용 예
```bash
S=.claude/skills/naver-search/scripts
python3 $S/naver_search.py "바르셀로나 신혼여행 꿀팁" -t blog -s date -n 20
python3 $S/naver_search.py "스드메 견적" -t cafearticle -s date
python3 $S/naver_datalab.py trend "스페인 신혼여행" "이탈리아 신혼여행" --months 24
python3 $S/naver_datalab.py shopkw --category 50000004 "패브릭 소파" "가죽 소파" --csv sofa.csv
python3 $S/naver_datalab.py compete "세비야 맛집" "그라나다 알함브라 예약"
```

## 참고
- API HUB에는 **쇼핑 상품검색·책 검색이 없어요** (쇼핑인사이트=트렌드 지수는 있음)
- 데이터랩 수치는 실제 검색 수가 아니라 상대 지수(기간 내 최대=100)예요
