# reel-famous-genz: standing decisions (the board's rules)

Read this before writing any topic or script. These rules come from Manol, the board (SLA-1643, 21-22 Nov 2026). Change them only when the board says so, and record the date.

1. **One lane, one account:** Gen Z actors and creators only (answered 22 Nov 2026). No football, no lane A/B, no per-lane variants.
2. **The format is @glowupmenclub's:** the hook is one of their spoken hooks **word for word**, with only the name, pronoun or noun swapped (`pack/hooks.json`, templates A, A+, A', B, C, D, E). The beat order is theirs too: hook with the name, then "So let's break down what his face actually has.", then 4-6 features with a callout each, then the payoff, then the CTA.
3. **Facial features, not idol roles:** explain the face the way @glowupmenclub does (eyes, brows, cheekbones, jaw, lips, hair, skin). Never place anyone in a boy group, position, concept, debut, trainee or evaluation framing.
4. **Packaging only:** the faceless K-pop narrator (Airport Idol sprites, `idol_film` outfit) and the pink K-pop glow background are the look. They never change what the script says.
5. **Payoff = the game card:** OVR plus EYE JAW SYM NOS BRW SKN, rarity RARE/HERO/GOLD/ICON. Never a score out of 10.
6. **CTA = a comment prompt** ("Comment who I should break down next."). No app, no link, no "comment link".
7. **Photos:** Wikimedia Commons only, with a per-image credit (author and licence) on screen, plus "AI-edited images". The portrait is a painted restyle, never the raw photo.
8. **Nothing gets posted** without the board approving the rendered MP4 (`rfg.sh approve <id>`). Nothing from this skill is merged into reel-factory (PR #97 closed unmerged, 22 Nov 2026).
9. **Rendering:** the skill's own Remotion engine in `engine/` (composition `genz-face` only), on this server. Nothing in reel-factory is used or changed (22 Nov 2026). The skill is only for genz-face: no qoves or facemetric code, compositions or runtime are copied in; those stay in reel-factory (board, 22 Nov 2026). The render runtime is the skill's own (`$RFG_HOME/remotion-runtime/`).
10. **Lines:** every spoken sentence is under 14 words; plain English; no looksmaxxing vocabulary (canthal, mogging, mewing, PSL, chad); no health, surgery, age or ethnicity claims.

Open: the account handle (not given yet; needed before the first post).

- 2026-11-22: renamed from `reel-soccer-genz` to **`reel-famous-genz`** by the board. The skill lives in its own repo, https://github.com/man0l/reel-famous-genz, and the data home is `data/reel-famous-genz/<company>/`. Reel IDs `RSG0001`-`RSG0010` keep their old prefix.
