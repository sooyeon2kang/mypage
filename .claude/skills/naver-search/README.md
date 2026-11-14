# 네이버 검색 스킬 설정 가이드

## 1. API 키 발급 (무료, 하루 25,000회)
1. https://developers.naver.com → 로그인 → **Application → 애플리케이션 등록**
2. 사용 API: **검색** 선택
3. 환경: **WEB 설정** → URL에 `http://localhost` 입력
4. 등록 후 **Client ID / Client Secret** 확인

## 2. 키 넣기 (둘 중 하나)
- **로컬 PC**: 저장소 루트에 `.env` 파일 생성 (`.gitignore`에 등록되어 커밋되지 않음)
  ```
  NAVER_CLIENT_ID=발급받은ID
  NAVER_CLIENT_SECRET=발급받은Secret
  ```
- **Claude Code 클라우드 환경**: 환경 설정의 환경변수에 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 추가
  + 네트워크 허용 호스트에 `openapi.naver.com` 추가

## 3. 테스트
```bash
python3 .claude/skills/naver-search/scripts/naver_search.py "주차장" --type news -n 3
```
