---
name: reel-famous-genz
description: Make one-lane face-breakdown reels of Gen Z actors and creators in the @glowupmenclub format (their exact spoken hooks, "let's break down what his face actually has", 4-6 feature callouts on a painted Commons portrait, game-card payoff, comment CTA), packaged with the faceless K-pop narrator and pink glow background. Own memory (topic bank, subjects, hook rotation, posted log, learnings, board decisions) in its own data home; renders with its own Remotion engine (composition `genz-face`, nothing in reel-factory). Use for this account's topics, scripts, test renders, post logging and feedback. Nothing is posted without board approval.
---

# reel-famous-genz

One account, one lane: **Gen Z actors and creators** (no football, despite the name, which the board chose on 22 Nov 2026). The format is a straight clone of @glowupmenclub's face breakdowns. Only the packaging is ours: the Airport Idol narrator (faceless K-pop guy), the pink K-pop glow, and the game card instead of an app score.

**Before writing anything, read `$RFG_HOME/decisions.md` (the board's rules) and `$RFG_HOME/learnings.md`.** They are the skill's memory and they win over this file.

## Board rules (short version; full list in decisions.md)
- Hooks are @glowupmenclub's **word for word**; only `{slots}` change (`pack/hooks.json`). `lint` rejects anything else.
- Beat order: hook with the name → "So let's break down what his face actually has." → 4-6 features (one callout each) → game card (OVR + EYE JAW SYM NOS BRW SKN) → "Comment who I should break down next."
- Facial features only. No boy group, idol position, concept, debut or trainee framing; no score out of 10; no app or link; no looksmaxxing words; every spoken sentence under 14 words.
- Wikimedia Commons photos only, with the author and licence credited on screen, plus "AI-edited images".
- **Nothing is posted until the board approves the MP4** (`rfg.sh approve <id>`). Post logging is manual (`rfg.sh posted`).

## Data home (`$RFG_HOME`, default `/paperclip/instances/default/data/reel-famous-genz/<company>/`)
| File | What it holds |
|---|---|
| `decisions.md` | the board's standing rules (edit only on board direction, with a date) |
| `learnings.md` | feedback, view counts, render lessons; append with `rfg.sh learn` |
| `topics.csv` | topic bank index: id, template, subject, status (idea → ready → restyled → scripted → voiced → rendered → approved → posted, or dropped), hook, notes |
| `topics/<id>.json` | one reel: template, subject, gender, slots, Commons photo, 4-6 features (region, label, chip, vo, optional at/crop), card, cta |
| `subjects.json` | faces covered: Commons file, credit, cutout, likeness, posts (a subject cools down for 30 days after a post) |
| `hooks.jsonl` | every hook scripted, with its template id (rotation: `next` picks the least-used template) |
| `posted.jsonl` | what was posted, where, when, and stats added later |
| `faces/`, `stills/` | source photos, painted cutouts (`stills/faces/<slug>/cut.png`), narrator sprites (`stills/sprites/`) |
| `work/<id>/`, `out/<id>.mp4` | script.json, voice clips, durations; render jobs and MP4s |
| `state/spend.jsonl` | every OpenRouter call and its cost |

## Commands (`scripts/rfg.sh <cmd>`)
| Command | Does |
|---|---|
| `init` | create the data home, seed memory files (never overwrites), copy the `idol_film` narrator sprites from reel-factory |
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

## Writing a topic
1. Pick a template (`rfg.sh hooks`) and the least-used one if in doubt (`rfg.sh status`). C, D and E have no single celebrity: give each feature its own `subject` (each needs its own photo and cutout). The card is optional there.
2. Find a frontal Commons photo (CC BY, CC BY-SA, CC0 or PD), and put the `File:...` title in `photo.commons_file`.
3. Features: `region` is one of hair, brows, eyes, eye_colour, nose, cheekbones, lips, jaw, chin, skin. The default anchors fit a cutout whose face sits like Keoghan's. **After `restyle`, look at the cutout** and set `at` (image fractions) and `crop.y` per feature when the face sits higher or lower. Chalamet (RSG0002) is the worked example.
4. Before a full render, render one still per beat to check the layout: copy `out/<id>/job`, set `still_composition: "genz-face"` and `still_frame: N` in its job.json, and run `engine/render.sh <job> <out.jpg>`. It takes about 15 s a frame.

## Rendering (the skill's own engine)
- `engine/` is a self-contained Remotion renderer with one composition, `genz-face` (`engine/compositions/genz-face/`). It was copied from reel-factory's renderer, and nothing in reel-factory is needed or changed. `facemetric/` and `qoves/` under `engine/compositions/` hold only the three helper files `genz-face` imports.
- `render` runs `engine/render.sh` under its watchdog on this box. It takes about 20 min per 35 s reel.
  - It reuses the box's Remotion runtime dir (`render.vps_runtime`: node_modules, headless Chrome, and the render lock), so only one render runs on the box at a time, whichever skill starts it.
  - **Start it detached** (`setsid nohup ... &` with a log) and set `TMPDIR` inside `$RFG_HOME`. A render that is a child of the run dies when the run ends.
- There is no Cloudflare target: the reel-remotion Worker image belongs to reel-factory, and this skill doesn't deploy into it.
- `RFG_ENGINE` points the skill at another checkout of itself (tests only).
- Needs `OPEN_ROUTER_API_KEY` for restyle, copy and tts. The chroma key needs node and `sharp`; `rfg.sh` finds `/app/node_modules/.pnpm/sharp@*/node_modules` or uses `$RF_SHARP`.

## Tests
`cd <skill> && python3 -m unittest discover -s tests`: hook templates, slot whitelists, lint rules, script shape, hot words, rotation and memory. No network or spend.
