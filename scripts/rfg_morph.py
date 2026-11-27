"""SLA-1728: the clip morph opener of a celebrity reel (reel-factory's facemetric opener, board 27 Nov 2026: "use the same approach").

The full-frame hook shows the painted Commons portrait from frame 0. With the morph, the reel opens on the real Commons photo instead and a
first/last-frame video clip (OpenRouter /videos, Veo 3.1 Lite) turns it into the painted portrait in about PLAY s, then cuts to the
portrait still: the viewer sees who it is, then the edit. auto() runs before every render of a celebrity reel and decides:

  what   the topic's Commons photo, aligned onto the cutout with MediaPipe's face mesh (a similarity transform: same eyes, nose and mouth
         position) and cut to the portrait's silhouette over a flat background; the last frame is the cutout over the same background, in
         the hook's own frame position (beats[0].crop), so the composition plays the clip under the cutout's alpha and lands on the still
  when   the mesh fit must be close (FIT_MAX: the photo's face has about the portrait's pose) and a vision model must see the same person,
         pose and expression with nothing (hands, mic, glasses, hair) covering the face in one only, so the morph reads as one face
         repainted, not a jump between two pictures
  check  the clip's frames are checked (blink, mouth, head or camera move, hands, broken face, a different person), trimmed to the clean
         stretch that reaches the portrait; a failed check gets one new clip, then the reel keeps its still hook

The decision is kept in work/<id>/morph.json and the clip in work/<id>/morph/clip.mp4, so a re-render costs nothing; `rfg.sh morph <id>
--redo` decides again. A new cutout or photo (restyle) also decides again. RFG_MORPH=off skips it. About $0.12 a clip and a cent of checks.
Needs PIL, numpy, OpenCV and mediapipe (reel-factory's pylib, put on PYTHONPATH by rfg.sh) and models/face_landmarker.task in the data
home; without them the reel keeps its still hook."""
import hashlib, io, json, os, shutil, time, urllib.error, urllib.request

import rfg_lib as L

MCFG = dict({"model": "google/veo-3.1-lite", "seconds": 4, "resolution": "720p", "usd_per_clip": 0.12}, **L.CFG.get("morph", {}))
FRAME = (1080, 1920)          # the reel frame
VEO = (720, 1280)             # the clip's frames (9:16, 720p)
HOOK_CROP = {"w": 1400, "x": -160, "y": 250}   # engine theme.ts HOOK_FULL.crop
BG = (34, 12, 48)             # flat background behind both frames (masked away by the cutout's alpha in the reel)
PLAN, CLIP = "morph.json", "morph/clip.mp4"
PLAY = 1.8                    # seconds the trimmed clip plays for
HOOK_HOLD = 0.6               # the still shows at least this long before the first feature cut
RATE = (1.0, 2.0)             # playback speed range
MIN_PLAY = 0.8                # a clean stretch shorter than this (played) is no morph
FIT_MAX = 0.12                # median mesh distance after the fit, over the eye distance: above it the poses differ too much to morph
QA_TIMES = [round(0.25 * i, 2) for i in range(1, 16)] + [3.95]
LAND_GAP = 0.03               # the cut to the portrait may jump at most this mean grey level in the changing area
PROMPT = ("Locked-off static camera, head-and-shoulders portrait on a plain dark purple background. The same person keeps the same pose, "
          "head position and expression for the whole clip while %s, a smooth continuous morph from the first frame into the last frame. "
          "No camera movement, no head movement, no blinking, no talking, no hands or objects entering the frame, no text.")
DECIDE = ("Two head-and-shoulders images for a short-form face-breakdown reel, as they appear full screen on a phone. Image 1 is a real "
          "photo of the person, image 2 the painted portrait of them the reel's hook shows. The reel opens on a video that morphs image 1 "
          "into image 2 in about 2 seconds, so the viewer sees the real person turn into the painting. The faces are already aligned (same "
          "eye, nose and mouth position) and the clothes, hair styling and lighting are expected to change. Say no only when the morph "
          "would look broken: a different person, a clearly different head direction (a three-quarter profile against a frontal face; a "
          "slight turn is fine), a big expression change (a wide open-mouth laugh against a closed mouth), or something covering the face "
          "in one image only (hands, a microphone, sunglasses, another person). Answer JSON only: {\"morph\": true|false, \"change\": \"what changes from image 1 "
          "to image 2, as a clause that completes 'while ...', e.g. 'the photo is repainted as a smooth digital painting and the suit "
          "becomes a navy t-shirt', at most 20 words\", \"why\": \"one short sentence\"}")
CHECK = ("Image 1 is a contact sheet of %d frames (left to right, top to bottom, each labelled with its second) from a 4 s AI video that "
         "morphs a real photo of a person from its first frame into image 2 (the painted portrait it must land on). The intended change: "
         "%s. That change, including the soft blend while it happens and a slight shift of the head or expression towards the portrait's, is "
         "expected: never flag it. For every frame flag only what a viewer "
         "would see as a mistake: closed or half-closed eyes (a blink), a squint, a new smile, an open or moving mouth, a head turn or "
         "tilt, a camera move or zoom, hands or objects, text, or a broken face (melting, doubled or missing features). Answer JSON only: "
         "{\"frames\": [{\"t\": 0.25, \"ok\": true, \"issue\": \"\"}, ...], \"change_starts\": <the second label of the first frame where "
         "the intended change is visibly under way>, \"same_person\": true|false (false only when the face clearly becomes someone else)}")


class Unavailable(Exception):
    """The morph cannot run on this host (libraries or the face model missing): the reel keeps its still hook, nothing is recorded."""


class Refused(Exception):
    """The video model's content filter refused the frames (Veo and Wan both refuse many public figures' photos). Recorded as a no-morph
    decision; never retried on this or another model: the filter is the provider's policy, not a glitch."""


REFUSAL = ("filtered", "usage guidelines", "public figure", "violat", "safety", "prominent")


def libs():
    try:
        import cv2, numpy, mediapipe  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as e:
        raise Unavailable("no %s (rfg.sh puts reel-factory's pylib on PYTHONPATH; set RF_PYLIB)" % e.name)
    if not os.path.exists(model_path()):
        raise Unavailable("no face model %s (copy reel-factory's formats/facemetric/models/face_landmarker.task)" % model_path())


def model_path():
    return os.environ.get("RFG_FACE_MODEL") or L.p("models", "face_landmarker.task")


# ------------------------------------------------------------------ the two frames
def hook_rect(script):
    """(left, top, width, height) of the cutout in the full-frame hook, frame pixels."""
    b = script["beats"][0]
    c = b.get("crop") or HOOK_CROP
    return c["x"], c["y"], c["w"], c["w"] * script["ratios"][b["img"]]


def mesh(rgb):
    """MediaPipe's 478 face mesh points of the first face in an RGB numpy image, pixel coordinates, or None."""
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    opts = vision.FaceLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=model_path()), running_mode=vision.RunningMode.IMAGE,
                                        num_faces=1, min_face_detection_confidence=0.3)
    with vision.FaceLandmarker.create_from_options(opts) as fl:
        res = fl.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
    if not res.face_landmarks:
        return None
    h, w = rgb.shape[:2]
    return np.array([(p.x * w, p.y * h) for p in res.face_landmarks[0][:468]], float)


def fit(src_pts, dst_pts):
    """Similarity transform (2x3) taking the photo's mesh onto the portrait's, and its median error over the eye distance."""
    import cv2
    import numpy as np
    m, _ = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.LMEDS)
    if m is None:
        return None, 9.0
    moved = src_pts @ m[:, :2].T + m[:, 2]
    eyes = float(np.linalg.norm(dst_pts[33] - dst_pts[263])) or 1.0
    return m, float(np.median(np.linalg.norm(moved - dst_pts, axis=1)) / eyes)


def person(rgb, face, alpha, scale=0.5):
    """0-1 mask of the person in the aligned photo (OpenCV GrabCut): the face mesh's hull is the person for sure, outside the portrait's
    silhouette is background for sure, the rest is guessed. The photo's own background (a red-carpet wall) then does not show inside the
    silhouette where the painted hair is fuller than the photo's."""
    import cv2
    import numpy as np
    h, w = alpha.shape
    sw, sh = round(w * scale), round(h * scale)
    img = cv2.resize(rgb, (sw, sh), interpolation=cv2.INTER_AREA)
    a = cv2.resize(alpha, (sw, sh), interpolation=cv2.INTER_AREA)
    m = np.where(a > 0.5, cv2.GC_PR_FGD, cv2.GC_BGD).astype(np.uint8)
    hull = cv2.convexHull((face * scale).astype(np.int32))
    core = np.zeros_like(m)
    cv2.fillConvexPoly(core, hull, 1)
    m[core > 0] = cv2.GC_FGD
    try:
        cv2.grabCut(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), m, None, np.zeros((1, 65)), np.zeros((1, 65)), 5, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return np.ones_like(alpha)
    fg = np.isin(m, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.float32)
    fg = cv2.GaussianBlur(cv2.resize(fg, (w, h), interpolation=cv2.INTER_LINEAR), (0, 0), 3)
    return np.clip(fg, 0, 1)


def frames(script, photo, cut, work):
    """first.jpg (the photo aligned onto the portrait, in its silhouette) and last.jpg (the portrait), both full reel frames at the clip's
    size over BG. Returns (first, last, fit error), or (None, None, why) when a face is not found."""
    import cv2
    import numpy as np
    from PIL import Image
    x, y, w, h = hook_rect(script)
    W, H = FRAME
    co = Image.open(cut).convert("RGBA")
    sx = w / co.width
    canvas = Image.new("RGBA", FRAME, BG + (255,))
    placed = co.resize((round(w), round(h)), Image.LANCZOS)
    layer = Image.new("RGBA", FRAME, (0, 0, 0, 0))
    layer.paste(placed, (round(x), round(y)))
    alpha = np.asarray(layer)[:, :, 3].astype(float) / 255
    last = Image.alpha_composite(canvas, layer).convert("RGB")
    ph = np.asarray(Image.open(photo).convert("RGB"))
    a = mesh(ph)
    if a is None:
        return None, None, "no face found in the photo"
    on_grey = Image.alpha_composite(Image.new("RGBA", co.size, (128, 128, 128, 255)), co).convert("RGB")
    b = mesh(np.asarray(on_grey))
    if b is None:
        return None, None, "no face found in the portrait"
    b = b * sx + np.array([x, y])
    m, err = fit(a, b)
    if m is None:
        return None, None, "the photo's face does not fit the portrait's"
    warped = cv2.warpAffine(ph, m, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    keep = alpha * person(warped, a @ m[:, :2].T + m[:, 2], alpha)
    bg = np.empty_like(warped)
    bg[:] = BG
    first = (warped * keep[:, :, None] + bg * (1 - keep[:, :, None])).astype(np.uint8)
    os.makedirs(work, exist_ok=True)
    fp, lp = os.path.join(work, "first.jpg"), os.path.join(work, "last.jpg")
    Image.fromarray(first).resize(VEO, Image.LANCZOS).save(fp, "JPEG", quality=92)
    last.resize(VEO, Image.LANCZOS).save(lp, "JPEG", quality=92)
    return fp, lp, round(err, 4)


# ------------------------------------------------------------------ the clip
def _call(url, body=None):
    req = urllib.request.Request(url if url.startswith("http") else L.OR_BASE + url, json.dumps(body).encode() if body else None,
                                 {"Authorization": "Bearer " + os.environ["OPEN_ROUTER_API_KEY"], "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        raise L.Fatal("video API HTTP %s %s" % (e.code, e.read()[:300].decode(errors="replace")))


def gen_clip(first, last, change, out, timeout=900):
    """One first/last-frame clip (OpenRouter /videos, submit then poll). Writes the MP4, returns the API-reported cost."""
    L.need_env("OPEN_ROUTER_API_KEY")
    j = _call("/videos", {"model": MCFG["model"], "prompt": PROMPT % change, "duration": MCFG["seconds"], "aspect_ratio": "9:16",
                          "resolution": MCFG["resolution"], "generate_audio": False,
                          "frame_images": [{"type": "image_url", "image_url": {"url": L.durl(first)}, "frame_type": "first_frame"},
                                           {"type": "image_url", "image_url": {"url": L.durl(last)}, "frame_type": "last_frame"}]})
    t0 = time.time()
    while j.get("status") not in ("completed", "failed", "cancelled", "expired"):
        if time.time() - t0 > timeout:
            raise L.Fatal("morph clip %s still %s after %d s" % (j.get("id"), j.get("status"), timeout))
        time.sleep(10)
        j = _call(j["polling_url"])
    if j["status"] != "completed":
        L.spend("video", (j.get("usage") or {}).get("cost") or 0)
        err = str(j.get("error") or "")
        if any(w in err.lower() for w in REFUSAL):
            raise Refused(err[:200])
        raise L.Fatal("morph clip %s %s: %s" % (j.get("id"), j["status"], err))
    usd = (j.get("usage") or {}).get("cost") or MCFG["usd_per_clip"]
    L.spend("video", usd)
    req = urllib.request.Request((j.get("unsigned_urls") or j.get("urls"))[0], headers={"Authorization": "Bearer " + os.environ["OPEN_ROUTER_API_KEY"]})
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with urllib.request.urlopen(req, timeout=300) as r, open(out + ".part", "wb") as f:
        shutil.copyfileobj(r, f)
    os.replace(out + ".part", out)
    return usd


def _grey(img):
    import numpy as np
    from PIL import Image
    im = img if isinstance(img, Image.Image) else Image.open(img)
    return np.asarray(im.convert("L").resize((180, 320), Image.BILINEAR), float) / 255


def clip_frames(clip, times):
    """{t: PIL image} of the clip's frames at `times` (seconds), read with OpenCV."""
    import cv2
    from PIL import Image
    cap, out = cv2.VideoCapture(clip), {}
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if ok:
            out[t] = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    cap.release()
    return out


def contact_sheet(frames, out, cols=4, size=(180, 320)):
    from PIL import Image, ImageDraw
    ts = sorted(frames)
    rows = (len(ts) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * size[0], rows * (size[1] + 22)), "white")
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(ts):
        x, y = (i % cols) * size[0], (i // cols) * (size[1] + 22)
        sheet.paste(frames[t].resize(size), (x, y + 22))
        d.text((x + 6, y + 4), "%.2f s" % t, fill="black")
    sheet.save(out, "JPEG", quality=88)
    return out


def trim(frames, ok, first, last, start=None, play=PLAY):
    """(in, out, rate) of the clean stretch of the clip that reaches the portrait, else None. `ok` = {t: clean}; a frame's progress is
    how far it is from the first frame towards the last (0-1) in the area that changes: `in` is a quarter second before the change starts
    (`start`, the vision check's frame, else measured), `out` the last clean frame before the first unclean one after `in`, which must be
    at least 85 % of the way or close enough to the portrait (LAND_GAP) that the cut to it does not jump."""
    import numpy as np
    a, z = _grey(first), _grey(last)
    diff = abs(a - z)
    mask = diff >= max(0.03, float(np.quantile(diff, 0.95)))
    if mask.sum() < 50:
        mask = np.ones_like(diff, bool)
    prog, gap = {}, {}
    for t, im in frames.items():
        g = _grey(im)
        da, dz = float(abs(g - a)[mask].mean()), float(abs(g - z)[mask].mean())
        prog[t], gap[t] = (da / (da + dz) if da + dz > 1e-6 else 1.0), dz
    ts = sorted(frames)
    if isinstance(start, (int, float)) and 0 < start < 3.0:
        t_in = round(max(0.0, start - 0.25), 2)
    else:
        t_in = max([0.0] + [t for t in ts if prog[t] < 0.15 and t < 3.0])
        t_in = max(0.0, round(t_in - 0.25, 2)) if t_in else 0.0
    t_out = None
    for t in ts:
        if t <= t_in:
            continue
        if not ok.get(t, False):
            break
        t_out = t
    if t_out is None or (prog.get(t_out, 0) < 0.85 and gap.get(t_out, 1) > LAND_GAP):
        return None
    rate = min(RATE[1], max(RATE[0], (t_out - t_in) / play))
    if (t_out - t_in) / rate < MIN_PLAY:
        return None
    return t_in, t_out, round(rate, 2)


def check_clip(clip, first, last, work, change, play=PLAY):
    """(trim or None, notes, usd): the vision check of a generated clip, then trim()."""
    fr = clip_frames(clip, QA_TIMES)
    if len(fr) < len(QA_TIMES) - 2:
        return None, "could not read the clip's frames", 0.0
    sheet = contact_sheet(fr, os.path.join(work, "check.jpg"))
    j, usd = L.chat_json(CHECK % (len(fr), change), [sheet, last])
    rows = {round(float(f.get("t", -1)), 2): bool(f.get("ok")) for f in (j.get("frames") or []) if isinstance(f, dict)}
    ok = {t: rows.get(t, False) for t in fr}
    bad = ["%.2f %s" % (round(float(f.get("t", 0)), 2), f.get("issue") or "") for f in j.get("frames") or [] if isinstance(f, dict) and not f.get("ok")]
    if j.get("same_person") is False:
        return None, "the clip changes the person", usd
    if not rows:
        return None, "no frame check: %s" % (j.get("notes") or "empty answer"), usd
    st = j.get("change_starts")
    return trim(fr, ok, first, last, st if isinstance(st, (int, float)) else None, play), "; ".join(bad) or "clean", usd


# ------------------------------------------------------------------ the decision
def applies(script):
    """A celebrity reel whose hook is the full-frame cutout (not the card layout, not a self-diagnosis topic card)."""
    b = (script.get("beats") or [{}])[0]
    return b.get("kind") == "hook" and (b.get("layout") or "full") == "full" and b.get("img") in (script.get("ratios") or {})


def sources(tid, script):
    """(photo, cutout) paths of the hook's face."""
    t = L.topic(tid)
    cut = L.p("stills", script["assets"][script["beats"][0]["img"]])
    return L.p("faces", L.slug(t["subject"]), "source.jpg"), cut


def _key(*paths):
    h = hashlib.sha1()
    for f in paths:
        st = os.stat(f)
        h.update(("%s:%d:%d;" % (os.path.basename(f), st.st_size, int(st.st_mtime))).encode())
    return h.hexdigest()[:12]


def plan_of(tid):
    """The recorded decision (work/<id>/morph.json) or {}."""
    pp = L.p("work", tid, PLAN)
    try:
        return json.load(open(pp, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def play_for(durations):
    """How long the clip plays: PLAY, shorter when the spoken hook is short, so the still shows HOOK_HOLD before the first cut."""
    return round(max(MIN_PLAY, min(PLAY, (durations[0] if durations else PLAY + HOOK_HOLD) - HOOK_HOLD)), 2)


def auto(tid, redo=False, tries=2):
    """Decides the clip morph for reel `tid` (see the module doc) and records it in work/<id>/morph.json. Returns the plan
    {"morph": bool, "why", ...}, or None when it does not apply or cannot run here (the reel keeps its still hook)."""
    if os.environ.get("RFG_MORPH", "").lower() in ("off", "0", "no"):
        return None
    wd = L.p("work", tid)
    script = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    if not applies(script):
        return None
    t = L.topic(tid)
    if t.get("morph") is False:
        return None
    try:
        libs()
    except Unavailable as e:
        L.log("  morph %s: skipped, %s" % (tid, e))
        return None
    photo, cut = sources(tid, script)
    if not os.path.exists(photo):
        L.log("  morph %s: skipped, no photo %s" % (tid, photo))
        return None
    durs = json.load(open(os.path.join(wd, "durations.json"))) if os.path.exists(os.path.join(wd, "durations.json")) else []
    key = _key(photo, cut) + "-%s" % json.dumps(script["beats"][0].get("crop") or HOOK_CROP, sort_keys=True)
    old, clip = plan_of(tid), os.path.join(wd, CLIP)
    if not redo and old.get("key") == key and "morph" in old and (not old["morph"] or os.path.exists(clip)):
        return old
    plan = {"key": key, "morph": False, "usd": 0.0, "play": play_for(durs)}
    work = os.path.join(wd, "morph")

    def done(why, **kw):
        plan.update(why=why, **kw)
        plan["usd"] = round(plan["usd"], 3)
        json.dump(plan, open(os.path.join(wd, PLAN), "w"), indent=1)
        L.log("  morph %s: %s (%s)" % (tid, "clip opener" if plan["morph"] else "no morph, still hook", why))
        return plan

    first, last, err = frames(script, photo, cut, work)
    if first is None:
        return done(err)
    plan["fit"] = err
    if err > FIT_MAX:
        return done("the photo's pose differs from the portrait's (mesh fit %.3f > %.2f)" % (err, FIT_MAX))
    j, usd = L.chat_json(DECIDE, [first, last])
    plan["usd"] += usd
    plan["change"] = " ".join(str(j.get("change") or "").split()).rstrip(".")
    if not j.get("morph") or not plan["change"]:
        return done("the photo would not read as the same face repainted: %s" % (j.get("why") or j.get("notes") or "no answer"))
    notes = []
    for attempt in range(tries):
        if attempt or redo or not os.path.exists(clip) or old.get("key") != key:
            try:
                plan["usd"] += gen_clip(first, last, plan["change"], clip)
            except Refused as e:
                return done("the video model refused the photo: %s" % e, check=notes)
        tr, note, usd = check_clip(clip, first, last, work, plan["change"], plan["play"])
        plan["usd"] += usd
        notes.append(note)
        if tr:
            return done("%s; clip %.2f-%.2f s at %.2fx" % (plan["change"], tr[0], tr[1], tr[2]), morph=True,
                        check=notes, **{"in": tr[0], "out": tr[1], "rate": tr[2]})
    if os.path.exists(clip):
        os.replace(clip, os.path.join(work, "clip.rejected.mp4"))   # kept to look at; the job never ships it
    return done("no clean clip in %d tries: %s" % (tries, " | ".join(notes)), check=notes)


def opener(tid):
    """The hook beat's `open` for the render job ({"clip": {...}}) and the clip file, or (None, None)."""
    pl = plan_of(tid)
    clip = L.p("work", tid, CLIP)
    if not pl.get("morph") or not os.path.exists(clip):
        return None, None
    return {"clip": {"src": CLIP, "in": pl["in"], "out": pl["out"], "rate": pl["rate"]}}, clip


def play_seconds(tid):
    """Seconds the clip opener plays for (0 without one): the cover is taken after it."""
    op, _ = opener(tid)
    return round((op["clip"]["out"] - op["clip"]["in"]) / op["clip"]["rate"], 2) if op else 0.0
