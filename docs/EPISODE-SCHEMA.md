# Lane episodes — news, people, clip

Same engine as the NEC episodes (`engine/build.py`), different recipes. One JSON per video in
`lanes/<lane>/<id>-<slug>.json`. Ids: news `n001…`, people `p001…`, clip `c001…`.
Validate with `python engine/validate_lanes.py`.

## Top-level keys (all lanes)
```json
{
 "id": "n001", "slug": "kebab-case-slug", "format": "news | people | clip",
 "title": "≤ 60 chars, curiosity-driven, no clickbait lies",
 "category": "IT | AI | Power | Energy | EV | Chips | Nepal Power | Telecom | Space | ...",
 "date": "2026-10-26 (the day it was researched)",
 "description": "2–4 plain sentences for YouTube: what happened / who they are, and why it matters.",
 "sources": ["https://… at least 2 reputable URLs actually opened and read (3+ for news)"],
 "tags": ["5–10 lowercase YouTube tags"],
 "mascot": true,
 "beats": [ ... ]
}
```
Optional: `"style"`: one of classic, blueprint, neon, notebook, chalkboard, sunset, newsroom (omit to rotate).

## Recipes (beat order, regex)
- **news**: `hook headline (stat )?concept (timeline )?tip outro`
- **people**: `hook profile (timeline )?(quote )?concept tip outro`
- **clip** (15–25 s): `hook (stat|concept) outro`

## Beats (every beat has `vo`, the spoken line)
| type | fields | limits |
|---|---|---|
| hook | `text` | text ≤ 8 words; vo ≤ 22 words — a question or surprising claim |
| headline | `text`, `source` ("Source: Reuters, IEEE Spectrum"), `date` ("26 OCT 2026"), optional `tag` (default BREAKING), `ticker` | text ≤ 12 words |
| stat | `number` (JSON number), `unit` (≤ 5 words), `text` (≤ 12 words), optional `prefix`, `suffix` (e.g. "%", " GW"), `tag` | number ≤ 6 digits before the decimal |
| concept | `text` (≤ 9 words), `points` (2–3, each ≤ 6 words), optional `tag` (e.g. "WHAT HAPPENED", "WHY THEY MATTER") | |
| timeline | `events`: 2–4 × `{"year", "text" ≤ 7 words}`, optional `tag` | |
| profile | `name`, `role` (≤ 7 words), `icon` (ONE emoji, no flags/people-skin-tones), `known_for` (2–3 × ≤ 3 words), optional `tag` | |
| quote | `quote` (≤ 22 words, a real, sourced quote — the source URL must be in `sources`), `by` | omit the beat if you can't source it |
| tip | `text` (≤ 14 words), `tag` ("WHY IT MATTERS", "ENGINEER'S TAKE", "EXAM LINK") | |
| outro | `text` = "Daily EE" | vo: news "Follow for tech and power news every day." · people "Follow to meet the minds behind the tech." · clip "Follow for a daily dose of engineering." |

## Voiceover rules
- Spoken English for a text-to-speech voice: **no digits** (write "twenty twenty-six", "three point five gigawatts"), no symbols (% → "percent"), spell acronyms with spaces ("A I", "E V", "N E A").
- Total vo words: news 110–170, people 110–170, clip 40–75.
- Hook in the first two seconds; every beat must earn its place; end with a "why it matters to *you*" (a student, an engineer in Nepal).

## Accuracy
- News: only stories from the last 72 hours, confirmed by ≥ 2 independent reputable sources. No rumours, no stock tips, no politics beyond energy/tech policy facts.
- People: verifiable facts only; for living people, nothing defamatory or speculative. Prefer quotes from primary sources; otherwise omit the quote beat.
- Numbers in `stat` must appear in a cited source.
