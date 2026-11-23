"""reel-famous-genz: one-lane face-breakdown reels (Gen Z actors and creators) in the @glowupmenclub format.

Memory lives in the skill's own data home (RFG_HOME). The picture is the skill's own Remotion composition `genz-face`
(engine/), rendered on this box; nothing in reel-factory is needed or changed.
Stdlib only."""
import base64, csv, fcntl, datetime as dt, json, os, re, shutil, struct, subprocess, time, urllib.error, urllib.parse, urllib.request, zipfile

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(SKILL, "pack")
COMPANY = os.environ.get("PAPERCLIP_COMPANY_ID") or "default"
HOME = os.environ.get("RFG_HOME") or "/paperclip/instances/default/data/reel-famous-genz/%s" % COMPANY
OR_BASE = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
WIKI_UA = "reel-famous-genz/1.0 (Paperclip; face-breakdown reels)"

CFG = json.load(open(os.path.join(PACK, "config.json"), encoding="utf-8"))
HOOKS = json.load(open(os.path.join(PACK, "hooks.json"), encoding="utf-8"))
TOPIC_COLS = ["id", "template", "subject", "status", "hook", "updated", "notes"]
STATUSES = ["idea", "ready", "restyled", "scripted", "voiced", "rendered", "qa_ok", "approved", "scheduled", "posted", "dropped"]


class Fatal(Exception):
    pass


def log(msg):
    print(msg, flush=True)


def p(*parts):
    return os.path.join(HOME, *parts)


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def need_env(*names):
    miss = [n for n in names if not os.environ.get(n)]
    if miss:
        raise Fatal("missing env: %s" % ", ".join(miss))


# ---------- memory (data home) ----------
def init_home():
    """Create the data home and seed the memory files that do not exist yet (never overwrites)."""
    for d in ("topics", "faces", "stills", "work", "out", "state"):
        os.makedirs(p(d), exist_ok=True)
    seed = os.path.join(SKILL, "seed")
    for name in ("decisions.md", "learnings.md", "subjects.json"):
        if not os.path.exists(p(name)):
            shutil.copyfile(os.path.join(seed, name), p(name))
    for name in ("hooks.jsonl", "posted.jsonl"):
        open(p(name), "a").close()
    if not os.path.exists(p("topics.csv")):
        shutil.copyfile(os.path.join(seed, "topics.csv"), p("topics.csv"))
    for f in os.listdir(os.path.join(seed, "topics")):
        if not os.path.exists(p("topics", f)):
            shutil.copyfile(os.path.join(seed, "topics", f), p("topics", f))
    return HOME


def topics():
    if not os.path.exists(p("topics.csv")):
        return []
    return list(csv.DictReader(open(p("topics.csv"), newline="", encoding="utf-8")))


def save_topics(rows):
    with open(p("topics.csv") + ".tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, TOPIC_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in TOPIC_COLS})
    os.replace(p("topics.csv") + ".tmp", p("topics.csv"))


def set_status(tid, status, **kv):
    if status not in STATUSES:
        raise Fatal("unknown status %r" % status)
    rows = topics()
    for r in rows:
        if r["id"] == tid:
            r["status"], r["updated"] = status, now()
            r.update({k: v for k, v in kv.items() if k in TOPIC_COLS})
            save_topics(rows)
            return r
    raise Fatal("no topic %s in topics.csv" % tid)


def topic(tid):
    f = p("topics", tid + ".json")
    if not os.path.exists(f):
        raise Fatal("no topic file topics/%s.json" % tid)
    t = json.load(open(f, encoding="utf-8"))
    t.setdefault("id", tid)
    return t


def save_topic(t):
    json.dump(t, open(p("topics", t["id"] + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def subjects():
    try:
        return json.load(open(p("subjects.json"), encoding="utf-8"))
    except Exception:
        return {}


def save_subjects(s):
    json.dump(s, open(p("subjects.json") + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(p("subjects.json") + ".tmp", p("subjects.json"))


def jsonl(name):
    if not os.path.exists(p(name)):
        return []
    return [json.loads(l) for l in open(p(name), encoding="utf-8") if l.strip()]


def append(name, rec):
    with open(p(name), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def spend(kind, usd, **kw):
    append("state/spend.jsonl", {"t": now(), "run": os.environ.get("PAPERCLIP_RUN_ID", ""), "kind": kind, "usd": usd or 0, **kw})


# ---------- hooks ----------
def pron(t):
    return {"he": "she", "his": "her", "him": "her"} if t.get("gender") == "W" else {"he": "he", "his": "his", "him": "him"}


def fill(text, slots):
    """{slot} -> value; {Slot} -> the value capitalised (sentence-initial pronouns: "{He} was every girl's crush.")."""
    def sub(m):
        k = m.group(1)
        if k in slots:
            return slots[k]
        if k[:1].isupper() and k.lower() in slots:
            v = slots[k.lower()]
            return v[:1].upper() + v[1:]
        raise Fatal("hook slot {%s} has no value" % k)
    return re.sub(r"\{(\w+)\}", sub, text)


def slots_of(t):
    s = dict(t.get("slots") or {})
    s.setdefault("name", t.get("subject", ""))
    s.update({k: v for k, v in pron(t).items() if k not in s})
    s.setdefault("crush_of", "guy" if t.get("gender") == "W" else "girl")
    return s


def hook_lines(t):
    """The hook sentences of a topic: its template's lines with the slots filled (the only allowed difference from @glowupmenclub)."""
    tpl = HOOKS["templates"].get(t["template"])
    if not tpl:
        raise Fatal("unknown hook template %r (have %s)" % (t["template"], ", ".join(HOOKS["templates"])))
    s = slots_of(t)
    for k, allowed in (tpl.get("slots") or {}).items():
        if s.get(k) not in allowed:
            raise Fatal("template %s slot {%s}=%r is not one of %s" % (t["template"], k, s.get(k), allowed))
    return [fill(l, s) for l in tpl["lines"]]


def bridge_line(t):
    kind = HOOKS["templates"][t["template"]]["kind"]
    return fill(HOOKS["bridge"][kind], slots_of(t))


# ---------- lint ----------
SCORE10 = re.compile(r"\b\d+(?:\.\d+)?\s*/\s*10\b|\bout of (?:10|ten)\b", re.I)


def lint_text(text, where):
    out, low, L = [], text.lower(), CFG["lint"]
    for b in L["banned"] + L["banned_names"]:
        if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(b), low):
            out.append("%s: banned %r in %r" % (where, b, text))
    if L.get("no_score_out_of_10") and SCORE10.search(text):
        out.append("%s: score out of 10 in %r" % (where, text))
    return out


def lint_vo(vo, where):
    out = lint_text(vo, where)
    for sent in re.split(r"(?<=[.?!])\s+", vo.strip()):
        n = len(sent.split())
        if n > CFG["lint"]["max_line_words"]:
            out.append("%s: spoken line has %d words (max %d): %r" % (where, n, CFG["lint"]["max_line_words"], sent))
    return out


def lint_script(script, t):
    """Every rule of the account (decisions.md) that a machine can check. Returns a list of problems (empty = ok)."""
    out = []
    beats = script["beats"]
    kind = HOOKS["templates"][t["template"]]["kind"]
    want = " ".join(hook_lines(t))
    if not beats or beats[0]["vo"] != want:
        out.append("hook: must be the @glowupmenclub template %s word for word: %r" % (t["template"], want))
    hook_kind = "hook" if kind == "celebrity" else "topic"
    if beats and beats[0]["kind"] != hook_kind:
        out.append("hook: a %s reel opens on the %s beat (%s), not %r" % (kind, hook_kind, "name photocard" if kind == "celebrity" else "topic card, no name", beats[0]["kind"]))
    if len(beats) < 2 or beats[1]["kind"] != "narrator" or beats[1]["vo"] != bridge_line(t):
        out.append("bridge: must be %r" % bridge_line(t))
    lo, hi = body_range(kind)
    nf = sum(1 for b in beats if b["kind"] == BODY[kind])
    if not lo <= nf <= hi:
        out.append("%s: %d %s beats (want %d-%d)" % (BODY[kind], nf, BODY[kind], lo, hi))
    kinds = [b["kind"] for b in beats]
    if kind == "celebrity" and "walkout" not in kinds:
        out.append("payoff: a celebrity breakdown ends on the game card (walkout beat)")
    if kinds[-1] != "cta":
        out.append("cta: the last beat must be the comment prompt")
    elif not beats[-1]["vo"].startswith("Comment "):
        out.append("cta: the comment prompt starts with \"Comment \": %r" % beats[-1]["vo"])
    for i, b in enumerate(beats):
        where = "beat %d (%s)" % (i, b["kind"])
        out += lint_vo(b["vo"], where) if i else lint_text(b["vo"], where)
        for s in screen_texts(b):
            out += lint_text(s, where + " on screen")
        for c in b.get("callouts") or []:
            right = label_right(c["pos"], c.get("label", ""))
            if right > 1060:
                out.append("%s: callout %r ends at x=%d, past the frame (max 1060); move pos left" % (where, c.get("label"), right))
    for s in faces_of(t):
        if not credit_of(t, s):
            out.append("credit: no photo credit for %s (Commons author + licence)" % s)
    return out


def screen_texts(b):
    out = list(b.get("head") or []) if isinstance(b.get("head"), list) else [b.get("head") or ""]
    out += b.get("lines") or []
    for c in b.get("callouts") or []:
        out += [c.get("label", ""), c.get("chip", "")]
    out += b.get("pills") or []
    out += b.get("labels") or []
    out += b.get("chips") if isinstance(b.get("chips"), list) and all(isinstance(x, str) for x in b["chips"]) else []
    out += [b.get("tease") or "", b.get("sub") or "", b.get("name") or "", b.get("title") or "", b.get("chip") or ""]
    return [x for x in out if x]


# ---------- script ----------
def first(name):
    return name.split()[0]


def head_lines(text, width=15):
    """Hook headline: upper-case words wrapped at ~width characters, at most 4 lines; the last line is the accent (*...*)."""
    words, lines, cur = text.upper().split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    if len(lines) > 4:
        lines = lines[:3] + [" ".join(lines[3:])]
    lines[-1] = "*%s*" % lines[-1]
    return lines


def bare(w):
    return re.sub(r"[^\w]+", "", w.lower())


def hot_of(vo, want):
    """Hot words must be spoken words of the beat (the caption highlights them)."""
    spoken = {bare(w) for w in vo.split()}
    return [w for w in want if bare(w) in spoken][:3]


def region(f):
    r = CFG["regions"].get(f.get("region", ""))
    if not r:
        raise Fatal("feature %r: unknown region %r (have %s)" % (f.get("label"), f.get("region"), ", ".join(k for k in CFG["regions"] if not k.startswith("$"))))
    return r


CALLOUT_RIGHT = 1040  # right edge a callout label may reach; lint fails past 1060


def label_right(pos, label):
    """Right edge of a callout's label box: the same width estimate as calloutBox in engine geometry.ts (the label is nowrap)."""
    return pos[0] + len(label) * 30 + 44


def fit_pos(pos, label):
    """Shift a callout left so its label ends inside the frame; the region slots are placed for short labels."""
    return [max(40, min(pos[0], CALLOUT_RIGHT - (label_right(pos, label) - pos[0]))), pos[1]]


def feature_beat(f, img):
    r = region(f)
    label = f["label"].upper()
    c = {"at": f.get("at") or r["at"], "label": label, "pos": fit_pos(f.get("pos") or r["pos"], label)}
    if f.get("chip"):
        c["chip"] = f["chip"]
    c["w"] = f.get("w") or (640 if c["pos"][0] < 300 else 460)
    b = {"kind": "feature", "img": img, "crop": f.get("crop") or r["crop"], "callouts": [c], "vo": f["vo"]}
    hot = hot_of(f["vo"], f.get("hot") or f["label"].lower().split()[-1:])
    if hot:
        b["hot"] = hot
    return b


def png_ratio(path, default=1.3):
    try:
        with open(path, "rb") as f:
            h = f.read(24)
        w, ht = struct.unpack(">II", h[16:24])
        return round(ht / w, 4)
    except Exception:
        return default


def cut_rel(subject):
    return "faces/%s/cut.png" % slug(subject)


def sprite_assets():
    sp = CFG["sprites"]
    sprites, assets = {}, {}
    for pose in sp["poses"] + sp["pending"]:
        rel = "sprites/%s_%s.png" % (sp["outfit"], pose)
        if os.path.exists(p("stills", rel)):
            sprites[pose], assets["idol_" + pose] = "idol_" + pose, rel
    if not sprites:
        raise Fatal("no narrator sprites in %s (expected %s_<pose>.png)" % (p("stills", "sprites"), sp["outfit"]))
    return sprites, assets


# body beat of each hook kind: celebrity features, self-test checks (E), numbered types (C), this-or-that rounds (D)
BODY = {"celebrity": "feature", "selftest": "check", "types": "type", "compare": "versus"}


def body_range(kind):
    r = (CFG["features"].get("by_kind") or {}).get(kind)
    return tuple(r) if r else (CFG["features"]["min"], CFG["features"]["max"])


def sides_of(t):
    sd = t.get("sides") or {}
    return [sd[k] for k in ("a", "b") if sd.get(k)]


def faces_of(t):
    """Every painted face the reel shows: the subject (celebrity), the demo face (C, E), the A/B faces (D) and per-feature faces, in order."""
    names = [t.get("subject") or "", t.get("demo") or ""] + sides_of(t) + [f.get("subject") or "" for f in t.get("features") or []]
    return [n for n in dict.fromkeys(names) if n]


def credit_of(t, s):
    """Commons credit of a face: the topic's photo for its own subject, else subjects.json, else any topic that has that subject."""
    if s == t.get("subject") and (t.get("photo") or {}).get("credit"):
        return t["photo"]["credit"]
    cr = (subjects().get(slug(s)) or {}).get("credit")
    if cr:
        return cr
    d = p("topics")
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        try:
            o = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception:
            continue
        if o.get("subject") == s and (o.get("photo") or {}).get("credit"):
            return o["photo"]["credit"]
    return None


def body_beat(kind, f, i, key):
    """One body beat of a self-diagnosis reel. `key(name)` -> asset key of a face."""
    title = f["label"].upper()
    hot = hot_of(f["vo"], f.get("hot") or f["label"].lower().split()[-1:])
    if kind == "selftest":
        b = {"kind": "check", "n": i + 1, "title": title, "vo": f["vo"]}
        if f.get("chip"):
            b["chip"] = f["chip"]
        if f.get("subject"):
            b["img"] = key(f["subject"])
            for k in ("marks", "demo_crop"):
                if f.get(k):
                    b[k] = f[k]
    elif kind == "types":
        r = region(f)
        label = (f.get("tag") or f["region"].replace("_", " ")).upper()
        c = {"at": f.get("at") or r["at"], "label": label, "pos": fit_pos(f.get("pos") or r["pos"], label)}
        if f.get("chip"):
            c["chip"] = f["chip"]
        c["w"] = f.get("w") or (640 if c["pos"][0] < 300 else 460)
        b = {"kind": "type", "n": i + 1, "title": title, "img": key(f["subject"]), "crop": f.get("crop") or r["crop"], "callouts": [c], "vo": f["vo"]}
    else:
        b = {"kind": "versus", "title": title, "imgs": [key(f["sides"][0]), key(f["sides"][1])], "vo": f["vo"]}
        for k in ("labels", "chips", "crops"):
            if f.get(k):
                b[k] = f[k]
    if hot:
        b["hot"] = hot
    return b


def build_script(t):
    """Topic -> script.json for the `genz-face` composition in engine/ (lane B tokens, kpop stage), in the @glowupmenclub beat order.
    Celebrity (A, A', A+, B): name photocard hook -> "so let's break down what his face actually has" -> 4-6 features with callouts -> game card -> comment prompt.
    Self-diagnosis (no celebrity): topic-card hook -> bridge -> E: 3-4 numbered checks on the narrator / C: numbered types on one demo face /
    D: A/B rounds side by side -> optional turn -> the kind's comment prompt."""
    kind = HOOKS["templates"][t["template"]]["kind"]
    name = t.get("subject") or ""
    if kind == "celebrity" and not name:
        raise Fatal("%s: a celebrity breakdown needs `subject`" % t["id"])
    pr = pron(t)
    feats = [dict(f) for f in t.get("features") or []]
    lo, hi = body_range(kind)
    if not lo <= len(feats) <= hi:
        raise Fatal("%s: a %s reel needs %d-%d features, has %d" % (t["id"], kind, lo, hi, len(feats)))
    missing = [f.get("label") for f in feats if not f.get("vo")]
    if missing:
        raise Fatal("%s: features without a spoken line (run `rfg.sh copy %s` or write `vo`): %s" % (t["id"], t["id"], ", ".join(map(str, missing))))
    sides = sides_of(t)
    if kind == "types":
        for f in feats:
            f["subject"] = f.get("subject") or t.get("demo")
            if not f["subject"]:
                raise Fatal("%s: a types reel needs `demo` (the face for the types) or a `subject` per feature" % t["id"])
    if kind == "compare":
        if len(sides) != 2:
            raise Fatal("%s: a this-or-that reel needs `sides` {a, b} (two faces)" % t["id"])
        for f in feats:
            f["sides"] = f.get("sides") or sides
    sprites, sassets = sprite_assets()
    faces = faces_of(dict(t, features=feats))
    assets, ratios = dict(sassets), {}
    key = lambda s: "cut" if (not s or s == name) else "cut_" + slug(s)
    for s in faces:
        rel = cut_rel(s)
        if not os.path.exists(p("stills", rel)):
            raise Fatal("%s: no painted cutout for %s (run `rfg.sh restyle %s`)" % (t["id"], s, t["id"]))
        assets[key(s)], ratios[key(s)] = rel, png_ratio(p("stills", rel))
    ep = int(t.get("ep") or re.sub(r"\D", "", t["id"]) or 1)
    hook = hook_lines(t)
    if kind == "celebrity":
        hb = {"kind": "hook", "img": "cut", "head": head_lines(hook[0]), "card": [first(name).upper(), t.get("card_line") or "face file · ep.%02d" % ep],
              "badge": CFG["badge"], "vo": " ".join(hook)}
        if len(hook) > 1:
            hb["sub"] = hook[1].lower() if len(hook[1]) < 70 else hook[1]
        hb["hot"] = hot_of(hb["vo"], [first(name), "attractive", "viral"])
    else:
        hc = t.get("hook_card") or {}
        hb = {"kind": "topic", "head": hc.get("head") or head_lines(hook[0]), "vo": " ".join(hook)}
        if hc.get("sub"):
            hb["sub"] = hc["sub"]
        if kind == "types":
            hb["imgs"] = [key(t.get("demo") or feats[0]["subject"])]
        elif kind == "compare":
            hb["imgs"], hb["labels"] = [key(s) for s in sides], (t.get("sides") or {}).get("labels") or ["A", "B"]
        elif kind == "selftest":
            hb["pills"] = [str(i + 1) for i in range(len(feats))]
        hb["hot"] = hot_of(hb["vo"], hc.get("hot") or ["easy", "attractive", "types", "attractive?"])
    beats = [hb]
    br = bridge_line(t)
    blines = t.get("bridge_lines") or HOOKS.get("bridge_lines", {}).get(kind) or ["so let's break down", "what %s face" % pr["his"], "*actually has.*"]
    beats.append({"kind": "narrator", "lines": blines, "vo": br, "hot": hot_of(br, ["face", "actually", "check", "one", "side"])})
    for i, f in enumerate(feats):
        beats.append(feature_beat(f, key(f.get("subject"))) if kind == "celebrity" else body_beat(kind, f, i, key))
    turn = t.get("turn")
    if turn:
        beats.append({"kind": "narrator", "lines": turn["lines"], "vo": turn["vo"], "hot": hot_of(turn["vo"], turn.get("hot") or [])})
    card = t.get("card")
    if kind == "celebrity" or (card and name):
        if not card:
            raise Fatal("%s: a celebrity breakdown needs `card` (ovr, rarity, stats)" % t["id"])
        stats = card["stats"]
        miss = [k for k in CFG["card"]["stats"] if k not in stats]
        if miss or card.get("rarity") not in CFG["card"]["rarity"]:
            raise Fatal("%s: card needs stats %s and rarity in %s" % (t["id"], CFG["card"]["stats"], CFG["card"]["rarity"]))
        vo = card.get("vo") or "Put it all together and %s face card comes out at %d." % (pr["his"], int(card["ovr"]))
        beats.append({"kind": "walkout", "img": "cut", "name": name.upper(), "sub": card.get("sub") or "face card", "ovr": int(card["ovr"]), "rarity": card["rarity"],
                      "stats": [[k, int(stats[k])] for k in CFG["card"]["stats"]], "vo": vo, "hot": hot_of(vo, [str(card["ovr"]), "card"])})
    dflt = HOOKS.get("cta", {}).get(kind) or {}
    cta = t.get("cta") or {}
    nxt = t.get("next") or []
    pills = cta.get("pills") or dflt.get("pills") or [x.upper() for x in nxt[:4]] or ["WHO'S NEXT?"]
    if pills == "#":
        pills = [str(i + 1) for i in range(len(feats))]
    if len(pills) < 2:
        pills = pills + ["SOMEONE ELSE"]
    cvo = cta.get("vo") or dflt.get("vo") or "Comment who I should break down next."
    c = {"kind": "cta", "head": cta.get("head") or dflt.get("head") or ["COMMENT", "WHO'S *NEXT*"], "pills": pills, "vo": cvo,
         "hot": hot_of(cvo, cta.get("hot") or ["next", "comment", "passed", "type", "A", "B"])}
    if cta.get("tease"):
        c["tease"] = cta["tease"]
    beats.append(c)
    credits = []
    for s in faces:
        cr = credit_of(t, s)
        if not cr:
            raise Fatal("%s: no photo credit for %s" % (t["id"], s))
        if cr not in credits:
            credits.append(cr)
    cite = "Portraits painted from photos by %s, Wikimedia Commons" % "; ".join(credits) if len(credits) > 1 else "Portrait painted from a photo by %s, Wikimedia Commons" % credits[0]
    out = {"format": "genz-face", "reel_id": t["id"], "template": t["template"], "footer": CFG["footer"], "lane": CFG["lane"], "lens": CFG["lens"],
           "episode_type": "celebrity" if kind == "celebrity" else "self_diagnosis", "tag": {"en": CFG["tag"] % ep},
           "cite": "%s · %s" % (cite, CFG["footer"]), "hangul": False, "assets": assets, "sprites": sprites, "ratios": ratios, "beats": beats, "sfx": True}
    if name:
        out["name"] = name
    return out


# ---------- OpenRouter ----------
def _post(path, body, timeout=600):
    need_env("OPEN_ROUTER_API_KEY")
    req = urllib.request.Request(OR_BASE + path, json.dumps(body).encode(), {"Authorization": "Bearer " + os.environ["OPEN_ROUTER_API_KEY"], "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout)), None
    except urllib.error.HTTPError as e:
        return None, "HTTP %s %s" % (e.code, e.read()[:300].decode(errors="replace"))
    except Exception as e:
        return None, repr(e)


def durl(path):
    ext = path.lower().rsplit(".", 1)[-1]
    mt = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
    return "data:%s;base64,%s" % (mt, base64.b64encode(open(path, "rb").read()).decode())


def chat_json(prompt, imgs=(), kind="qa", model=None):
    content = [{"type": "text", "text": prompt}] + [{"type": "image_url", "image_url": {"url": durl(i)}} for i in imgs]
    r, err = _post("/chat/completions", {"model": model or CFG["restyle"]["qa_model"], "messages": [{"role": "user", "content": content}],
                                         "response_format": {"type": "json_object"}, "usage": {"include": True}}, 300)
    if err:
        return {"pass": False, "notes": err}, 0
    cost = (r.get("usage") or {}).get("cost") or 0
    spend(kind, cost)
    txt = r["choices"][0]["message"]["content"].strip().strip("`").removeprefix("json").strip()
    try:
        return json.loads(txt), cost
    except Exception:
        return {"pass": False, "notes": "unparseable: " + txt[:200]}, cost


def gen_image(prompt, out, ref, aspect):
    content = [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": durl(ref)}}]
    body = {"model": CFG["restyle"]["model"], "messages": [{"role": "user", "content": content}], "modalities": ["image", "text"], "usage": {"include": True},
            "image_config": {"aspect_ratio": aspect}}
    r, err = _post("/chat/completions", body)
    if err:
        return 0, err
    try:
        url = (r["choices"][0]["message"].get("images") or [])[0]["image_url"]["url"]
        data = base64.b64decode(url.split(",", 1)[1])
    except (KeyError, IndexError, TypeError, ValueError):
        return 0, "no image in reply " + json.dumps(r)[:300]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(data)
    cost = (r.get("usage") or {}).get("cost") or 0
    spend("image", cost)
    return cost, None


def tts(text, out):
    a = CFG["audio"]
    body = {"model": a["model"], "voice": a["voice"], "response_format": "mp3", "input": text}
    if a.get("speed"):
        body["speed"] = a["speed"]
    need_env("OPEN_ROUTER_API_KEY")
    req = urllib.request.Request(OR_BASE + "/audio/speech", json.dumps(body).encode(), {"Authorization": "Bearer " + os.environ["OPEN_ROUTER_API_KEY"], "Content-Type": "application/json"})
    try:
        data = urllib.request.urlopen(req, timeout=120).read()
    except urllib.error.HTTPError as e:
        raise Fatal("tts HTTP %s %s" % (e.code, e.read()[:200].decode(errors="replace")))
    open(out + ".part", "wb").write(data)
    os.replace(out + ".part", out)
    spend("tts", round(len(text) * 0.017 / 1000, 6), chars=len(text))


_BR = {1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320], 2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]}
_SR = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def mp3_duration(path):
    d = open(path, "rb").read(); i = 0; t = 0.0
    if d[:3] == b"ID3":
        i = 10 + ((d[6] << 21) | (d[7] << 14) | (d[8] << 7) | d[9])
    while i + 4 <= len(d):
        if d[i] != 0xFF or (d[i + 1] & 0xE0) != 0xE0:
            i += 1; continue
        ver = (d[i + 1] >> 3) & 3; bi = d[i + 2] >> 4; si = (d[i + 2] >> 2) & 3; pad = (d[i + 2] >> 1) & 1
        if ver == 1 or bi in (0, 15) or si == 3:
            i += 1; continue
        sr = _SR[ver][si]; br = _BR[1 if ver == 3 else 2][bi] * 1000
        spf = 1152 if ver == 3 else 576
        i += spf // 8 * br // sr + pad; t += spf / sr
    return t


# ---------- photos (Wikimedia Commons only) ----------
# Commons only serves these thumbnail widths (https://w.wiki/GHai); any other width is a 400, and the
# unscaled original (what a width >= the file's own width returns) is rate-limited with 429.
COMMONS_WIDTHS = (1920, 1280, 960, 500)


def commons_info(file_title):
    """(thumb url, credit 'Author, Licence') of a Commons file title like 'File:Timothée Chalamet-63541.jpg'."""
    def query(width):
        q = urllib.parse.urlencode({"action": "query", "format": "json", "titles": file_title, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": str(width)})
        d = json.load(urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + q, headers={"User-Agent": WIKI_UA}), timeout=60))
        return next(iter(d["query"]["pages"].values()))
    page = query(1280)
    if "imageinfo" not in page:
        raise Fatal("Commons has no file %r" % file_title)
    ii = page["imageinfo"][0]
    w = next((x for x in COMMONS_WIDTHS if x <= 1280 and x < ii.get("width", 0)), None)
    if w and w != 1280:
        ii = query(w)["imageinfo"][0]
    m = ii.get("extmetadata") or {}
    artist = re.sub(r"<[^>]+>", "", (m.get("Artist") or {}).get("value", "")).strip()
    lic = (m.get("LicenseShortName") or {}).get("value", "").strip()
    if not artist or not lic:
        raise Fatal("Commons file %r has no author or licence metadata" % file_title)
    return ii.get("thumburl") or ii["url"], "%s, %s" % (artist, lic)


def fetch_photo(t):
    """Download the topic's Commons photo into faces/<slug>/source.jpg and record the credit in subjects.json."""
    ph = t.get("photo") or {}
    if not ph.get("commons_file"):
        raise Fatal("%s: topic has no photo.commons_file (a Wikimedia Commons file title)" % t["id"])
    dest = p("faces", slug(t["subject"]), "source.jpg")
    url, credit = commons_info(ph["commons_file"])
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": WIKI_UA}), timeout=120).read()
        if not (data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG"):
            raise Fatal("Commons download of %s is not an image" % ph["commons_file"])
        open(dest, "wb").write(data)
    ph["credit"] = ph.get("credit") or credit
    t["photo"] = ph
    save_topic(t)
    subs = subjects()
    s = subs.setdefault(slug(t["subject"]), {"name": t["subject"]})
    s.update({"commons_file": ph["commons_file"], "credit": ph["credit"], "photo": os.path.relpath(dest, HOME)})
    save_subjects(subs)
    return dest


def key_png(src, dst):
    r = subprocess.run(["node", os.path.join(PACK, "key.mjs"), src, dst], capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(dst):
        raise Fatal("chroma key failed (set RF_SHARP to a node_modules dir with sharp): %s" % (r.stderr or r.stdout)[-300:])


def restyle(t, tries=2):
    """Painted-portrait restyle of the subject (Gemini on flat magenta, QA likeness >= 8, chroma key). Returns USD spent."""
    dest = p("stills", cut_rel(t["subject"]))
    if os.path.exists(dest):
        return 0.0
    src = p("faces", slug(t["subject"]), "source.jpg")
    if not os.path.exists(src):
        src = fetch_photo(t)
    st, spent, last = CFG["restyle"], 0.0, {}
    work = p("work", "_paint", slug(t["subject"]))
    for i in range(tries):
        out = os.path.join(work, "paint_%d.png" % i)
        cost, err = gen_image(st["prompt"].format(style=st["style"]), out, src, st["aspect"])
        spent += cost
        if err:
            last = {"notes": err}; continue
        v, c = chat_json(st["qa"].format(name=t["subject"]), [src, out])
        spent += c
        last = v
        # Gate on likeness + style only: the model's own "pass" also wants realism >= 7, which a painterly
        # portrait never gets, so it rejected 7 of 7 good likenesses (22-23 Nov).
        if (v.get("likeness") or 0) >= 8 and v.get("style_ok"):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            key_png(out, dest)
            subs = subjects()
            subs.setdefault(slug(t["subject"]), {"name": t["subject"]}).update({"cutout": os.path.relpath(dest, HOME), "likeness": v.get("likeness")})
            save_subjects(subs)
            return spent
    raise Fatal("no painted cutout of %s passed QA ($%.3f spent): %s" % (t["subject"], spent, last.get("notes", "")))


def restyle_all(t):
    """Restyle every face the reel shows that has no cutout yet (subject, demo, A/B sides, per-feature faces). Returns USD spent."""
    usd = 0.0
    for s in faces_of(t):
        if os.path.exists(p("stills", cut_rel(s))):
            continue
        usd += restyle(t if s == t.get("subject") else dict(t, subject=s, photo=(subjects().get(slug(s)) or {})))
    return usd


# ---------- copy (optional LLM help for missing feature lines) ----------
COPY_PROMPT = """Write the spoken voice-over for a face-breakdown short in the style of @glowupmenclub: calm, confident, plain English, explains why each feature works.
Subject: {name}. Features in order (one line each): {features}
Rules: every sentence under 14 words, one or two sentences per feature, name the feature plainly, no emojis, no score out of 10, never mention an app, a link or face analysis,
no looksmaxxing words (canthal, mogging, mewing, PSL, chad), no health, surgery, age or ethnicity claims, no boy group or idol framing, never name a studio, show or film.
Reply JSON only: {{"feature_vo": [{n} strings]}}"""


def llm_feature_lines(t):
    feats = t["features"]
    desc = " | ".join("%d. %s (%s)" % (i + 1, f["label"], f.get("chip") or f.get("region")) for i, f in enumerate(feats))
    v, _ = chat_json(COPY_PROMPT.format(name=t.get("subject") or "a self-test for the viewer (no celebrity)", features=desc, n=len(feats)), kind="script")
    lines = v.get("feature_vo")
    if not isinstance(lines, list) or len(lines) != len(feats):
        raise Fatal("LLM reply has no usable feature_vo: %s" % str(v)[:200])
    bad = [x for i, l in enumerate(lines) for x in lint_vo(l, "feature %d" % i)]
    if bad:
        raise Fatal("LLM lines failed lint: %s" % "; ".join(bad[:3]))
    return lines


# ---------- render (the skill's own engine) ----------
def engine():
    """The skill's own Remotion renderer (engine/, the `genz-face` composition only). $RFG_ENGINE overrides it for testing."""
    c = os.environ.get("RFG_ENGINE") or SKILL
    if os.path.exists(os.path.join(c, "engine", "compositions", CFG["composition"], "Reel.tsx")):
        return c
    raise Fatal("no engine/ with the %r composition in %s" % (CFG["composition"], c))


def build_job(tid):
    """out/<id>/job: job.json + script.json (with durations) + public/ (cutouts, sprites, voice, fonts, sfx)."""
    wd = p("work", tid)
    script = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    script["durations"] = json.load(open(os.path.join(wd, "durations.json")))
    job = p("out", tid, "job")
    shutil.rmtree(job, ignore_errors=True)
    pub = os.path.join(job, "public")
    os.makedirs(pub)
    for rel in script["assets"].values():
        src = p("stills", rel)
        if not os.path.exists(src):
            raise Fatal("missing asset %s" % rel)
        os.makedirs(os.path.dirname(os.path.join(pub, rel)), exist_ok=True)
        shutil.copyfile(src, os.path.join(pub, rel))
    shutil.copytree(os.path.join(wd, "vo"), os.path.join(pub, "vo"))
    eng_fonts = os.path.join(engine(), "engine", "fonts")
    os.makedirs(os.path.join(pub, "fonts"))
    for d in (eng_fonts, os.path.join(PACK, "fonts")):
        for f in (os.listdir(d) if os.path.isdir(d) else []):
            shutil.copyfile(os.path.join(d, f), os.path.join(pub, "fonts", f))
    os.makedirs(os.path.join(pub, "sfx"))
    for f in os.listdir(os.path.join(PACK, "sfx")):  # stored as base64 text: the skill library only takes UTF-8 files
        if f.endswith(".b64"):
            with open(os.path.join(PACK, "sfx", f)) as src, open(os.path.join(pub, "sfx", f[:-4]), "wb") as dst:
                dst.write(base64.b64decode(src.read()))
    music = sorted(os.listdir(p("music"))) if os.path.isdir(p("music")) else []
    if music:
        pick = music[sum(map(ord, tid)) % len(music)]
        os.makedirs(os.path.join(pub, "music"), exist_ok=True)
        shutil.copyfile(p("music", pick), os.path.join(pub, "music", pick))
        script["music"] = {"src": "music/" + pick, "volume": 0.12, "fade_in": 0.3, "fade_out": 1.2}
    json.dump(script, open(os.path.join(job, "script.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"reel_id": tid, "format": "reel-famous-genz", "template": script.get("template", ""), "composition": CFG["composition"]}, open(os.path.join(job, "job.json"), "w"))
    return job


class Pending(Exception):
    """A Cloudflare render is queued or running; the job id is kept in state/cf-jobs.json and the next `render` call collects it."""


CF = CFG["render"]


def cf_url():
    return (os.environ.get("REEL_REMOTION_URL") or CF["worker_url"]).rstrip("/")


def cf_req(method, path, data=None, ctype=None, timeout=60):
    key = os.environ.get("REEL_REMOTION_KEY")
    if not key:
        raise Fatal("REEL_REMOTION_KEY is not set (bearer for the reel-remotion Worker)")
    h = {"user-agent": WIKI_UA, "authorization": "Bearer " + key}
    if ctype:
        h["content-type"] = ctype
    try:
        r = urllib.request.urlopen(urllib.request.Request(cf_url() + path, data=data, method=method, headers=h), timeout=timeout)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:500]


def cf_json(method, path, body=None, timeout=60):
    st, raw = cf_req(method, path, json.dumps(body).encode() if body is not None else None, "application/json" if body is not None else None, timeout)
    try:
        return st, json.loads(raw)
    except Exception:
        return st, {"error": raw[:300].decode(errors="replace")}


def cf_jobs():
    try:
        return json.load(open(p("state", "cf-jobs.json")))
    except Exception:
        return {}


def cf_set(tid, jid=None):
    """Record (or with jid=None drop) one reel's job under a lock, re-reading the file: several runs share cf-jobs.json, and
    writing back a stale copy dropped another run's jobs (SLA-1655, 23 Nov)."""
    os.makedirs(p("state"), exist_ok=True)
    with open(p("state", "cf-jobs.lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        j = cf_jobs()
        if jid:
            j[tid] = jid
        else:
            j.pop(tid, None)
        tmp = p("state", "cf-jobs.json.%d.tmp" % os.getpid())
        json.dump(j, open(tmp, "w"), indent=1)
        os.replace(tmp, p("state", "cf-jobs.json"))


def cf_submit(tid, job):
    """Zip out/<id>/job, upload it in parts to the reel-remotion Worker and queue it. Returns the remote job id."""
    zp = p("out", tid, "job.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for root, _, files in os.walk(job):
            for f in sorted(files):
                z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), job))
    size, part = os.path.getsize(zp), int(CF["part_bytes"])
    n = max(1, -(-size // part))
    st, j = cf_json("POST", "/jobs", {"reel_id": tid, "composition": CFG["composition"], "parts": n, "bytes": size})
    if st == 429:
        raise Fatal("reel-remotion daily cap reached (%s of %s today); render again after 00:00 UTC" % (j.get("used", "?"), j.get("cap", "?")))
    if st != 201:
        raise Fatal("reel-remotion refused the job: HTTP %s %s" % (st, str(j)[:200]))
    with open(zp, "rb") as f:
        for i in range(n):
            data = f.read(part)
            for attempt in range(5):
                st, raw = cf_req("PUT", "/jobs/%s/parts/%d" % (j["id"], i), data, "application/octet-stream", 300)
                if st == 200:
                    break
                if attempt == 4:
                    raise Fatal("upload of part %d/%d failed: HTTP %s %s" % (i + 1, n, st, raw[:120]))
                time.sleep(3 * 2 ** attempt)
    st, r = cf_json("POST", "/jobs/%s/start" % j["id"])
    if st != 202:
        raise Fatal("could not queue the job: HTTP %s %s" % (st, str(r)[:200]))
    os.remove(zp)
    log("%s: submitted to reel-remotion as job %s (%.1f MB, %d part(s))" % (tid, j["id"], size / 1e6, n))
    return j["id"]


def render_cloudflare(tid, wait=0):
    """Render out/<id>.mp4 on the reel-remotion Worker (Cloudflare Container; the genz-face composition is baked into its image).
    Submits the job unless one is already recorded, then polls for up to `wait` seconds. Raises Pending while it is still queued or
    running (the job id stays in state/cf-jobs.json, so the next call resumes), Fatal when the Worker fails it (the record is dropped,
    so the next call submits again)."""
    jid = cf_jobs().get(tid)
    if not jid:
        jid = cf_submit(tid, build_job(tid))
        cf_set(tid, jid)
    deadline = time.time() + wait
    while True:
        st, j = cf_json("GET", "/status/" + jid, timeout=30)
        state = j.get("state") if st == 200 else ("gone" if st == 404 else "unreachable")
        if state == "done":
            break
        if state in ("failed", "gone"):
            cf_set(tid)
            raise Fatal("reel-remotion job %s %s: %s (render again to resubmit)" % (jid, state, str(j.get("error", ""))[:300]))
        if time.time() >= deadline:
            prog = "%s %d%%" % (j.get("phase"), int(float(j.get("progress") or 0) * 100)) if j.get("phase") else ""
            queue = "queue position %s" % j["queue_position"] if j.get("queue_position") else ""
            raise Pending("%s: job %s is %s %s; run `rfg.sh render %s` again to collect it" % (tid, jid, state, prog or queue, tid))
        time.sleep(15)
    st, data = cf_req("GET", "/out/%s.mp4" % jid, timeout=300)
    if st != 200 or len(data) < 20000 or data[4:8] != b"ftyp":
        raise Pending("%s: job %s is done but the MP4 download failed (HTTP %s, %d bytes); run render again" % (tid, jid, st, len(data)))
    out = p("out", tid + ".mp4")
    with open(out + ".part", "wb") as fh:
        fh.write(data)
    os.replace(out + ".part", out)
    cf_set(tid)
    return out


# ---------- rotation ----------
def rotation():
    """Hook template -> times used (scripted or posted), so `next` picks the least-used template."""
    used = {k: 0 for k in HOOKS["templates"]}
    for h in jsonl("hooks.jsonl"):
        used[h["template"]] = used.get(h["template"], 0) + 1
    return used


def next_topic():
    cool = dt.timedelta(days=CFG["rotation"]["subject_cooldown_days"])
    recent = {slug(x["subject"]) for x in jsonl("posted.jsonl") if x.get("subject") and dt.datetime.fromisoformat(x["t"].replace("Z", "+00:00")) > dt.datetime.now(dt.timezone.utc) - cool}
    used = rotation()
    ready = [r for r in topics() if r["status"] in ("ready", "restyled", "scripted", "voiced") and not (r["subject"] and slug(r["subject"]) in recent)]
    ready.sort(key=lambda r: (used.get(r["template"], 0), STATUSES.index(r["status"]) * -1, r["id"]))
    return ready[0] if ready else None


# ---------- schedule (all four jenny accounts, one day ahead) ----------
SCHED = CFG["schedule"]


def ff(tool):
    """ffmpeg/ffprobe for QA and covers: the system one, else the binary in the skill's Remotion runtime (`render.ffmpeg_runtime`)."""
    if shutil.which(tool):
        return [tool], dict(os.environ)
    d = os.path.join(CFG["render"]["ffmpeg_runtime"].format(company=COMPANY), "app", "node_modules", "@remotion", "compositor-linux-x64-gnu")
    if not os.path.exists(os.path.join(d, tool)):
        raise Fatal("no %s on PATH or in %s (build it once with `cd engine && npm ci` into that runtime)" % (tool, d))
    return [os.path.join(d, tool)], dict(os.environ, LD_LIBRARY_PATH=d)


def probe(path):
    cmd, env = ff("ffprobe")
    out = subprocess.run(cmd + ["-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", path],
                         env=env, capture_output=True, text=True)
    if out.returncode != 0:
        raise Fatal("ffprobe %s: %s" % (path, out.stderr.strip()[:200]))
    return json.loads(out.stdout)


def make_cover(tid):
    """9:16 JPEG from the hook frame, used as the IG cover and the YT/Pinterest thumbnail."""
    out = p("out", tid + "_cover.jpg")
    cmd, env = ff("ffmpeg")
    subprocess.run(cmd + ["-v", "error", "-y", "-ss", str(SCHED["cover_at_s"]), "-i", p("out", tid + ".mp4"), "-frames:v", "1", "-q:v", "3", out],
                   env=env, check=True)
    return out


def qa(tid):
    """Automated QA of a rendered reel: lint, 1080x1920 with audio, length matches the voice track, cover under 2 MB. Returns problems."""
    t = topic(tid)
    bad = []
    mp4 = p("out", tid + ".mp4")
    if not os.path.exists(mp4):
        return ["no out/%s.mp4" % tid]
    sf = p("work", tid, "script.json")
    s = json.load(open(sf, encoding="utf-8")) if os.path.exists(sf) else build_script(t)
    bad += ["lint: " + x for x in lint_script(s, t)]
    info = probe(mp4)
    v = [x for x in info.get("streams", []) if x.get("codec_type") == "video"]
    if not v or (v[0].get("width"), v[0].get("height")) != (1080, 1920):
        bad.append("video is not 1080x1920: %s" % (v[0] if v else "no video stream"))
    if not any(x.get("codec_type") == "audio" for x in info.get("streams", [])):
        bad.append("no audio stream")
    dur = float(info.get("format", {}).get("duration") or 0)
    if not 20 <= dur <= 60:
        bad.append("length %.1f s is outside 20-60 s" % dur)
    df = p("work", tid, "durations.json")
    if os.path.exists(df):
        voice = sum(json.load(open(df)))
        if dur < voice:
            bad.append("length %.1f s is shorter than the voice track %.1f s (truncated render)" % (dur, voice))
    if not bad:
        cover = make_cover(tid)
        if not 0 < os.path.getsize(cover) < 2e6:
            bad.append("cover %s is empty or over 2 MB" % cover)
    return bad


def caption(t):
    """Post text: hook / features + card + CTA / photo credit + AI-edited / hashtags. A topic's own `caption` (line 2) and `tags` win."""
    s = json.load(open(p("work", t["id"], "script.json"), encoding="utf-8")) if os.path.exists(p("work", t["id"], "script.json")) else build_script(t)
    hook = s["beats"][0]["vo"]
    pr = pron(t)
    if t.get("caption"):
        body = t["caption"].strip()
    else:
        labels = [f["label"].replace(" + ", " and ").replace(",", "").lower() for f in t["features"]]
        body = (", ".join(labels[:-1]) + " and " + labels[-1] if len(labels) > 1 else labels[0])
        body = body[0].upper() + body[1:] + "."
    card = t.get("card") or {}
    if card.get("ovr"):
        body += " %s face card comes out at %d." % (pr["his"].capitalize(), card["ovr"])
    body += " " + s["beats"][-1]["vo"]  # the reel's own comment prompt (per kind)
    credits = []
    for s in faces_of(t):
        c = credit_of(t, s)
        if c and c not in credits:
            credits.append(c)
    photo = ("Photo: %s, via Wikimedia Commons. " % "; ".join(credits)) if credits else ""
    tags = t.get("tags") or (["#" + re.sub(r"[^a-z0-9]", "", slug(t["subject"]))] if t.get("subject") else []) + SCHED["tags"]
    return "\n".join([hook, body, photo + CFG["footer"] + ".", " ".join(tags[:5])])


def hosted():
    try:
        return json.load(open(p("state", "hosted.json")))
    except Exception:
        return {}


def gh_api(args, body=None):
    cmd = ["gh", "api"] + args
    if body is not None:
        f = p("tmp", "gh-%d.json" % os.getpid())
        os.makedirs(p("tmp"), exist_ok=True)
        json.dump(body, open(f, "w"))
        cmd += ["--input", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if body is not None:
        os.remove(f)
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip().startswith(("{", "[")) else {}), r.stderr


def host(tid):
    """Push out/<id>.mp4 + cover to the media branch; returns raw.githubusercontent URLs pinned to the commit.
    Not jsDelivr: the media branch is over its 50 MB package limit, so new jsDelivr URLs answer 403 (SLA-1669).
    The cache is keyed on the local file sizes, so a re-rendered reel is pushed again instead of reusing the old URL."""
    repo, br = SCHED["media_repo"], SCHED["media_branch"]
    h = hosted()
    sizes = [os.path.getsize(f) if os.path.exists(f) else None for f in (p("out", tid + ".mp4"), p("out", tid + "_cover.jpg"))]
    if tid in h and h[tid].get("sizes") == sizes and "raw.githubusercontent.com" in h[tid]["mp4"]:
        return h[tid]
    sha = None
    for local, name in ((p("out", tid + ".mp4"), tid + ".mp4"), (p("out", tid + "_cover.jpg"), tid + "_cover.jpg")):
        if not os.path.exists(local):
            raise Fatal("%s missing (run qa first)" % local)
        rc, cur, _ = gh_api(["repos/%s/contents/%s?ref=%s" % (repo, name, br)])
        if rc == 0 and cur.get("size") == os.path.getsize(local):
            continue
        body = {"message": "media: %s (%s)" % (name, tid), "branch": br, "content": base64.b64encode(open(local, "rb").read()).decode()}
        if rc == 0 and cur.get("sha"):
            body["sha"] = cur["sha"]
        rc, res, err = gh_api(["-X", "PUT", "repos/%s/contents/%s" % (repo, name)], body)
        if rc != 0:
            raise Fatal("push %s to %s@%s failed: %s" % (name, repo, br, err.strip()[:300]))
        sha = res["commit"]["sha"]
    if not sha:
        rc, res, err = gh_api(["repos/%s/commits/%s" % (repo, br)])
        if rc != 0:
            raise Fatal("read %s@%s: %s" % (repo, br, err.strip()[:300]))
        sha = res["sha"]
    base = "https://raw.githubusercontent.com/%s/%s/" % (repo, sha)
    h[tid] = {"mp4": base + tid + ".mp4", "cover": base + tid + "_cover.jpg", "commit": sha, "sizes": sizes, "t": now()}
    os.makedirs(p("state"), exist_ok=True)
    json.dump(h, open(p("state", "hosted.json"), "w"), indent=1)
    return h[tid]


def slot_times(start, days):
    """Posting slots in the window, minus any less than 30 min away (Slashloop needs lead time)."""
    soon = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [x for x in ["%sT%s:00Z" % ((start + dt.timedelta(days=d)).isoformat(), hm) for d in range(days) for hm in SCHED["slots_utc"]] if x > soon]


def calendar_groups(posts_file):
    """Groups from a saved list_social_posts result (raw, wrapped in the MCP content envelope, or {lane: result})."""
    if not posts_file:
        return []
    d = json.load(open(posts_file, encoding="utf-8"))
    if isinstance(d, dict) and "content" in d and isinstance(d["content"], list):
        d = json.loads(d["content"][0]["text"])
    if isinstance(d, dict) and "posts" not in d:
        return [g for v in d.values() if isinstance(v, dict) for g in v.get("posts", [])]
    return d.get("posts", []) if isinstance(d, dict) else d


def iso(x):
    return dt.datetime.fromisoformat(x.replace("Z", "+00:00")).strftime("%Y-%m-%dT%H:%M:%SZ")


def plan(start, days, posts_file=None):
    """Slots in the window: who fills them, which accounts are missing, and which postable reel goes into each empty slot."""
    acc = SCHED["accounts"]
    ours = set(acc.values())
    sched = jsonl("scheduled.jsonl")
    by_group = {r["groupId"]: r for r in sched}
    cal = calendar_groups(posts_file)
    have = {}  # slot -> {reel id: set(account ids)}
    notes = []
    if cal:
        for g in cal:
            at = iso(g["publishAt"])
            mine = [x for x in g.get("posts", []) if x["account"]["id"] in ours]
            if not mine:
                continue
            urls = " ".join(m.get("url", "") for m in g.get("media", []))
            rid = (by_group.get(g["groupId"]) or {}).get("id")
            if not rid and "/publish/F" in urls:
                notes.append("MIXING %s group %s: facemetric media on the genz accounts (%s)" % (at, g["groupId"], urls[:120]))
                continue
            rid = rid or "?" + g["groupId"][:8]
            bad = [x for x in mine if x.get("state") == "ERROR" or x.get("error")]
            if bad:
                notes.append("ERROR %s %s: %s" % (at, rid, "; ".join("%s %s" % (x["provider"], x.get("error")) for x in bad)))
            have.setdefault(at, {}).setdefault(rid, set()).update(x["account"]["id"] for x in mine if not (x.get("state") == "ERROR" or x.get("error")))
        listed = {g["groupId"] for g in cal}
        for r in sched:
            if r["groupId"] not in listed and iso(r["publishAt"]) in slot_times(start, days):
                notes.append("MISSING %s %s: group %s is in scheduled.jsonl but not on the calendar (deleted?)" % (iso(r["publishAt"]), r["id"], r["groupId"]))
    else:
        names = {"ig": acc["instagram"], "yt": acc["youtube"], "threads": acc["threads"], "pinterest": acc["pinterest"]}
        for r in sched:
            have.setdefault(iso(r["publishAt"]), {}).setdefault(r["id"], set()).update(names.get(x, x) for x in r.get("platforms", []))
    used_ids = {r["id"] for r in sched}
    cool = dt.timedelta(days=CFG["rotation"]["subject_cooldown_days"])
    taken_subj = {slug(r["subject"]): iso(r["publishAt"]) for r in sched if r.get("subject")}  # self-diagnosis reels (no subject) never cool down
    rows = {r["id"]: r for r in topics()}
    blocked = SCHED.get("blocked_templates") or {}
    pool = [r for r in topics() if r["status"] in SCHED["postable"] and r["id"] not in used_ids and r["template"] not in blocked
            and os.path.exists(p("out", r["id"] + ".mp4"))]
    pool.sort(key=lambda r: (SCHED["postable"].index(r["status"]), r["id"]))  # board-approved first
    fills, gaps, short = [], [], []
    for at in slot_times(start, days):
        reels = have.get(at, {})
        if reels:
            for rid, got in reels.items():
                miss = [k for k, v in acc.items() if v not in got]
                if miss and not rid.startswith("?"):
                    gaps.append({"reel": rid, "publishAt": at, "missing": miss})
            continue
        pick = None
        for r in pool:
            last = taken_subj.get(slug(r["subject"])) if r["subject"] else None
            if last and abs(dt.datetime.fromisoformat(at.replace("Z", "+00:00")) - dt.datetime.fromisoformat(last.replace("Z", "+00:00"))) < cool:
                continue
            pick = r
            break
        if pick:
            pool.remove(pick)
            if pick["subject"]:
                taken_subj[slug(pick["subject"])] = at
            fills.append({"reel": pick["id"], "publishAt": at, "status": pick["status"], "subject": pick["subject"]})
        else:
            short.append(at)
    return {"fills": fills, "gaps": gaps, "short": short, "notes": notes, "pool_left": [r["id"] for r in pool], "rows": rows}


def payload(tid, at, missing=None):
    """One create_social_post call for a reel on all four accounts (or only the missing ones). Media URLs still go through upload_social_media."""
    t = topic(tid)
    h = host(tid)
    acc = SCHED["accounts"]
    ids = [acc[k] for k in (missing or acc)]
    out = {"reel": tid, "publishAt": at, "integrationIds": ids, "content": caption(t),
           "upload": {"video": h["mp4"], "thumbnail": h["cover"]},
           "media": [{"type": "video", "url": "<upload_social_media(upload.video)>", "thumbnail": "<upload_social_media(upload.thumbnail)>"}]}
    if acc["pinterest"] in ids:
        out["settings"] = {acc["pinterest"]: {"boardId": SCHED["pinterest_board"]}}
    return out


def supply(start, days=3):
    """Reels that can still be posted vs open slots from `start` for `days`; plus the next topics to make."""
    pl = plan(start, days)
    blocked = SCHED["blocked_templates"]
    todo = [r for r in topics() if r["status"] in ("idea", "ready", "restyled", "scripted", "voiced", "rendered") and r["template"] not in blocked]
    todo.sort(key=lambda r: (-STATUSES.index(r["status"]), r["id"]))
    return {"open": len(pl["short"]), "ready_left": pl["pool_left"], "next": [(r["id"], r["template"], r["subject"], r["status"]) for r in todo],
            "blocked": [(r["id"], r["template"], blocked[r["template"]]) for r in topics() if r["template"] in blocked and r["status"] not in ("posted", "dropped")]}
