# G. Robotics — autonomous Instagram Reels operation

Researches, writes, renders, checks and publishes **3–4 Reels a day** (one is always **World Tech News**), on
GitHub's cloud — your laptop can be off. Nothing is published unless it passed automated QA; nothing paid is ever
called without an explicit budget.

## How it runs (cloud)
| Job (GitHub Actions) | When (NPT) | What |
|---|---|---|
| `research-and-produce` | 06:15, 16:15 | collect news (27 feeds) → if the queue is short, Claude Code writes verified briefs (`docs/prompts/editor.md`) → viral QA → render (HyperFrames + South Asian English edge-tts voice, ducked music + hits) → QA → host file in release `reel-queue` → queue `qa_passed` |
| `publish-slot` | 08:00, 12:30, 18:00, 21:00 | publish the next approved Reel via the official Instagram API, poll until ready, read back the permalink; skips the slot rather than posting filler |
| `maintenance` | 23:45 daily, Mon 08:45 | pull Insights (only metrics the API returns) → `state/research/performance.md` for the editor; refresh the 60-day Instagram token |

State lives in `state/` (committed by every run): `queue.json` (rendered → scheduled → submitted → published / failed),
`audit.jsonl` (every action), `research/candidates.jsonl`, `analytics.jsonl`, `captions/`.

## Pipeline modules
- `gr/research/collect.py` — 27 feeds (arXiv, NASA, NVIDIA, DeepMind, IEEE Spectrum, The Robot Report, drone press, The Verge, TechCrunch, Ars, MIT TR, Wired, BBC, HN, Google News incl. Nepal). Flags deaths/attacks/disasters/politics as `sensitive` → never auto-produced.
- `docs/prompts/editor.md` — editorial rules: daily World Tech News (2–3 verified stories, source + date on screen), category mix, format/series/style rotation, no fabricated quotes, safety.
- `gr/produce/engine/` — the video engine (formats: explain, mcq, eli5, myth, mistake, news, people, clip; 7 visual styles; captions with word timing; edge-tts en-IN-PrabhatNeural / en-IN-NeerjaExpressiveNeural voice (free, English only), Kokoro fallback; `sound.py` ducks the music bed under the voice and adds hits/risers on the hook, payoff and CTA). `validate_brief.py` checks every brief.
- `gr/qa/check.py` — resolution/codec/fps/duration/size, black or frozen opening, silence, loudness/peak, HDR, caption length/hashtags, token leaks. Limits in `config/platform.json`.
- `gr/publish/instagram.py` + `slot.py` — container → poll → publish → permalink; quota check; lost-commit duplicate guard; resume after transient errors; token-expiry → failed + alert. `hosting.py` gives Meta a public video URL (Instagram Login path).
- `gr/analytics/pull.py` — Reels Insights; `digest.py` ranks them into `state/research/performance.md`, which every editor run reads.
- `.claude/skills/` — vendored MIT skills (Ootto) the editor runs for every Reel: trends → going-viral → hooks + A/B → script → on-screen text → CTA → caption/hashtags → cover. `gr/qa/viral.py` rejects weak hooks / early payoffs before rendering.
- `tests/` — publisher safety tests (`python -m pytest tests -q`).

## One-time setup (needs you)
1. **GitHub**: create a free account/repo `g-robotics-media` (**public** recommended: unlimited Actions minutes and Meta can fetch the video URL; no secrets live in the repo). Push this folder.
2. **Instagram**: switch the G. Robotics account to **Professional (Business or Creator)**. At developers.facebook.com create an app → add **Instagram API with Instagram Login** → add yourself as Instagram tester → generate a token with `instagram_business_basic` + `instagram_business_content_publish` (+ `instagram_business_manage_insights`). Owner-only use works in development mode.
3. **Secrets** (repo → Settings → Secrets → Actions): `IG_USER_ID`, `IG_ACCESS_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN` (run `claude setup-token`), optional `ELEVENLABS_API_KEY`, `GH_SECRETS_PAT` (fine-grained PAT, this repo, Secrets: write — lets the token auto-refresh).
4. Run **publish-slot** once manually with *Dry run* on, then **research-and-produce**, inspect the first Reels, then let the schedule run.

## Cost (estimate, verify monthly)
GitHub Actions on a public repo: $0. Research/editorial: your Claude subscription (usage limits apply). Rendering + Kokoro voice: $0.
Optional paid: ElevenLabs (~110–150k chars/month for 4 Reels/day → a paid tier), AI video/avatars (disabled until you set a budget).
