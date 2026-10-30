# shitposts98

@shitposts98용 무인 텍스트 밈 봇입니다. LLM이 드립 한 줄을 쓰면 트윗 캡처 스타일 카드(1080×1350 JPEG)로 렌더링해서 승인 없이 Instagram에 올리고, 올린 뒤 Slack에 알립니다.

목적은 계정 클렌징이에요. 최근 30일 피드의 과반을 오리지널로 채워서 추천 자격을 되찾고, 퍼온 밈은 그대로 병행합니다.

## 왜 Semifeed와 구조가 다른가

| | Semifeed | shitposts98 |
| --- | --- | --- |
| 승인 | Slack 버튼 | 없음 (게시 후 알림만) |
| 실행 | Claude 예약 작업 + Cloudflare Worker | GitHub Actions만 |
| 이미지 호스팅 | raw.githubusercontent.com | 같음 |
| 게시 API | Instagram API (Graph API) | 같음, 공용 Meta 앱 **plutofeed** (Unified login) |
| 토큰 | Worker cron으로 갱신 → KV | 만료 없는 시스템 사용자 토큰 → GitHub Secret (갱신 불필요) |

Semifeed의 Worker는 **Slack 버튼 콜백을 받으려고** 있어요. 이 봇은 승인이 없어서 밖에서 들어오는 요청이 없고, Worker가 할 일이 없어요. 반대로 카드 렌더링에는 Chromium이 필요한데, Worker에서는 돌릴 수 없어요. 그래서 cron, Chromium, git 커밋을 한곳에서 할 수 있는 GitHub Actions 하나로 끝냈어요. 서버도, Cloudflare 계정도, 이미지 호스팅 키도 필요 없어요.

기사 선별 같은 판단이 필요 없어서 Claude 예약 작업 대신 LLM API(Groq) 한 번 호출로 충분해요.

## 한 번 실행 = 최대 1개 게시

```
make_card.py  → 드립 작성(필터 통과 시) → cards/<날짜>/<id>.jpg + .json
git push      → raw URL이 열림
publish.py    → Graph API로 게시 → 카드 JSON에 permalink 기록 → Slack 알림
git push      → 결과 저장 (중복 방지·일일 제한의 근거)
```

`cards/**.json`이 유일한 상태 저장소예요. 과거에 쓴 드립과의 중복 검사, 하루 게시 수 제한 모두 이 파일을 읽어요.

## 무인 운영 안전장치

- **필터**: 금지 주제(정치·실존 인물·성적 내용 등), 220자 초과, 해시태그·멘션, 과거 게시물이나 `style_examples.txt`와 너무 비슷한 문장은 다시 생성해요. 4번 모두 실패하면 **아무것도 올리지 않아요.**
- **일일 제한**: 24시간 동안 `daily_cap`개(기본 3)까지만 올려요.
- **긴급 정지**: 레포 루트에 `STOP` 파일을 만들면 멈춰요. GitHub 모바일 앱에서도 파일 추가 한 번이면 돼요. 지우면 다시 돌아가요.
- **알림**: 게시와 실패가 Slack으로 와요. 토큰이 끊기면 실패 알림에 그렇다고 적혀 와요. 이상한 글이 올라가면 링크로 바로 가서 지우면 돼요.

## 파일

```
config/bot.json            계정 이름·테마·일일 제한·IG 사용자 ID·raw URL·LLM 모델
config/style_examples.txt  말투 기준 문장 — 유머 튜닝은 여기서
config/banned_words.txt    추가 금지어
scripts/writer.py          LLM 호출 + 필터
scripts/render.py          텍스트 → 카드 JPEG (Playwright, 폰트 내장)
scripts/make_card.py       1단계: 카드 생성
scripts/publish.py         2단계: Instagram 게시
scripts/check_token.py     처음 한 번: 토큰 확인, Instagram 계정 ID·만료일 출력
.github/workflows/post.yml  하루 3회 실행
cards/                     만든 카드와 게시 결과
fonts/                     Inter (SIL OFL 1.1)
```

세팅은 [`docs/SETUP.md`](docs/SETUP.md), Meta 앱은 [`docs/PLUTOFEED.md`](docs/PLUTOFEED.md)를 보세요.

## 로컬에서 확인

```bash
pip install -r requirements.txt && python -m playwright install chromium
python scripts/render.py "드립 테스트" -o test.jpg
python -m pytest -q tests
```
