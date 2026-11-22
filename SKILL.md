---
name: reel-famous-genz
description: Make one-lane face-breakdown reels of Gen Z actors and creators in the @glowupmenclub format (their exact spoken hooks, "let's break down what his face actually has", 4-6 feature callouts on a painted Commons portrait, game-card payoff, comment CTA), packaged with the faceless K-pop narrator and pink glow background. Own memory (topic bank, subjects, hook rotation, posted log, learnings, board decisions) in its own data home; renders with its own Remotion engine (composition `genz-face`, nothing in reel-factory). Use for this account's daily routine (make, QA, schedule one day ahead on the four jenny accounts), topics, scripts, renders, post logging and feedback.
---

# reel-famous-genz

One account, one lane: **Gen Z actors and creators** (no football, despite the name, which the board chose on 22 Nov 2026). The format is a straight clone of @glowupmenclub's face breakdowns. Only the packaging is ours: the Airport Idol narrator (faceless K-pop guy), the pink K-pop glow, and the game card instead of an app score.

**Before writing anything, read `$RFG_HOME/decisions.md` (the board's rules) and `$RFG_HOME/learnings.md`.** They are the skill's memory and they win over this file.

## Board rules (short version; full list in decisions.md)
- Hooks are @glowupmenclub's **word for word**; only `{slots}` change (`pack/hooks.json`). `lint` rejects anything else.
- Beat order: hook with the name → "So let's break down what his face actually has." → 4-6 features (one callout each) → game card (OVR + EYE JAW SYM NOS BRW SKN) → "Comment who I should break down next."
- Facial features only. No boy group, idol position, concept, debut or trainee framing; no score out of 10; no app or link; no looksmaxxing words; every spoken sentence under 14 words.
- Wikimedia Commons photos only, with the author and licence credited on screen, plus "AI-edited images".
- **Posting is automatic since 22 Nov 2026** (board: "an automatic routine like reel-factory's, scheduling 1 day ahead, self-healing"). A reel goes out once it passes `rfg.sh qa`; board-approved reels (`rfg.sh approve <id>`) go first. Every reel is on the calendar a day before it posts, so the board can veto it (`status=dropped`, delete its queued group). Post logging: `rfg.sh posted`.

## Data home (`$RFG_HOME`, default `/paperclip/instances/default/data/reel-famous-genz/<company>/`)
| File | What it holds |
|---|---|
| `decisions.md` | the board's standing rules (edit only on board direction, with a date) |
| `learnings.md` | feedback, view counts, render lessons; append with `rfg.sh learn` |
| `topics.csv` | topic bank index: id, template, subject, status (idea → ready → restyled → scripted → voiced → rendered → qa_ok or approved → scheduled → posted, or dropped), hook, notes |
| `topics/<id>.json` | one reel: template, subject, gender, slots, Commons photo, 4-6 features (region, label, chip, vo, optional at/crop), card, cta |
| `subjects.json` | faces covered: Commons file, credit, cutout, likeness, posts (a subject cools down for 30 days after a post) |
| `hooks.jsonl` | every hook scripted, with its template id (rotation: `next` picks the least-used template) |
| `scheduled.jsonl` | every Slashloop group created: reel, publishAt, groupId, platforms, media |
| `posted.jsonl` | what was posted, where, when, and stats added later |
| `faces/`, `stills/` | source photos, painted cutouts (`stills/faces/<slug>/cut.png`), narrator sprites (`stills/sprites/`) |
| `work/<id>/`, `out/<id>.mp4` | script.json, voice clips, durations; render jobs and MP4s |
| `state/spend.jsonl` | every OpenRouter call and its cost |
| `state/hosted.json`, `state/schedule-<date>.json` | jsDelivr URLs per reel; the `create_social_post` payloads of the last `schedule` |

## Commands (`scripts/rfg.sh <cmd>`)
| Command | Does |
|---|---|
| `init` | create the data home and seed the memory files (never overwrites). Narrator sprites live in `stills/sprites/idol_film_<pose>.png` |
| `status` | topics by status, hook rotation, posts, next suggested topic |
| `hooks` | list the hook templates and their source reels |
| `photo <id>` | download `photo.commons_file` from Wikimedia Commons; record the author and licence |
| `restyle <id>` | painted portrait (Gemini 3.1 Flash Image on magenta, QA likeness ≥ 8, chroma key): about $0.08 |
| `copy <id> [--force]` | LLM writes missing feature lines (linted); topic lines you wrote win |
| `script <id>` | build `work/<id>/script.json` and lint it against the board rules; logs the hook in hooks.jsonl |
| `lint <id>` | lint only |
| `tts <id> [--force]` | ElevenLabs `charlie` at 0.95 via OpenRouter, one clip per beat: about $0.01 |
| `render <id>` | build the job and render it with the skill's own engine (`engine/`) |
| `make <id>` | restyle (if needed) → script → tts → render |
| `approve <id>` | the board approved the MP4 |
| `posted <id> --platform ig\|tt\|yt [--url U]` | log a post (posted.jsonl, subjects.json) |
| `stats <id> --views N` | add view counts to the post |
| `learn "<text>"` | append a dated line to learnings.md |
| `qa <id>` | automated QA: lint, 1080x1920 + audio, 20-60 s and not shorter than the voice, cover `out/<id>_cover.jpg` (frame at 1.2 s, under 2 MB). `rendered` → `qa_ok`; exit 3 on FAIL |
| `host <id>` | push the MP4 + cover to the `media` branch, print jsDelivr URLs pinned to the commit (skips files already there) |
| `plan [--start D] [--days N] [--posts F]` | slots (13:00 and 20:00 UTC) in the window: `FILL` (reel for an empty slot; board-approved first, 30-day subject cooldown), `GAP` (a reel missing some of the four accounts), `SHORT` (nothing to post), and with a saved `list_social_posts` file `ERROR`, `MISSING` (group deleted) and `MIXING` (facemetric media on these accounts). Default: tomorrow, 1 day |
| `schedule [same args]` | `plan`, then QA + host each FILL and write `state/schedule-<date>.json`: one `create_social_post` payload per reel (all four accounts, Pinterest board, caption) |
| `scheduled <id> --at ISO --group G [--platforms ig,yt,threads,pinterest] [--media U --cover U]` | record a created group in scheduled.jsonl; status → `scheduled` |
| `supply [--start D] [--days 3]` | open slots vs postable reels, the next topics to make, templates still blocked; last line `SUPPLY OK` or `SUPPLY WARN` |

## Writing a topic
1. Pick a template (`rfg.sh hooks`) and the least-used one if in doubt (`rfg.sh status`). C, D and E have no single celebrity: give each feature its own `subject` (each needs its own photo and cutout). The card is optional there.
2. Find a frontal Commons photo (CC BY, CC BY-SA, CC0 or PD), and put the `File:...` title in `photo.commons_file`.
3. Features: `region` is one of hair, brows, eyes, eye_colour, nose, cheekbones, lips, jaw, chin, skin. The default anchors fit a cutout whose face sits like Keoghan's. **After `restyle`, look at the cutout** and set `at` (image fractions) and `crop.y` per feature when the face sits higher or lower. Chalamet (RSG0002) is the worked example.
4. Before a full render, render one still per beat to check the layout: copy `out/<id>/job`, set `still_composition: "genz-face"` and `still_frame: N` in its job.json, and run `engine/render.sh <job> <out.jpg>`. It takes about 15 s a frame.

## Rendering (the skill's own engine)
- `engine/` is a self-contained Remotion renderer with one composition, `genz-face` (`engine/compositions/genz-face/`), and nothing else. It holds no qoves or facemetric code (those stay in reel-factory), and it needs nothing from reel-factory.
- `render` runs `engine/render.sh` under its watchdog on this box. It takes about 20 min per 35 s reel.
  - The runtime (node_modules, headless Chrome, bundle cache, render lock) is the skill's own: `render.vps_runtime` = `$RFG_HOME/remotion-runtime/`, built on the first render (about 1.5 GB).
  - A render won't start below 1 GB MemAvailable, so it backs off if another renderer on the box is using memory.
  - **Start it detached** (`setsid nohup ... &` with a log) and set `TMPDIR` inside `$RFG_HOME`. A render that is a child of the run dies when the run ends.
- There is no Cloudflare target.
- `RFG_ENGINE` points the skill at another checkout of itself (tests only).
- Needs `OPEN_ROUTER_API_KEY` for restyle, copy and tts. The chroma key needs node and `sharp`; `rfg.sh` finds `/app/node_modules/.pnpm/sharp@*/node_modules` or uses `$RF_SHARP`.

## Posting (all four jenny accounts)
- Accounts and slots live in `pack/config.json` → `schedule`: Instagram `jennymaxxer`, YouTube `looksmaxxers-d1q`, Threads `jennymaxxer`, Pinterest `jennymaxxing` (board `1088323134893667526`), 13:00 and 20:00 UTC.
- The skill cannot call Slashloop. For each payload of `schedule`: `upload_social_media` on `upload.video` and `upload.thumbnail`, put the two returned URLs in `media[0].url` / `media[0].thumbnail`, `create_social_post` with `integrationIds`, `content`, `media`, `publishAt`, `settings` exactly as written, then `rfg.sh scheduled <id> --at <publishAt> --group <groupId>`.
- Caption = hook / line 2 + card + CTA / photo credit + "AI-edited images" / 5 hashtags. Line 2 and the hashtags come from the topic's `caption` and `tags` when set (write them by hand), else from the feature labels.
- Templates C, D and E are blocked in `schedule.blocked_templates` until their layouts exist (SLA-1653).

## Tests
`cd <skill> && python3 -m unittest discover -s tests`: hook templates, slot whitelists, lint rules, script shape, hot words, rotation and memory. No network or spend.
