# Setup

처음 한 번만 PC에서 하면 돼요. 체크박스 순서대로 진행하세요.

## 1. Instagram 계정

- [ ] @shitposts98을 **크리에이터 계정**으로 전환해요 (앱 → 설정 → 계정 유형 및 도구).

## 2. Meta 앱 (plutogram)

Semifeed와 같이 쓰는 **plutogram** 앱(Unified login)에서 @shitposts98 토큰을 받아요. 앱 만들기부터 토큰 확인까지는 [`PLUTOGRAM.md`](PLUTOGRAM.md)에 정리돼 있어요.

- [ ] PLUTOGRAM.md 0~3단계를 진행해서 @shitposts98 토큰을 받아요 (만료: never).
- [ ] `check_token.py`가 출력한 Instagram account id를 `config/bot.json`의 `ig_user_id`에 넣어요. `FILL_ME` 상태로 두면 게시 단계에서 멈춰요.

## 3. GitHub 레포

- [ ] `plt8172/shitposts98`을 **공개(public)** 레포로 만들고 이 폴더를 push해요. Instagram이 `raw.githubusercontent.com`에서 이미지를 가져가기 때문에 공개 레포여야 해요. 레포 이름이 다르면 `config/bot.json`의 `cards_raw_base`를 고치세요.
- [ ] Settings → Actions → General → Workflow permissions가 **Read and write**인지 확인해요. 봇이 카드를 커밋해야 해요.

## 4. Secrets (Settings → Secrets and variables → Actions)

| 이름 | 값 | 어디서 |
| --- | --- | --- |
| `LLM_API_KEY` | Groq API 키 | console.groq.com/keys (Yunoballizer 키를 재사용해도 돼요) |
| `IG_ACCESS_TOKEN` | 2단계에서 받은 plutogram 토큰 | plutogram 앱 → API setup with Unified login → Generate token |
| `SLACK_WEBHOOK_URL` | 밈 채널 전용 Incoming Webhook | Slack 앱 → Incoming Webhooks → 밈 채널 선택 |

토큰 만료를 never로 받았다면 갱신할 일이 없어요. 혹시 만료되거나 끊기면 게시 실패 알림이 Slack으로 오니까, 그때 토큰만 다시 받아서 이 secret을 바꾸면 돼요.

Slack은 Semifeed와 같은 워크스페이스를 쓰되, 밈 채널 전용 웹훅을 따로 만들어요. 웹훅은 지정한 채널 하나에만 글을 쓸 수 있어서 Semifeed 채널과 섞이지 않아요.

## 5. 첫 실행

- [ ] Actions → `post` → Run workflow → **dry_run 체크한 채로** 실행해요. 실행 결과 페이지의 Artifacts에서 `dry-run-card`를 받아 봇이 쓴 드립과 카드를 확인해요. 몇 번 돌려서 톤을 보고, 마음에 안 들면 `config/style_examples.txt`를 고쳐요.
- [ ] dry_run을 끄고 한 번 실행해서 실제 게시와 Slack 알림을 확인해요.

여기까지 되면 하루 3번(KST 12:17, 18:43, 22:09) 자동으로 돌아가요. 시간이나 횟수는 `.github/workflows/post.yml`의 cron에서 바꿔요. GitHub Actions 예약 실행은 몇 분에서 수십 분 늦어질 수 있어요.

## 운영

- 멈추기: 레포 루트에 `STOP` 파일 추가 (내용은 아무거나) → 다시 돌리기: 삭제
- 또는 Actions 탭에서 `post` workflow를 Disable
- 게시 실패: 카드 JSON의 `status`가 `failed`가 되고 `error`에 이유가 남아요. Slack에도 알림이 와요.
- 공개 레포에서 60일 동안 활동이 없으면 GitHub가 예약 실행을 끄는데, 봇이 매번 커밋하니까 돌아가는 동안은 해당 없어요.
