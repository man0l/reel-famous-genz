"""reel-famous-genz: one-lane face-breakdown reels (Gen Z actors and creators) in the @glowupmenclub format.

Memory lives in the skill's own data home (RFG_HOME). The picture is the skill's own Remotion composition `genz-face`
(engine/), rendered on this box; nothing in reel-factory is needed or changed.
Stdlib only."""
import base64, csv, datetime as dt, json, os, re, shutil, struct, subprocess, time, urllib.error, urllib.parse, urllib.request, zipfile

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(SKILL, "pack")
COMPANY = os.environ.get("PAPERCLIP_COMPANY_ID") or "default"
HOME = os.environ.get("RFG_HOME") or "/paperclip/instances/default/data/reel-famous-genz/%s" % COMPANY
OR_BASE = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
WIKI_UA = "reel-famous-genz/1.0 (Paperclip; face-breakdown reels)"

CFG = json.load(open(os.path.join(PACK, "config.json"), encoding="utf-8"))
HOOKS = json.load(open(os.path.join(PACK, "hooks.json"), encoding="utf-8"))
TOPIC_COLS = ["id", "template", "subject", "status", "hook", "updated", "notes"]
STATUSES = ["idea", "ready", "restyled", "scripted", "voiced", "rendered", "approved", "posted", "dropped"]


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
    want = " ".join(hook_lines(t))
    if not beats or beats[0]["kind"] != "hook" or beats[0]["vo"] != want:
        out.append("hook: must be the @glowupmenclub template %s word for word: %r" % (t["template"], want))
    if len(beats) < 2 or beats[1]["kind"] != "narrator" or beats[1]["vo"] != bridge_line(t):
        out.append("bridge: must be %r" % bridge_line(t))
    nf = sum(1 for b in beats if b["kind"] == "feature")
    if not CFG["features"]["min"] <= nf <= CFG["features"]["max"]:
        out.append("features: %d feature beats (want %d-%d)" % (nf, CFG["features"]["min"], CFG["features"]["max"]))
    kinds = [b["kind"] for b in beats]
    if HOOKS["templates"][t["template"]]["kind"] == "celebrity" and "walkout" not in kinds:
        out.append("payoff: a celebrity breakdown ends on the game card (walkout beat)")
    if kinds[-1] != "cta":
        out.append("cta: the last beat must be the comment prompt")
    for i, b in enumerate(beats):
        where = "beat %d (%s)" % (i, b["kind"])
        out += lint_vo(b["vo"], where) if i else lint_text(b["vo"], where)
        for s in screen_texts(b):
            out += lint_text(s, where + " on screen")
    if not t.get("photo", {}).get("credit"):
        out.append("credit: topic has no photo credit (Commons author + licence)")
    return out


def screen_texts(b):
    out = list(b.get("head") or []) if isinstance(b.get("head"), list) else [b.get("head") or ""]
    out += b.get("lines") or []
    for c in b.get("callouts") or []:
        out += [c.get("label", ""), c.get("chip", "")]
    out += b.get("pills") or []
    out += [b.get("tease") or "", b.get("sub") or "", b.get("name") or ""]
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


def feature_beat(f, img):
    r = region(f)
    c = {"at": f.get("at") or r["at"], "label": f["label"].upper(), "pos": f.get("pos") or r["pos"]}
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


def build_script(t):
    """Topic -> script.json for the `genz-face` composition in engine/ (lane B tokens, kpop stage), in the @glowupmenclub beat order:
    hook with the name -> "so let's break down what his face actually has" -> 4-6 features with callouts -> game card -> comment prompt."""
    kind = HOOKS["templates"][t["template"]]["kind"]
    name = t["subject"]
    pr = pron(t)
    feats = t.get("features") or []
    if not CFG["features"]["min"] <= len(feats) <= CFG["features"]["max"]:
        raise Fatal("%s: needs %d-%d features, has %d" % (t["id"], CFG["features"]["min"], CFG["features"]["max"], len(feats)))
    missing = [f.get("label") for f in feats if not f.get("vo")]
    if missing:
        raise Fatal("%s: features without a spoken line (run `rfg.sh copy %s` or write `vo`): %s" % (t["id"], t["id"], ", ".join(map(str, missing))))
    sprites, sassets = sprite_assets()
    subjects_used = [name] + [f["subject"] for f in feats if f.get("subject")]
    assets, ratios = dict(sassets), {}
    for s in dict.fromkeys(subjects_used):
        key = "cut" if s == name else "cut_" + slug(s)
        rel = cut_rel(s)
        if not os.path.exists(p("stills", rel)):
            raise Fatal("%s: no painted cutout for %s (run `rfg.sh restyle %s`)" % (t["id"], s, t["id"]))
        assets[key], ratios[key] = rel, png_ratio(p("stills", rel))
    img_of = lambda s: "cut" if (not s or s == name) else "cut_" + slug(s)
    ep = int(t.get("ep") or re.sub(r"\D", "", t["id"]) or 1)
    hook = hook_lines(t)
    hb = {"kind": "hook", "img": "cut", "head": head_lines(hook[0]), "card": [first(name).upper(), t.get("card_line") or "face file · ep.%02d" % ep],
          "badge": CFG["badge"], "vo": " ".join(hook)}
    if len(hook) > 1:
        hb["sub"] = hook[1].lower() if len(hook[1]) < 70 else hook[1]
    hb["hot"] = hot_of(hb["vo"], [first(name), "attractive", "viral"])
    beats = [hb]
    br = bridge_line(t)
    beats.append({"kind": "narrator", "lines": t.get("bridge_lines") or ["so let's break down", "what %s face" % pr["his"], "*actually has.*"], "vo": br, "hot": hot_of(br, ["face", "actually"])})
    for f in feats:
        beats.append(feature_beat(f, img_of(f.get("subject"))))
    card = t.get("card")
    if kind == "celebrity" or card:
        if not card:
            raise Fatal("%s: a celebrity breakdown needs `card` (ovr, rarity, stats)" % t["id"])
        stats = card["stats"]
        miss = [k for k in CFG["card"]["stats"] if k not in stats]
        if miss or card.get("rarity") not in CFG["card"]["rarity"]:
            raise Fatal("%s: card needs stats %s and rarity in %s" % (t["id"], CFG["card"]["stats"], CFG["card"]["rarity"]))
        vo = card.get("vo") or "Put it all together and %s face card comes out at %d." % (pr["his"], int(card["ovr"]))
        beats.append({"kind": "walkout", "img": "cut", "name": name.upper(), "sub": card.get("sub") or "face card", "ovr": int(card["ovr"]), "rarity": card["rarity"],
                      "stats": [[k, int(stats[k])] for k in CFG["card"]["stats"]], "vo": vo, "hot": hot_of(vo, [str(card["ovr"]), "card"])})
    cta = t.get("cta") or {}
    nxt = t.get("next") or []
    pills = cta.get("pills") or [x.upper() for x in nxt[:4]] or ["WHO'S NEXT?"]
    if len(pills) < 2:
        pills = pills + ["SOMEONE ELSE"]
    cvo = cta.get("vo") or "Comment who I should break down next."
    c = {"kind": "cta", "head": cta.get("head") or ["COMMENT", "WHO'S *NEXT*"], "pills": pills, "vo": cvo, "hot": hot_of(cvo, cta.get("hot") or ["next", "comment"])}
    if cta.get("tease"):
        c["tease"] = cta["tease"]
    beats.append(c)
    credits = []
    for s in dict.fromkeys(subjects_used):
        cr = (t.get("photo") or {}).get("credit") if s == name else (subjects().get(slug(s)) or {}).get("credit")
        if not cr:
            raise Fatal("%s: no photo credit for %s" % (t["id"], s))
        credits.append(cr)
    cite = "Portraits painted from photos by %s, Wikimedia Commons" % "; ".join(credits) if len(credits) > 1 else "Portrait painted from a photo by %s, Wikimedia Commons" % credits[0]
    return {"format": "genz-face", "reel_id": t["id"], "template": t["template"], "footer": CFG["footer"], "lane": CFG["lane"], "lens": CFG["lens"],
            "episode_type": "celebrity" if kind in ("celebrity", "compare") else "self_diagnosis", "tag": {"en": CFG["tag"] % ep}, "name": name,
            "cite": "%s · %s" % (cite, CFG["footer"]), "hangul": False, "assets": assets, "sprites": sprites, "ratios": ratios, "beats": beats, "sfx": True}


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
def commons_info(file_title):
    """(thumb url, credit 'Author, Licence') of a Commons file title like 'File:Timothée Chalamet-63541.jpg'."""
    q = urllib.parse.urlencode({"action": "query", "format": "json", "titles": file_title, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": "1200"})
    d = json.load(urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + q, headers={"User-Agent": WIKI_UA}), timeout=60))
    page = next(iter(d["query"]["pages"].values()))
    if "imageinfo" not in page:
        raise Fatal("Commons has no file %r" % file_title)
    ii = page["imageinfo"][0]
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
        if v.get("pass"):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            key_png(out, dest)
            subs = subjects()
            subs.setdefault(slug(t["subject"]), {"name": t["subject"]}).update({"cutout": os.path.relpath(dest, HOME), "likeness": v.get("likeness")})
            save_subjects(subs)
            return spent
    raise Fatal("no painted cutout of %s passed QA ($%.3f spent): %s" % (t["subject"], spent, last.get("notes", "")))


# ---------- copy (optional LLM help for missing feature lines) ----------
COPY_PROMPT = """Write the spoken voice-over for a face-breakdown short in the style of @glowupmenclub: calm, confident, plain English, explains why each feature works.
Subject: {name}. Features in order (one line each): {features}
Rules: every sentence under 14 words, one or two sentences per feature, name the feature plainly, no emojis, no score out of 10, never mention an app, a link or face analysis,
no looksmaxxing words (canthal, mogging, mewing, PSL, chad), no health, surgery, age or ethnicity claims, no boy group or idol framing, never name a studio, show or film.
Reply JSON only: {{"feature_vo": [{n} strings]}}"""


def llm_feature_lines(t):
    feats = t["features"]
    desc = " | ".join("%d. %s (%s)" % (i + 1, f["label"], f.get("chip") or f.get("region")) for i, f in enumerate(feats))
    v, _ = chat_json(COPY_PROMPT.format(name=t["subject"], features=desc, n=len(feats)), kind="script")
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


def render_vps(tid, job):
    lim = CFG["render"]["vps_limits"]
    out = p("out", tid + ".mp4")
    env = dict(os.environ, RF_REMOTION_HOME=CFG["render"]["vps_runtime"].format(company=COMPANY), MAX_RSS_MB=str(lim["max_rss_mb"]),
               MIN_AVAIL_MB=str(lim["min_avail_mb"]), MAX_SECS=str(lim["max_secs"]), RF_START_AVAIL_MB=str(lim["start_avail_mb"]))
    sh = os.path.join(engine(), "engine", "render.sh")
    rc = subprocess.run(["bash", sh, job, out], env=env).returncode
    if rc == 75:
        raise Fatal("another render is running on this box or memory is low; try again later")
    if rc != 0 or not os.path.exists(out):
        raise Fatal("VPS render exit %s (see %s/watchdog.summary)" % (rc, job))
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
    recent = {slug(x["subject"]) for x in jsonl("posted.jsonl") if dt.datetime.fromisoformat(x["t"].replace("Z", "+00:00")) > dt.datetime.now(dt.timezone.utc) - cool}
    used = rotation()
    ready = [r for r in topics() if r["status"] in ("ready", "restyled", "scripted", "voiced") and slug(r["subject"]) not in recent]
    ready.sort(key=lambda r: (used.get(r["template"], 0), STATUSES.index(r["status"]) * -1, r["id"]))
    return ready[0] if ready else None
