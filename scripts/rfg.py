"""rfg.sh <command> ...  (see SKILL.md). Every command reads and writes the skill's own data home ($RFG_HOME)."""
import argparse, concurrent.futures as cf, datetime as dt, json, os, sys
import rfg_lib as L
from rfg_lib import Fatal, log, p


def cmd_init(a):
    home = L.init_home()
    os.makedirs(p("stills", "sprites"), exist_ok=True)
    n = len([f for f in os.listdir(p("stills", "sprites")) if f.startswith(L.CFG["sprites"]["outfit"] + "_")])
    log("data home %s ready (%d narrator sprite(s) in stills/sprites/)" % (home, n))


def cmd_status(a):
    rows = L.topics()
    by = {}
    for r in rows:
        by.setdefault(r["status"], []).append(r["id"])
    log("data home: %s" % L.HOME)
    for s in L.STATUSES:
        if by.get(s):
            log("  %-9s %s" % (s, " ".join(by[s])))
    log("hook rotation (times scripted): %s" % ", ".join("%s=%d" % kv for kv in L.rotation().items()))
    posted = L.jsonl("posted.jsonl")
    log("posted: %d (last: %s)" % (len(posted), posted[-1]["id"] + " " + posted[-1]["t"] if posted else "none"))
    nx = L.next_topic()
    log("next suggested: %s" % ("%s (%s, %s)" % (nx["id"], nx["template"], nx["subject"]) if nx else "none ready"))


def cmd_hooks(a):
    for k, t in L.HOOKS["templates"].items():
        log("%-3s %-22s %s   [%s]" % (k, t["name"], " ".join(t["lines"]), t["source"]))


def cmd_photo(a):
    t = L.topic(a.id)
    f = L.fetch_photo(t)
    log("%s: %s (credit: %s)" % (a.id, f, t["photo"]["credit"]))


def cmd_restyle(a):
    t = L.topic(a.id)
    usd = L.restyle_all(t)
    L.set_status(a.id, "restyled")
    log("%s: cutouts %s ($%.3f)" % (a.id, ", ".join(p("stills", L.cut_rel(s)) for s in L.faces_of(t)), usd))


def cmd_copy(a):
    t = L.topic(a.id)
    lines = L.llm_feature_lines(t)
    for f, l in zip(t["features"], lines):
        if not f.get("vo") or a.force:
            f["vo"] = l
    L.save_topic(t)
    for f in t["features"]:
        log("  %-18s %s" % (f["label"], f["vo"]))


def cmd_script(a):
    t = L.topic(a.id)
    s = L.build_script(t)
    bad = L.lint_script(s, t)
    if bad:
        raise Fatal("%s: lint failed:\n  %s" % (a.id, "\n  ".join(bad)))
    wd = p("work", a.id)
    os.makedirs(wd, exist_ok=True)
    json.dump(s, open(os.path.join(wd, "script.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if not any(h["id"] == a.id for h in L.jsonl("hooks.jsonl")):
        L.append("hooks.jsonl", {"t": L.now(), "id": a.id, "template": t["template"], "subject": t.get("subject", ""), "hook": s["beats"][0]["vo"]})
    L.set_status(a.id, "scripted", hook=s["beats"][0]["vo"])
    log("%s: script ok (%d beats): %s" % (a.id, len(s["beats"]), s["beats"][0]["vo"]))


def cmd_lint(a):
    t = L.topic(a.id)
    s = json.load(open(p("work", a.id, "script.json"), encoding="utf-8")) if os.path.exists(p("work", a.id, "script.json")) else L.build_script(t)
    bad = L.lint_script(s, t)
    log("\n".join(bad) if bad else "%s: lint ok" % a.id)
    return 1 if bad else 0


def cmd_tts(a):
    wd = p("work", a.id)
    s = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    vd = os.path.join(wd, "vo")
    if a.force:
        L.shutil.rmtree(vd, ignore_errors=True)
    os.makedirs(vd, exist_ok=True)
    todo = [(i, b["vo"]) for i, b in enumerate(s["beats"]) if not os.path.exists(os.path.join(vd, "%02d.mp3" % i))]
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda x: L.tts(x[1], os.path.join(vd, "%02d.mp3" % x[0])), todo))
    durs = [round(L.mp3_duration(os.path.join(vd, "%02d.mp3" % i)), 3) for i in range(len(s["beats"]))]
    if not all(d > 0.3 for d in durs):
        raise Fatal("voice clip missing or empty: %s" % durs)
    json.dump(durs, open(os.path.join(wd, "durations.json"), "w"))
    L.set_status(a.id, "voiced")
    log("%s: %d clips, %.1f s of voice" % (a.id, len(durs), sum(durs)))


def cmd_render(a):
    """The reel (SLA-1685: the short cut, every platform). An MP4 newer than the script and the voice is not rendered again; --force does."""
    inputs = max(os.path.getmtime(p("work", a.id, f)) for f in ("script.json", "durations.json"))
    mp4 = p("out", a.id + ".mp4")
    if not getattr(a, "force", False) and a.id not in L.cf_jobs() and os.path.exists(mp4) and os.path.getmtime(mp4) > inputs:
        log("%s: %s is up to date (--force renders it again)" % (a.id, mp4))
    else:
        if getattr(a, "force", False) and a.id not in L.cf_jobs() and os.path.exists(mp4):
            os.remove(mp4)
        try:
            out = L.render_cloudflare(a.id, a.wait)
        except L.Pending as e:
            log(str(e))
            return 75
        log("%s: wrote %s (%.1f MB)" % (a.id, out, os.path.getsize(out) / 1e6))
    L.set_status(a.id, "rendered")


def cmd_make(a):
    t = L.topic(a.id)
    if not all(os.path.exists(p("stills", L.cut_rel(s))) for s in L.faces_of(t)):
        cmd_restyle(a)
    cmd_script(a)
    a.force = False
    cmd_tts(a)
    return cmd_render(a)


def cmd_approve(a):
    L.set_status(a.id, "approved")
    log("%s approved" % a.id)


def cmd_posted(a):
    t = L.topic(a.id)
    L.append("posted.jsonl", {"t": L.now(), "id": a.id, "subject": t.get("subject", ""), "template": t["template"], "platform": a.platform, "url": a.url, "stats": {}})
    if t.get("subject"):  # self-diagnosis reels have no subject (their demo faces don't cool down)
        subs = L.subjects()
        subs.setdefault(L.slug(t["subject"]), {"name": t["subject"]}).setdefault("posted", []).append({"id": a.id, "t": L.now(), "url": a.url})
        L.save_subjects(subs)
    L.set_status(a.id, "posted")
    log("%s logged as posted on %s" % (a.id, a.platform))


def cmd_stats(a):
    rows = L.jsonl("posted.jsonl")
    hit = [r for r in rows if r["id"] == a.id]
    if not hit:
        raise Fatal("%s is not in posted.jsonl" % a.id)
    hit[-1]["stats"].update({"views": a.views, "at": L.now()} if a.views is not None else {})
    with open(p("posted.jsonl") + ".tmp", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(p("posted.jsonl") + ".tmp", p("posted.jsonl"))
    log("%s stats: %s" % (a.id, hit[-1]["stats"]))


def cmd_learn(a):
    with open(p("learnings.md"), "a", encoding="utf-8") as f:
        f.write("\n- %s: %s\n" % (L.now()[:10], a.text.strip()))
    log("added to learnings.md")


def day(s):
    return dt.date.fromisoformat(s) if s else dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1)


def cmd_qa(a):
    bad = L.qa(a.id)
    if bad:
        log("QA FAIL %s: %s" % (a.id, "; ".join(bad)))
        return 3
    if [r for r in L.topics() if r["id"] == a.id and r["status"] == "rendered"]:
        L.set_status(a.id, "qa_ok")
    log("QA PASS %s (cover out/%s_cover.jpg)" % (a.id, a.id))


def cmd_host(a):
    h = L.host(a.id)
    log("%s video %s\n%s cover %s" % (a.id, h["mp4"], a.id, h["cover"]))


def cmd_plan(a):
    pl = L.plan(day(a.start), a.days, a.posts)
    for n in pl["notes"]:
        log(n)
    for g in pl["gaps"]:
        log("GAP %s %s: missing %s" % (g["publishAt"], g["reel"], ", ".join(g["missing"])))
    for f in pl["fills"]:
        log("FILL %s %s (%s, %s)" % (f["publishAt"], f["reel"], f["subject"], f["status"]))
    for s in pl["short"]:
        log("SHORT %s: no postable reel left (make one: rfg.sh supply)" % s)
    if a.cmd != "schedule":
        return 1 if pl["short"] else 0
    out = []
    for f in pl["fills"]:
        bad = L.qa(f["reel"])
        if bad:
            log("SKIP %s: QA FAIL %s" % (f["reel"], "; ".join(bad)))
            continue
        got, note = L.payloads(f["reel"], f["publishAt"])
        out += got
        if note:
            log(note)
    for g in pl["gaps"]:
        got, note = L.payloads(g["reel"], g["publishAt"], g["missing"])
        out += got
        if note:
            log(note)
    f = p("state", "schedule-%s.json" % L.now()[:10])
    json.dump({"start": str(day(a.start)), "days": a.days, "posts": out, "short": pl["short"], "notes": pl["notes"]}, open(f, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    log("wrote %s: %d create_social_post payload(s)" % (f, len(out)))
    return 1 if pl["short"] else 0


def cmd_scheduled(a):
    t = L.topic(a.id)
    rec = {"id": a.id, "subject": t.get("subject", ""), "publishAt": a.at, "groupId": a.group, "platforms": a.platforms.split(","), "media": a.media, "cover": a.cover, "t": L.now()}
    L.append("scheduled.jsonl", rec)
    if [r for r in L.topics() if r["id"] == a.id and r["status"] in ("qa_ok", "approved", "rendered")]:
        L.set_status(a.id, "scheduled")
    log("%s recorded: %s group %s" % (a.id, a.at, a.group))


def cmd_supply(a):
    s = L.supply(day(a.start), a.days)
    log("open slots from %s for %d days: %d; postable reels not yet scheduled: %s" % (day(a.start), a.days, s["open"], " ".join(s["ready_left"]) or "none"))
    for r in s["next"]:
        log("  next to make: %s %-3s %s (%s)" % r)
    for r in s["blocked"]:
        log("  blocked: %s %-3s %s" % r)
    log("SUPPLY OK" if not s["open"] else "SUPPLY WARN: %d slot(s) open, make %d reel(s)" % (s["open"], s["open"]))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rfg.sh")
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "status", "hooks"):
        sp.add_parser(name)
    for name in ("photo", "restyle", "script", "lint", "approve"):
        sp.add_parser(name).add_argument("id")
    for name in ("copy", "tts"):
        q = sp.add_parser(name); q.add_argument("id"); q.add_argument("--force", action="store_true")
    for name in ("render", "make"):
        q = sp.add_parser(name); q.add_argument("id"); q.add_argument("--force", action="store_true", help="render again even when the MP4 is up to date")
        q.add_argument("--wait", type=int, default=0, help="seconds to wait for the Cloudflare render (default 0: submit or check, then return)")
    q = sp.add_parser("posted"); q.add_argument("id"); q.add_argument("--platform", required=True); q.add_argument("--url", default="")
    q = sp.add_parser("stats"); q.add_argument("id"); q.add_argument("--views", type=int)
    q = sp.add_parser("learn"); q.add_argument("text")
    for name in ("qa", "host"):
        sp.add_parser(name).add_argument("id")
    for name in ("plan", "schedule", "supply"):
        q = sp.add_parser(name); q.add_argument("--start", help="first day, YYYY-MM-DD (default: tomorrow UTC)")
        q.add_argument("--days", type=int, default=3 if name == "supply" else 1); q.add_argument("--posts", help="saved list_social_posts result")
    q = sp.add_parser("scheduled"); q.add_argument("id"); q.add_argument("--at", required=True); q.add_argument("--group", required=True)
    q.add_argument("--platforms", default="ig,yt,threads,pinterest"); q.add_argument("--media", default=""); q.add_argument("--cover", default="")
    a = ap.parse_args(argv)
    if a.cmd != "init" and not os.path.exists(p("topics.csv")):
        raise Fatal("data home %s is not initialised: run `rfg.sh init`" % L.HOME)
    return globals()["cmd_" + ("plan" if a.cmd == "schedule" else a.cmd)](a) or 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Fatal as e:
        print("rfg: %s" % e, file=sys.stderr)
        sys.exit(2)
