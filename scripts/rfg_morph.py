"""SLA-1728: the clip morph opener of a celebrity reel (reel-factory's facemetric opener, board 27 Nov 2026: "use the same approach").

The full-frame hook shows the painted Commons portrait from frame 0. With the morph, the reel opens on a "before glow-up" version of that
portrait (same face, pose and painted style, worse grooming) and a first/last-frame video clip (OpenRouter /videos) glows it up into the
portrait, then cuts to the portrait still: a real before/after, @glowupmenclub style. Every celebrity reel morphs (board, 27 Nov 2026: "it is
mandatory to morph the genz reels"; the photo → painting morph read as a filter fading in, so the board took the glow-up the same day).
auto() runs before every render of a celebrity reel:

  last   the cutout over a flat background in the hook's own frame position (beats[0].crop), so the composition plays the clip under the
         cutout's alpha and lands on the still
  before BEFORE_MODELS in order (Gemini, then Grok Imagine Image when Gemini refuses) repaint the last frame with worse grooming (messy
         flat hair, patchy beard, ungroomed brows, dull skin, flat light), aligned back onto it with MediaPipe's face mesh. A vision check
         wants the same person and a difference a viewer sees at phone size; one retry per model
  model  MODELS in order, Grok Imagine Video first. Veo is not used (board, 27 Nov: "dont use veo"). A refusal moves on to the next model
  check  the clip's frames are checked (blink, mouth, camera move, hands, broken face, a different person), trimmed to the clean stretch
         that reaches the portrait, holding the "before" HOLD s first (the clip is padded with its first frame when it changes too early);
         a failed check gets a new clip, up to TRIES clips. When none is clean the last take still plays (trimmed as if clean, `forced` in
         morph.json) so the reel never loses its morph; look at those by eye

The decision is kept in work/<id>/morph.json, the "before" in work/<id>/morph/before.jpg and the clip in work/<id>/morph/clip.mp4, so a
re-render costs nothing; `rfg.sh morph <id> --redo` decides again. A new cutout (restyle) also decides again. RFG_MORPH=off skips it. About
$0.07 for the "before", $0.26 a clip and a cent of checks. Needs PIL, numpy, OpenCV and mediapipe (reel-factory's pylib, put on PYTHONPATH
by rfg.sh) and models/face_landmarker.task in the data home; without them the reel keeps its still hook."""
import base64, hashlib, json, os, shutil, subprocess, time, urllib.error, urllib.request

import rfg_lib as L

# the video models in order (first/last-frame clips over OpenRouter /videos); pack config.json "morph": {"models": [...]} overrides
MODELS = L.CFG.get("morph", {}).get("models") or [
    {"model": "x-ai/grok-imagine-video-1.5", "seconds": 3, "resolution": "480p", "usd_per_clip": 0.26},
    {"model": "minimax/hailuo-3-max", "seconds": 5, "resolution": "480p", "usd_per_clip": 0.25}]
MCFG = MODELS[0]
# the "before glow-up" still: image edit models in order (Gemini via chat completions, Grok Imagine Image via /images/generations)
BEFORE_MODELS = L.CFG.get("morph", {}).get("before_models") or [
    {"model": L.CFG["restyle"]["model"], "api": "chat"},
    {"model": "x-ai/grok-imagine-image-2.0", "api": "images"}]
BEFORE_TRIES = 2              # "before" stills per model at most (the vision check rejected the first)
TRIES = 3                     # clips per reel at most (a refusal moves on to the next model)
FRAME = (1080, 1920)          # the reel frame
VEO = (720, 1280)             # the first/last frames sent to the model (9:16; the composition fills the reel frame with the clip)
HOOK_CROP = {"w": 1400, "x": -160, "y": 250}   # engine theme.ts HOOK_FULL.crop
BG = (34, 12, 48)             # flat background behind both frames (masked away by the cutout's alpha in the reel)
PLAN, CLIP, BEFORE = "morph.json", "morph/clip.mp4", "morph/before.jpg"
KIND = "glowup"               # morph.json keys start with it: a decision of the old photo → painting morph is made again
PLAY = 2.3                    # seconds the trimmed clip plays for: the "before" held HOLD s, then the glow-up
HOLD = 0.3                    # the "before" shows still this long so it registers
HOOK_HOLD = 0.6               # the still shows at least this long before the first feature cut
RATE = (1.0, 2.0)             # playback speed range
MIN_PLAY = 0.8                # a clean stretch shorter than this (played) is no morph
LAND_GAP = 0.03               # the cut to the portrait may jump at most this mean grey level in the changing area
GROOM = {
    "M": ("messy, flat, unwashed-looking hair with no shape; a patchy, uneven, untrimmed beard or stubble (keep a clean-shaven face "
          "clean-shaven but with a faint uneven shadow); thick ungroomed eyebrows with stray hairs; dull, tired, slightly uneven skin with "
          "mild under-eye shadows; flat dull lighting"),
    "W": ("unstyled, flat, frizzy hair pulled back carelessly; no makeup at all; ungroomed natural eyebrows; dull, tired, slightly uneven "
          "skin with mild under-eye shadows; flat dull lighting")}
BEFORE_PROMPT = ("Edit this painted portrait into the \"before glow-up\" version of the same person, for a before/after reel. Keep exactly "
                 "the same person and likeness, face shape, eyes, nose, lips, head position, pose, expression, framing, camera distance, "
                 "clothing, the flat dark purple background and the same painted digital-painting style. Change only the grooming: %s. "
                 "Not ugly, not ill, not older: the same person on an unkempt day. No text. Vertical 9:16, same composition.")
BEFORE_CHECK = ("Image 1 is a \"before glow-up\" edit of image 2, a painted portrait, for a before/after reel that morphs image 1 into image "
                "2 full screen on a phone in about 2 seconds. Answer JSON only: {\"same_person\": true|false (clearly the same person, "
                "same pose and framing), \"visible\": true|false (a viewer sees the grooming difference at phone size in 2 seconds), "
                "\"defects\": [str] (broken face, text, a changed background or pose), \"change\": \"what changes from image 1 to image 2, "
                "as a clause that completes 'while ...', e.g. 'the messy hair gets styled into a clean quiff, the patchy beard is trimmed "
                "and the skin turns clear and glowing', at most 25 words\"}")
PROMPT = ("Locked-off static camera, head-and-shoulders painted portrait on a plain dark purple background, a glow-up transformation. The "
          "same person keeps the same pose, head position and expression for the whole clip while %s, a smooth continuous morph from the "
          "first frame into the last frame. No camera movement, no head movement, no blinking, no talking, no hands or objects entering "
          "the frame, no text.")
CHECK = ("Image 1 is a contact sheet of %d frames (left to right, top to bottom, each labelled with its second) from a %d s AI video that "
         "glows up a \"before\" version of a painted portrait from its first frame into image 2 (the portrait it must land on). The "
         "intended change: %s. That change, including the soft blend while it happens and %s, is expected: never flag it. For every frame "
         "flag only what a viewer would see as a mistake: closed or half-closed eyes (a blink), a squint, a new smile, an open or moving "
         "mouth, %sa camera move or zoom, hands or objects, text, or a broken face (melting, doubled or missing features). Answer JSON "
         "only: {\"frames\": [{\"t\": 0.25, \"ok\": true, \"issue\": \"\"}, ...], \"change_starts\": <the second label of the first frame "
         "where the intended change is visibly under way>, \"same_person\": true|false (false only when the face clearly becomes someone "
         "else)}")


class Unavailable(Exception):
    """The morph cannot run on this host (libraries or the face model missing): the reel keeps its still hook, nothing is recorded."""


class Refused(Exception):
    """The video model's content filter refused the frames (Veo and Wan refuse many public figures' photos). Never retried on the same
    model: the filter is the provider's policy, not a glitch. auto() moves on to the next model in MODELS."""


def qa_times(seconds):
    """The clip times the vision check looks at: every quarter second, and the last frame."""
    return [round(0.25 * i, 2) for i in range(1, int((seconds - 0.05) / 0.25) + 1)] + [round(seconds - 0.05, 2)]


QA_TIMES = qa_times(MCFG["seconds"])


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
    """Similarity transform (2x3) taking one image's face mesh onto another's, and its median error over the eye distance."""
    import cv2
    import numpy as np
    m, _ = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.LMEDS)
    if m is None:
        return None, 9.0
    moved = src_pts @ m[:, :2].T + m[:, 2]
    eyes = float(np.linalg.norm(dst_pts[33] - dst_pts[263])) or 1.0
    return m, float(np.median(np.linalg.norm(moved - dst_pts, axis=1)) / eyes)


def last_frame(script, cut, work):
    """last.jpg: the portrait over BG in the hook's own frame position, a whole reel frame at the clip's size."""
    from PIL import Image
    x, y, w, h = hook_rect(script)
    co = Image.open(cut).convert("RGBA")
    layer = Image.new("RGBA", FRAME, (0, 0, 0, 0))
    layer.paste(co.resize((round(w), round(h)), Image.LANCZOS), (round(x), round(y)))
    os.makedirs(work, exist_ok=True)
    lp = os.path.join(work, "last.jpg")
    Image.alpha_composite(Image.new("RGBA", FRAME, BG + (255,)), layer).convert("RGB").resize(VEO, Image.LANCZOS).save(lp, "JPEG", quality=92)
    return lp


def align(src, dst, out):
    """Writes `src` (an edit of `dst`) moved onto `dst` with a similarity transform on MediaPipe's face mesh, at VEO size, so the clip's
    first and last frames have the face in the same place. Returns the fit error, or None when a face is not found (written unmoved)."""
    import cv2
    import numpy as np
    from PIL import Image
    s = np.asarray(Image.open(src).convert("RGB").resize(VEO, Image.LANCZOS))
    a, b = mesh(s), mesh(np.asarray(Image.open(dst).convert("RGB")))
    m, err = fit(a, b) if a is not None and b is not None else (None, None)
    if m is not None:
        s = cv2.warpAffine(s, m, VEO, flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    Image.fromarray(s).save(out, "JPEG", quality=92)
    return round(err, 4) if m is not None else None


def gen_before(last, out, gender, cfg):
    """One "before glow-up" edit of `last` on image model `cfg` (a BEFORE_MODELS entry). Returns the API cost; raises Refused when the
    model refuses or returns no image, L.Fatal on an HTTP error."""
    prompt = BEFORE_PROMPT % GROOM.get(gender, GROOM["M"])
    ref = {"type": "image_url", "image_url": {"url": L.durl(last)}}
    if cfg.get("api") == "images":
        j = _call("/images/generations", {"model": cfg["model"], "prompt": prompt, "n": 1, "aspect_ratio": "9:16", "input_references": [ref]})
        d = (j.get("data") or [{}])[0]
        cost = (j.get("usage") or {}).get("cost") or 0
        if d.get("b64_json"):
            data = base64.b64decode(d["b64_json"])
        elif d.get("url"):
            data = urllib.request.urlopen(d["url"], timeout=120).read() if d["url"].startswith("http") else base64.b64decode(d["url"].split(",", 1)[1])
        else:
            L.spend("image", cost)
            raise Refused("no image: %s" % json.dumps(j)[:200])
    else:
        j = _call("/chat/completions", {"model": cfg["model"], "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, ref]}],
                                        "modalities": ["image", "text"], "usage": {"include": True}, "image_config": {"aspect_ratio": "9:16"}})
        cost = (j.get("usage") or {}).get("cost") or 0
        try:
            data = base64.b64decode(j["choices"][0]["message"]["images"][0]["image_url"]["url"].split(",", 1)[1])
        except (KeyError, IndexError, TypeError, ValueError):
            L.spend("image", cost)
            raise Refused("no image: %s" % json.dumps(j)[:200])
    L.spend("image", cost)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(data)
    return cost


FALLBACK_CHANGE = "the messy hair gets styled, the brows are groomed and the dull skin turns clear and glowing"


def before(last, work, gender):
    """(before.jpg or None, change clause or why not, usd, notes): the "before glow-up" still, aligned onto `last` and checked. When no
    take passes, the last one made is used anyway (mandatory morph; the note says "forced"); None only when every model refused."""
    usd, notes, made = 0.0, [], False
    out = os.path.join(work, "before.jpg")
    for cfg in BEFORE_MODELS:
        for i in range(BEFORE_TRIES):
            raw = os.path.join(work, "before_raw.png")
            try:
                usd += gen_before(last, raw, gender, cfg)
            except Refused as e:
                notes.append("%s refused: %s" % (cfg["model"], str(e)[:120]))
                break
            except L.Fatal as e:
                notes.append("%s: %s" % (cfg["model"], str(e)[:120]))
                break
            align(raw, last, out)
            made = True
            j, c = L.chat_json(BEFORE_CHECK, [out, last])
            usd += c
            change = " ".join(str(j.get("change") or "").split()).rstrip(".")
            if j.get("same_person") and j.get("visible") and not j.get("defects") and change:
                notes.append("%s: ok" % cfg["model"])
                return out, change, usd, notes
            notes.append("%s take %d: %s" % (cfg["model"], i + 1, "; ".join(
                [k for k in ("same_person", "visible") if not j.get(k)] + [str(d) for d in j.get("defects") or []]) or j.get("notes") or "no change"))
    if made:
        notes.append("forced: no take passed, the last one is used")
        return out, FALLBACK_CHANGE, usd, notes
    return None, "no \"before\" still: %s" % " | ".join(notes), usd, notes


# ------------------------------------------------------------------ the clip
def _call(url, body=None):
    req = urllib.request.Request(url if url.startswith("http") else L.OR_BASE + url, json.dumps(body).encode() if body else None,
                                 {"Authorization": "Bearer " + os.environ["OPEN_ROUTER_API_KEY"], "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        raise L.Fatal("OpenRouter HTTP %s %s" % (e.code, e.read()[:300].decode(errors="replace")))


def gen_clip(first, last, change, out, timeout=900, cfg=None):
    """One first/last-frame clip on model `cfg` (a MODELS entry; OpenRouter /videos, submit then poll). Writes the MP4, returns the
    API-reported cost."""
    L.need_env("OPEN_ROUTER_API_KEY")
    cfg = cfg or MCFG
    j = _call("/videos", {"model": cfg["model"], "prompt": PROMPT % change, "duration": cfg["seconds"],
                          "aspect_ratio": "9:16", "resolution": cfg["resolution"], "generate_audio": False,
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
    usd = (j.get("usage") or {}).get("cost") or cfg["usd_per_clip"]
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


def hold_for(play):
    """Seconds the "before" shows still at the start of a clip that plays `play` s: HOLD, a quarter of a short one."""
    return round(min(HOLD, play / 4), 2)


def trim(frames, ok, first, last, start=None, play=PLAY):
    """(in, out, rate) of the clean stretch of the clip that reaches the portrait, else None. `ok` = {t: clean}; a frame's progress is
    how far it is from the first frame towards the last (0-1) in the area that changes: `in` is a quarter second before the change starts
    (`start`, the vision check's frame, else measured), `out` the last clean frame before the first unclean one after `in`, which must be
    at least 85 % of the way or close enough to the portrait (LAND_GAP) that the cut to it does not jump. `rate` plays in → out in
    `play` less the "before" hold (hold_for), which hold() puts in front."""
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
    late = 0.75 * (ts[-1] + 0.05)       # the change must start in the first three quarters of the clip
    if isinstance(start, (int, float)) and 0 < start < late:
        t_in = round(max(0.0, start - 0.25), 2)
    else:
        t_in = max([0.0] + [t for t in ts if prog[t] < 0.15 and t < late])
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
    rate = min(RATE[1], max(RATE[0], (t_out - t_in) / (play - hold_for(play))))
    if (t_out - t_in) / rate < MIN_PLAY - hold_for(play):
        return None
    return t_in, t_out, round(rate, 2)


def hold(take, tr, play, out):
    """Writes the clip the reel plays: frame `in` of `take` held still for the "before" hold (hold_for(play) played), then `in` → `out`.
    Returns the opener's (in, out, rate) on the new clip (in is 0)."""
    import cv2
    t_in, t_out, rate = tr
    cap = cv2.VideoCapture(take)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    cap.set(cv2.CAP_PROP_POS_MSEC, t_in * 1000)
    frames = []
    while True:
        ok, fr = cap.read()
        if not ok or len(frames) > (t_out - t_in) * fps + 1:
            break
        frames.append(fr)
    cap.release()
    if not frames:
        raise L.Fatal("could not read %s from %.2f s" % (take, t_in))
    n = round(hold_for(play) * rate * fps)
    pad = n / fps
    cmd, env = L.ff("ffmpeg")      # Remotion's ffmpeg has no rawvideo demuxer and few filters: PNG frames over image2pipe
    p = subprocess.Popen(cmd + ["-v", "error", "-y", "-f", "image2pipe", "-c:v", "png", "-framerate", "%.3f" % fps, "-i", "-", "-an",
                                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-f", "mp4", out + ".part"], stdin=subprocess.PIPE, env=env)
    for fr in [frames[0]] * n + frames:
        p.stdin.write(cv2.imencode(".png", fr)[1].tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise L.Fatal("ffmpeg could not write %s" % out)
    os.replace(out + ".part", out)
    return 0.0, round(pad + (len(frames) - 1) / fps, 2), rate


def clip_seconds(clip):
    import cv2
    cap = cv2.VideoCapture(clip)
    n, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS) or 24
    cap.release()
    return n / fps if n > 0 else MCFG["seconds"]


def check_clip(clip, first, last, work, change, play=PLAY):
    """(trim or None, notes, usd): the vision check of a generated clip, then trim()."""
    secs = clip_seconds(clip)
    times = qa_times(round(secs * 4) / 4)
    fr = clip_frames(clip, times)
    if len(fr) < len(times) - 2:
        return None, "could not read the clip's frames", 0.0
    sheet = contact_sheet(fr, os.path.join(work, "check.jpg"))
    j, usd = L.chat_json(CHECK % (len(fr), round(secs), change, "a slight shift of the head or expression towards the portrait's",
                                  "a head turn or tilt, "), [sheet, last])
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


def cutout(script):
    """The hook face's painted cutout."""
    return L.p("stills", script["assets"][script["beats"][0]["img"]])


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


def auto(tid, redo=False, tries=TRIES):
    """Makes the glow-up clip morph for reel `tid` (see the module doc) and records it in work/<id>/morph.json. Returns the plan
    {"morph": bool, "why", ...}, or None when it does not apply or cannot run here (the reel keeps its still hook). A recorded
    no-morph (no "before" passed, every model refusing) is never final: the next render tries again."""
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
    cut = cutout(script)
    durs = json.load(open(os.path.join(wd, "durations.json"))) if os.path.exists(os.path.join(wd, "durations.json")) else []
    key = "%s-%s-%s" % (KIND, _key(cut), json.dumps(script["beats"][0].get("crop") or HOOK_CROP, sort_keys=True))
    old, clip, bpath = plan_of(tid), os.path.join(wd, CLIP), os.path.join(wd, BEFORE)
    if not redo and old.get("key") == key and old.get("morph") and os.path.exists(clip):
        return old
    plan = {"key": key, "kind": KIND, "morph": False, "usd": 0.0, "play": play_for(durs)}
    work = os.path.join(wd, "morph")

    def done(why, **kw):
        plan.update(why=why, **kw)
        plan["usd"] = round(plan["usd"], 3)
        json.dump(plan, open(os.path.join(wd, PLAN), "w"), indent=1)
        L.log("  morph %s: %s (%s)" % (tid, "glow-up clip opener" if plan["morph"] else "no morph, still hook", why))
        return plan

    last = last_frame(script, cut, work)
    if not redo and old.get("key") == key and old.get("change") and os.path.exists(bpath):
        first, plan["change"], plan["before_check"] = bpath, old["change"], old.get("before_check")
    else:
        first, change, usd, bnotes = before(last, work, t.get("gender") or "M")
        plan["usd"] += usd
        if first is None:
            return done(change, before_check=bnotes)
        plan["change"], plan["before_check"] = change, bnotes
    notes, takes, models = [], [], list(MODELS)
    for attempt in range(tries):
        if not models:
            break
        take = os.path.join(work, "take%d.mp4" % (attempt + 1))
        try:
            plan["usd"] += gen_clip(first, last, plan["change"], take, cfg=models[0])
        except Refused as e:
            notes.append("%s refused: %s" % (models.pop(0)["model"], str(e)[:120]))
            continue
        plan["model"] = models[0]["model"]
        tr, note, usd = check_clip(take, first, last, work, plan["change"], plan["play"])
        plan["usd"] += usd
        notes.append(note)
        if tr:
            op = hold(take, tr, plan["play"], clip)
            return done("%s; clip %.2f-%.2f s at %.2fx after a %.2f s hold" % (plan["change"], tr[0], tr[1], tr[2], hold_for(plan["play"])),
                        morph=True, check=notes, take={"in": tr[0], "out": tr[1]}, **{"in": op[0], "out": op[1], "rate": op[2]})
        takes.append((0 if note == "clean" else len(note.split("; ")), take, models[0]["model"]))
    if not takes:
        return done("every video model refused: %s" % " | ".join(notes), check=notes)
    # mandatory morph: the take with the fewest flagged frames plays, trimmed as if clean
    _, take, plan["model"] = min(takes)
    fr = clip_frames(take, qa_times(round(clip_seconds(take) * 4) / 4))
    ts = sorted(fr)
    tr = trim(fr, {t: True for t in ts}, first, last, None, plan["play"]) or (
        0.0, ts[-1], round(min(RATE[1], max(RATE[0], ts[-1] / (plan["play"] - hold_for(plan["play"])))), 2))
    op = hold(take, tr, plan["play"], clip)
    return done("%s; no clean take in %d, the best one plays: clip %.2f-%.2f s at %.2fx" % (plan["change"], len(takes), tr[0], tr[1], tr[2]),
                morph=True, forced=True, check=notes, take={"in": tr[0], "out": tr[1]}, **{"in": op[0], "out": op[1], "rate": op[2]})


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
