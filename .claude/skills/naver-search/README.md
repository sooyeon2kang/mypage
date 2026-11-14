# 네이버 검색 스킬 설정 가이드

> 네이버 검색 API 신규 발급은 이제 **NAVER API HUB(네이버 클라우드 플랫폼)** 에서 해요.
> 스크립트는 기본으로 API HUB 방식(`naverapihub.apigw.ntruss.com`)을 쓰고,
> 예전 개발자센터 키가 있으면 `NAVER_API_LEGACY=1`로 옛 방식(`openapi.naver.com`)도 쓸 수 있어요.

## 1. API 키 발급
1. https://console.ncloud.com 로그인 → **NAVER API HUB → Application 등록**
2. **① API 선택**: 쓸 검색 종류에 체크 (추천: 뉴스·블로그·지역·웹문서·카페·지식iN) → **다음**
3. **② Application 정보 입력**: 이름 등 입력 후 등록
4. 등록된 Application에서 **Client ID / Client Secret** 확인
5. 요금 안내 확인 (무료 한도·과금 기준)

## 2. 키 넣기 (둘 중 하나)
- **로컬 PC**: 저장소 루트에 `.env` 파일 생성 (`.gitignore`에 등록되어 커밋되지 않음)
  ```
  NAVER_CLIENT_ID=발급받은ID
  NAVER_CLIENT_SECRET=발급받은Secret
  # 예전 developers.naver.com 키라면 아래 줄 추가
  # NAVER_API_LEGACY=1
  ```
- **Claude Code 클라우드 환경**: 환경 설정 → 환경변수에 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 추가

## 3. 테스트
```bash
python3 .claude/skills/naver-search/scripts/naver_search.py "주차장" --type news -n 3
```

## 참고
- API HUB에는 쇼핑(`shop`)·책(`book`) 검색이 없어요 → 예전 키 + `NAVER_API_LEGACY=1`일 때만 가능
