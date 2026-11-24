---
name: reel-famous-genz
description: Make one-lane face-breakdown reels of Gen Z actors and creators in the @glowupmenclub format (their exact spoken hooks, 4 feature callouts on a painted Commons portrait with hard cuts, game-card payoff, Axend CTA card, music and a loop tail, 20-30 s), packaged with the faceless K-pop narrator and pink glow background. Own memory (topic bank, subjects, hook rotation, posted log, learnings, board decisions) in its own data home; renders its own Remotion composition `genz-face` on Cloudflare only (the `reel-remotion` Worker; never on the agent box). Use for this account's daily routine (make, QA, schedule one day ahead on the four jenny accounts), topics, scripts, renders, post logging and feedback.
---

# reel-famous-genz

One account, one lane: **Gen Z actors and creators** (no football, despite the name, which the board chose on 22 Nov 2026). The format is a straight clone of @glowupmenclub's face breakdowns. Only the packaging is ours: the Airport Idol narrator (faceless K-pop guy), the pink K-pop glow, and the game card instead of an app score.

**Before writing anything, read `$RFG_HOME/decisions.md` (the board's rules) and `$RFG_HOME/learnings.md`.** They are the skill's memory and they win over this file.

## Board rules (short version; full list in decisions.md)
- Hooks are @glowupmenclub's **word for word**; only `{slots}` change (`pack/hooks.json`). `lint` rejects anything else.
- Beat order (celebrity): hook with the name → 4 features (one callout each; a topic holds 4-6, the reel keeps 4) → game card (OVR + EYE JAW SYM NOS BRW SKN) → Axend CTA card ("Want your own face card? Scan yours in Axend."). **No spoken bridge** (board, 24 Nov 2026: "let's break down..." is filler): the hook cuts straight into the first feature, and every feature beat starts on a hard cut with a white flash and a crash zoom. The comment prompt ("Comment who I should break down next.") rides in the post text. Self-diagnosis kinds (C, D, E) keep their bridge and comment CTA.
- **Retention packaging (board, SLA-1682 / SLA-1685, 24 Nov 2026):** the hook shows the face full-frame from frame 0 with no headline over it, the spoken hook runs in the captions only (nothing animates in; board, 24 Nov: no episode tag and no credit line in the picture either) and the voice starts at 0.0 s; every reel ends with a 0.8 s silent loop tail (frame 0 held after the CTA, `loop`, lint 0.3-2.0 s). **Every reel is the short cut on every platform** (board, 24 Nov: YouTube, Threads and Pinterest too): 4 callouts, 20-30 s, with music (`$RFG_HOME/music/*.mp3`, reel-factory's Lyria beats, gain 0.12; `render` fails without a track). The spoken hooks stay word for word.
- **Text hook (board, 24 Nov 2026, SLA-1685 option 2, then "hook only"):** a small "wait for #4…" line at the top during the hook only (gone on the first feature cut, back in the loop tail), like @glowupmenclub's caption, and a "1/4 … 4/4" chip on each feature (4/4 in pink). The strongest feature plays last so #4 pays off: the topic's `best` (feature index), else the region with the highest card stat (`pack/config.json` → `tease.stat_of`); its "Start with ..." opener becomes "Saved the best for last: ...", and the cut always keeps the last feature. A+ reels keep the change last; a topic with `ig_features` keeps its own order. A topic's `tease` (its own line with `{n}`, or false) wins.
- Facial features only. No boy group, idol position, concept, debut or trainee framing; no score out of 10; no app or link; no looksmaxxing words; every spoken sentence under 14 words.
- Wikimedia Commons photos only, with the author and licence credited in the post text, plus "AI-edited images" (not on screen: board, 24 Nov).
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
| `state/hosted.json`, `state/schedule-<date>.json` | raw.githubusercontent URLs per reel (with the file sizes, so a re-render is pushed again); the `create_social_post` payloads of the last `schedule` |

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
| `render <id> [--wait S] [--force]` | build the job (the short cut: 4 features, music, Axend card) and render it on Cloudflare (`reel-remotion` Worker) to `out/<id>.mp4`. Submits, or checks the job already submitted, then returns: exit 0 = written (`rendered`), exit 75 = still queued/rendering (run it again on the next wake), exit 2 = failed (run it again to resubmit). An MP4 newer than the script and the voice is not rendered again; `--force` renders it again (e.g. after a composition change) |
| `make <id>` | restyle (if needed) → script → tts → render (submit; exit 75 until Cloudflare is done) |
| `approve <id>` | the board approved the MP4 |
| `posted <id> --platform ig\|tt\|yt [--url U]` | log a post (posted.jsonl, subjects.json) |
| `stats <id> --views N` | add view counts to the post |
| `learn "<text>"` | append a dated line to learnings.md |
| `qa <id>` | automated QA: lint, 1080x1920 + audio, 20-30 s (self-diagnosis reels 20-60 s) and not shorter than the kept voice, cover `out/<id>_cover.jpg` (frame at 1.2 s, under 2 MB). `rendered` → `qa_ok`; exit 3 on FAIL |
| `host <id>` | push the MP4 + cover to the `media` branch, print raw.githubusercontent URLs pinned to the commit (skips files already there; a re-rendered MP4 is pushed again). Not jsDelivr: the media branch is over its 50 MB limit and new jsDelivr URLs answer 403 |
| `plan [--start D] [--days N] [--posts F]` | slots (13:00 and 20:00 UTC) in the window: `FILL` (reel for an empty slot; board-approved first, 30-day subject cooldown), `GAP` (a reel missing some of the four accounts), `SHORT` (nothing to post), and with a saved `list_social_posts` file `ERROR`, `MISSING` (group deleted) and `MIXING` (facemetric media on these accounts). Default: tomorrow, 1 day |
| `schedule [same args]` | `plan`, then QA + host each FILL and write `state/schedule-<date>.json`: one `create_social_post` payload per reel: the same MP4 on all four accounts, Pinterest board, caption. Each payload says its `platforms` |
| `scheduled <id> --at ISO --group G [--platforms ig,yt,threads,pinterest] [--media U --cover U]` | record a created group in scheduled.jsonl; status → `scheduled` |
| `supply [--start D] [--days 3]` | open slots vs postable reels, the next topics to make, templates still blocked; last line `SUPPLY OK` or `SUPPLY WARN` |

## Writing a topic
1. Pick a template (`rfg.sh hooks`) and the least-used one if in doubt (`rfg.sh status`). C, D and E have no single celebrity: leave `subject` empty and set `hook_card` (`head` lines, `sub`) for the topic card that replaces the name photocard. The card is optional there.
   - **E self-test** (`selftest`, 3-4 checks): each feature becomes a numbered check card above the narrator (waist-up, centred). A feature with a `subject` also shows that face as a small demo card; `marks` (image-fraction y) draws guide lines on it. RSG0010 is the worked example.
   - **C types** (`types`, 4-6): one `demo` face for every type (or a `subject` per feature), each a numbered type beat with one callout (`tag`, `at`, `crop`, `pos`). RSG0007 is the worked example.
   - **D this or that** (`compare`, 2-4 rounds): the topic sets `sides: {a: face A, b: face B}` (a feature may override with its own `sides: [A, B]`), optional `labels`, `chips`, `crops`; the topic card shows both faces with A/B.
   - CTA per kind (`pack/hooks.json` → `cta`): E "Comment which one you passed.", C "Comment your type.", D "Comment A or B." Celebrity reels end on the Axend card instead (`pack/hooks.json` → `axend`; a topic's `axend_vo` overrides the line); their caption carries "Comment who I should break down next."
2. Find a frontal Commons photo (CC BY, CC BY-SA, CC0 or PD), and put the `File:...` title in `photo.commons_file`.
3. Features: `region` is one of hair, brows, eyes, eye_colour, nose, cheekbones, lips, jaw, chin, skin. The default anchors fit a cutout whose face sits like Keoghan's. **After `restyle`, look at the cutout** and set `at` (image fractions) and `crop.y` per feature when the face sits higher or lower. Chalamet (RSG0002) is the worked example. The full-frame hook places the cutout at width 1400, left -160, top 250 (frame pixels); set `hook_crop` {w, x, y} when the face sits too high or low in the frame.
   Optional `ig_features`: the 4 feature indices (0-based) the reel keeps. Without it the reel keeps the first 4, or the 4 shortest when the first 4 would run past ~29.7 s; an A+ reel (the hook asks how the look changed) always keeps its last feature, the change.
4. Before a full render, render one still per beat to check the layout: copy `out/<id>/job`, set `still_composition: "genz-face"` and `still_frame: N` in its job.json, and run `engine/render.sh <job> <out.jpg>`. It takes about 15 s a frame.

## Rendering (Cloudflare only, SLA-1668)
- Reels render **only on Cloudflare**: `render` zips `out/<id>/job` and submits it to the `reel-remotion` Worker (`render.worker_url`, bearer `REEL_REMOTION_KEY`), which renders `genz-face` in a Container and keeps the MP4 in R2. Nothing renders on the agent box, so there is no detached process, no pid, no memory guard and no wall limit to manage.
  - The job id is kept in `state/cf-jobs.json`. `rfg.sh render <id>` is quick and idempotent: the first call submits, later calls check and download `out/<id>.mp4` when done. `--wait S` polls up to S seconds (for a one-off; the routine uses the default 0 and comes back on its monitor).
  - Several reels can be submitted at once; the Worker queues them (FIFO, one Container at a time). A Cloudflare render takes about 5-10 min plus queue time.
  - A failed or expired job is dropped from `state/cf-jobs.json` (exit 2), so the next `render` submits it again. The Worker's daily cap (HTTP 429) is a stop until 00:00 UTC; report it, don't work around it.
- `engine/` holds the composition source (`engine/compositions/genz-face/`). The Cloudflare image renders a **copy** of it in reel-factory (`scripts/renderers/remotion/compositions/genz-face/`, registered in its `compositions/index.ts`; added in reel-factory PR #104). **A change to the composition reaches renders only after it is copied there, merged to reel-factory `main` and the `deploy-reel-remotion` workflow has run.**
- `engine/render.sh` stays for one-frame layout stills only (see "Writing a topic", step 4). Never use it, or anything else on the box, for a reel MP4.
- QA and covers use ffmpeg/ffprobe: the system ones, else the binaries in `render.ffmpeg_runtime` (`$RFG_HOME/remotion-runtime/`, already built).
- `RFG_ENGINE` points the skill at another checkout of itself (tests only).
- **Axend card and music** live in the data home: `stills/brand/axend-call-2-action.png` (Manol's card, from reel-factory's `brand/axend/r2/`) and `music/*.mp3` (reel-factory's `music/facemetric/`). `script` and `render` stop with the source path when either is missing. The card says "2.9 Sub-3" / "POTENTIAL 7 Chad" next to the face in the circle; women's reels patch "Chad" to "Eve". **Payoff variant** (`axend.payoff: "axend"` in `pack/config.json`, or a topic's `payoff`; board review, 24 Nov): the Axend card replaces the game card, its panels show the reel's own score (OVR / 10 with the rarity, e.g. "8.7 · ICON") and potential (+0.6), counting up, and the line is `hooks.json` → `axend.payoff_vo`.
- `tts` keeps `work/<id>/vo/lines.json` and voices a clip again when its line changed; older work dirs without it reuse clips by index, so run `tts --force` after the beats change.
- Needs `OPEN_ROUTER_API_KEY` for restyle, copy and tts. The chroma key needs node and `sharp`; `rfg.sh` finds `/app/node_modules/.pnpm/sharp@*/node_modules` or uses `$RF_SHARP`.

## Posting (all four jenny accounts)
- Accounts and slots live in `pack/config.json` → `schedule`: Instagram `jennymaxxer`, YouTube `looksmaxxers-d1q`, Threads `jennymaxxer`, Pinterest `jennymaxxing` (board `1088323134893667526`), 13:00 and 20:00 UTC.
- The skill cannot call Slashloop. For each payload of `schedule`: `upload_social_media` on `upload.video` and `upload.thumbnail`, put the two returned URLs in `media[0].url` / `media[0].thumbnail`, `create_social_post` with `integrationIds`, `content`, `media`, `publishAt`, `settings` exactly as written, then `rfg.sh scheduled <id> --at <publishAt> --group <groupId> --platforms <payload.platforms> --media <upload.video>`.
- **Instagram trial reels: Slashloop does not expose them** (checked 24 Nov 2026, SLA-1685: `create_social_post` documents no trial option; its only Instagram setting is the cover frame). Until it does, trials are the board's: 2 reels a week posted from the Instagram app as trial reels.
- Caption = hook / line 2 + card + CTA / photo credit + "AI-edited images" / 5 hashtags. Line 2 and the hashtags come from the topic's `caption` and `tags` when set (write them by hand), else from the feature labels.
- Templates C, D and E have their layouts (SLA-1653) but stay in `schedule.blocked_templates` until the board approves the first E and C reels (RSG0010, RSG0007) on SLA-1643. Remove a template from the list on board direction only.

## Tests
`cd <skill> && python3 -m unittest discover -s tests`: hook templates, slot whitelists, lint rules, script shape, hot words, rotation and memory. No network or spend.
