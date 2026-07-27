# Focus Languages v2 — Setup & Operations

Everything the v2 expansion added, and what you must configure before each
piece works in production. Systems degrade gracefully: an unset provider key
disables that feature rather than breaking the app.

## Repository layout

| Path       | What it is                                            |
|------------|-------------------------------------------------------|
| `backend/` | Django + DRF API (shared by every client)             |
| `mobile/`  | Flutter student app (Android/iOS)                     |
| `admin/`   | Standalone React admin dashboard (Vite)               |
| `web/`     | Next.js web app — same API as mobile                  |

## 1. Backend

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # then fill in the keys below
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed          # levels, placement bank, wordlist, admin
.venv/bin/python manage.py runserver
```

`seed` is idempotent — safe to re-run after deploys.

### Required environment variables

| Variable | Needed for | Without it |
|---|---|---|
| `ANTHROPIC_API_KEY` | AI Tutor replies, news rewriting | Tutor returns 503; generation command exits |
| `OPENAI_API_KEY` | Whisper STT (tutor audio) | Audio turns fail; text turns still work |
| `GOOGLE_TTS_API_KEY` | Tutor voice output | Replies are text-only |
| `GOOGLE_CLIENT_ID`, `GOOGLE_WEB_CLIENT_ID` | Google Sign-In | Google login returns 401 |
| `NEWSAPI_KEY` | News source articles | Only original stories can be generated |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*` | Web card payments | Stripe checkout returns 400 |
| `CMI_MERCHANT_ID`, `CMI_STORE_KEY` | Moroccan card payments | CMI initiate returns 400 |
| `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`, `ANDROID_PACKAGE_NAME` | Play purchase verification | Play verification refuses to activate |

Tunables (`COINS_*`, `TUTOR_*`) have working defaults — the coin cap is 60/day,
free tutor sessions 2/day, premium 10/day, 6 exchanges per session.

### Scheduled jobs

```cron
# News/story generation → saved as DRAFTS for admin review (v2 §2.2)
0 3 * * * cd /srv/focus/backend && .venv/bin/python manage.py generate_content --levels A1,A2,B1 --per-level 2
```

`generate_content` never publishes directly; everything lands in the admin
review queue. Run `annotate_lessons` once after loading new lessons to compute
selective-translation annotations:

```bash
.venv/bin/python manage.py load_wordlist          # CEFR word list → WordLevel
.venv/bin/python manage.py annotate_lessons       # add --llm to review ambiguous cases
```

## 2. Admin dashboard

```bash
cd admin && npm install && npm run dev     # proxies /api → 127.0.0.1:8000
npm run build                              # → admin/dist, serve behind nginx
```

Seeded super admin: `admin@focus.test` / `adminpanel12345` — **change this
immediately in production** (Team page → add a new super admin, disable the
seeded one).

Roles are enforced by backend decorators, not just hidden menus:
- **Super** — everything, plus admin accounts and API keys
- **Content** — lessons, articles, question bank; no users or payments
- **Support** — user search and manual premium activation; no content editing

## 3. Content Import API

```bash
curl -X POST https://lms.centrefocus.ma/api/v1/content/lessons/import \
  -H "Authorization: Bearer fl_live_xxx" \
  -H "Content-Type: application/json" \
  -d @lesson.json
```

`publish_mode` defaults to `draft`. `direct` requires a key minted with the
`direct_publish` trust level; every direct publish is logged with the key,
timestamp, and content ID (visible on the admin Team page).

## 4. Mobile

```bash
cd mobile && flutter pub get
flutter run --dart-define=API_BASE_URL=https://lms.centrefocus.ma/api/v1 \
            --dart-define=GOOGLE_WEB_CLIENT_ID=xxx.apps.googleusercontent.com \
            --dart-define=WHATSAPP_NUMBER=2126XXXXXXXX
```

Google Sign-In on Android needs the **Web** OAuth client ID as
`serverClientId` (that is what yields an `idToken` the backend can verify),
plus an Android OAuth client registered with both debug and release SHA-1
fingerprints.

## 5. Web app

```bash
cd web && npm install
API_ORIGIN=http://127.0.0.1:8000 npm run dev
npm run build && npm start
```

Set `NEXT_PUBLIC_WHATSAPP_NUMBER` for the manual-payment link. The payment
page auto-selects CMI for Morocco-detected users and Stripe elsewhere; the
rest sit behind the "طرق دفع أخرى" accordion.

Browser microphone caveats for the AI Tutor: `getUserMedia` requires HTTPS
(or localhost), Safari records `audio/mp4` rather than `audio/webm` (handled
by content-type sniffing), and Safari blocks autoplay unless playback is
primed inside a user gesture — the first mic tap does that priming.

## 6. Deployment notes

- Both `admin/dist` and the Next.js app should be served from the same origin
  as the API (`lms.centrefocus.ma`) so the `/api` paths resolve without CORS.
- Google Play RTDN → `POST /api/v1/billing/google/rtdn`
- Stripe webhook → `POST /api/v1/billing/stripe/webhook`
- CMI callback → `POST /api/v1/billing/cmi/callback`

All three are CSRF-exempt, signature/authenticity checked, and idempotent —
replaying a notification never grants premium twice.
