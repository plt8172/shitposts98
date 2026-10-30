# plutogram — Semifeed·shitposts98 공용 Meta 앱

두 봇이 함께 쓰는 Meta 앱이에요. 2026년 10월 기준으로 **새로 만드는 앱은 "API setup with Unified login"만 쓸 수 있어요.** 기존 "Instagram login" 방식(`graph.instagram.com`)은 새 앱에서 선택할 수 없어요.

## Instagram login과 뭐가 다른가

| | Instagram login (기존 Semifeed 앱) | Unified login (plutogram) |
| --- | --- | --- |
| API 주소 | `graph.instagram.com` | `graph.facebook.com/v26.0` |
| 토큰 종류 | Instagram 사용자 토큰 (60일, 매주 갱신 필요) | **시스템 사용자 토큰**. 만료 기간을 설정에서 고를 수 있어요 |
| 게시할 계정 지정 | `me` | 숫자 Instagram 계정 ID (`/me`는 시스템 사용자를 가리켜요) |
| 권한 이름 | `instagram_business_*` | `instagram_basic`, `instagram_content_publish` |
| 필요한 것 | 앱만 | **비즈니스 포트폴리오가 앱을 소유**해야 해요. Facebook 페이지는 필요 없어요 |

이게 바로 바꿀 이유예요. 토큰 만료를 **"없음"**으로 설정할 수 있으면 갱신 workflow, KV 저장, PAT가 전부 필요 없어져요. 한 번 발급하면 끝이에요.

## 만드는 순서

### 0. 준비
- [ ] semiwire와 shitposts98 둘 다 **프로페셔널(크리에이터 또는 비즈니스) 계정**이어야 해요.
- [ ] **비즈니스 포트폴리오**가 필요해요 (business.facebook.com). 없으면 하나 만드세요. 이름은 `plutogram` 정도면 충분해요.

### 1. 앱 만들기 (developers.facebook.com → My Apps → Create App)
- [ ] 앱 이름: `plutogram`
- [ ] 사용 사례: **Manage messaging & content on Instagram**
- [ ] 비즈니스 포트폴리오: 0단계에서 만든 것을 연결해요. Unified login은 포트폴리오가 소유한 앱이어야 해요.

### 2. 로그인 설정 (config) 만들기
- [ ] Use cases → Manage messaging & content on Instagram → **Customize** → **API setup with Unified login**
- [ ] Configure your app → **Create new configuration**
- [ ] **Edit permissions**에서 꼭 필요한 것만 남겨요: `instagram_basic`, `instagram_content_publish`. 게시만 하니까 메시지와 광고 권한(`instagram_manage_messages`, `ads_*`)은 빼도 돼요. 대시보드가 `instagram_manage_messages`를 필수로 요구하면 그대로 둬요.
- [ ] 미리보기에 나오는 **토큰 만료 기간**을 **Never(만료 없음)**로 골라요. 이 단계가 제일 중요해요. 해당 옵션이 없으면 가장 긴 기간을 고르세요.
- [ ] **Use this configuration**
- [ ] **Redirect URL**: HTTPS 주소 하나가 필요해요. 대시보드에서 토큰을 직접 생성할 거라 실제로 쓰이지는 않아요. Semifeed Worker 주소(`https://semifeed.semifeed.workers.dev/`)를 넣고 Save하면 돼요.

### 3. 계정 추가하고 토큰 받기 (계정마다 한 번씩)
- [ ] 같은 화면의 **Generate access tokens** → **Add account** → Instagram 계정을 테스터로 초대해요.
- [ ] 그 계정으로 Instagram 웹에 로그인 → 설정 → 웹사이트 권한 → 앱 및 웹사이트 → **테스터 초대**를 수락해요.
- [ ] 대시보드로 돌아와 **Generate token** → 로그인 → 토큰을 복사해요. **한 번만 보여주니까** 바로 저장하세요.
- [ ] 확인:
  ```bash
  IG_ACCESS_TOKEN=<토큰> META_APP_ID=<앱 ID> META_APP_SECRET=<앱 시크릿> \
    python scripts/check_token.py
  ```
  출력에서 확인할 것은 세 가지예요. `instagram account: @계정 id ...`가 맞는 계정인지, `expires: never`인지, `scopes`에 `instagram_content_publish`가 있는지요. 앱 ID와 시크릿은 App settings → Basic에 있어요.

semiwire와 shitposts98에 각각 이걸 해서 **토큰 두 개**를 받아요. 하나의 토큰이 같은 포트폴리오의 두 계정을 다 다룰 수도 있지만, 계정별로 따로 받아야 한쪽을 끊어도 다른 쪽이 살아 있어요.

### 4. 각 봇에 넣기
| | shitposts98 | Semifeed |
| --- | --- | --- |
| 토큰 | GitHub Secret `IG_ACCESS_TOKEN` | `wrangler secret put IG_ACCESS_TOKEN` |
| 계정 ID | `config/bot.json` → `ig_user_id` | `wrangler.toml` → `IG_USER_ID` |
| 코드 | 이미 Unified login용으로 바뀌어 있어요 | Worker 수정 필요 (아래) |

**Semifeed Worker에서 바꿔야 하는 것**: `worker/src/instagram.ts`의 주소 `graph.instagram.com` → `graph.facebook.com`, `IG_API_VERSION` → `v26.0`, 그리고 `refreshToken`(`ig_refresh_token`)은 시스템 사용자 토큰에는 쓸 수 없으니 토큰 갱신 cron(`0 18 * * *`)과 함께 빼요.

### 5. 앱 모드
개발 모드 그대로 두면 돼요. 앱 역할이 있는 본인 계정에는 Standard Access로 충분하고, 앱 심사는 다른 사람의 계정을 연결할 때만 필요해요.

## 막히면
- **"Instagram login is not available"**: 정상이에요. 새 앱이라서 그래요. Unified login을 쓰면 돼요.
- **테스터 초대가 안 보임**: Instagram 앱 말고 **웹**(instagram.com)에서 찾아야 해요.
- **게시할 때 `code 190`**: 토큰이 만료됐거나 끊긴 거예요. 계정이 포트폴리오에서 빠졌거나 앱이 제거됐을 수 있어요. 3단계를 다시 하면 돼요.
- **`ig_user_id`에 뭘 넣어야 할지 모름**: `check_token.py`가 출력하는 Instagram account id를 넣으세요.
