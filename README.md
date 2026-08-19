# 두산 베어스 KBO 자동 수집 + GitHub Pages 배포 스캐폴드

이 저장소는 다음 3가지를 함께 제공합니다.

1. `scripts/refresh.py` : KBO 공식 페이지를 긁어 `data/latest.json` 갱신
2. `.github/workflows/daily.yml` : 매일 자동 실행 + GitHub Pages 배포
3. `app.py` : 로컬에서 `POST /refresh` 로 즉시 갱신 버튼 지원

## 포함된 구조

```text
.github/workflows/daily.yml
app.py
data/latest.json
scripts/refresh.py
docs/index.html
docs/app.js
docs/styles.css
requirements.txt
README.md
```

## 기본 스케줄

- 현재 기본값: **매일 08:05 KST**
- GitHub Actions cron 은 **UTC 기준**이므로 워크플로에는 `5 23 * * *` 로 들어 있습니다.
- 주의: GitHub cron 은 몇 분 정도 지연되거나 드물게 스킵될 수 있습니다.

## GitHub 설정 방법

1. 새 GitHub 저장소 생성
2. 이 ZIP 내용을 그대로 업로드 또는 커밋
3. 저장소에서 **Settings → Pages** 이동
4. **Build and deployment** 의 Source 를 **GitHub Actions** 로 변경
5. 저장소 메인 페이지의 **Actions** 탭에서 `Daily KBO Refresh and Deploy` 확인
6. 첫 배포 테스트는 **Run workflow** (`workflow_dispatch`) 로 수동 실행
7. 성공 후 `github-pages` 환경 URL이 발급되면 그 URL이 실제 공개 주소입니다.

## 로컬 테스트

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python scripts/refresh.py
python app.py
```

그 다음 브라우저에서 `http://127.0.0.1:5000` 접속 후 **즉시 갱신** 버튼 테스트.

## 설계 메모

- KBO 는 공식 공개 JSON API 가 아니라 ASP.NET 페이지 구조를 많이 사용합니다.
- 실제 운영에서는 `__VIEWSTATE`, `__EVENTVALIDATION`, POST 파라미터 유지가 필요한 페이지가 있습니다.
- 이 스캐폴드는 그 구조를 감안해 **서버 측 수집기**를 전제로 두었습니다.
- unattended 실행을 위해 요청 재시도, 타임아웃, **마지막 정상 JSON 유지** 가 들어 있습니다.
- 스크래핑이 완전히 실패해도 빈 지표를 배포하지 않도록 마지막 정상값을 유지합니다.

## 한계 / 수정 포인트

- 현재는 팀 요약과 선발 4명은 자동 수집 경로가 포함되어 있고, `최승용` 및 최신 경기 문자열은 시드 JSON 기준 `null` 일 수 있습니다.
- 구단 상대전적 세부표, 16명 전체 선수 ID 자동 탐색, 최신 경기 문구 보강은 `scripts/refresh.py` 에 추가 확장 가능합니다.
- Pages 는 정적 호스팅이라 서버 측 버튼은 동작하지 않습니다. **즉시 갱신 버튼은 로컬 Flask 실행 시에만 동작**합니다.
