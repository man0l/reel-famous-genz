"""reel-famous-genz unit tests (stdlib unittest, no network, no API spend): python3 -m unittest discover -s tests"""
import json, os, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
TMP = tempfile.mkdtemp(prefix="rfg-test-")
os.environ["RFG_HOME"] = TMP
import rfg_lib as L  # noqa: E402

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (896).to_bytes(4, "big") + (1200).to_bytes(4, "big") + b"\x08\x06\x00\x00\x00")


def seed_topic(tid):
    return json.load(open(os.path.join(HERE, "..", "seed", "topics", tid + ".json"), encoding="utf-8"))


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        L.init_home()
        os.makedirs(L.p("stills", "sprites"), exist_ok=True)
        for pose in L.CFG["sprites"]["poses"]:
            open(L.p("stills", "sprites", "%s_%s.png" % (L.CFG["sprites"]["outfit"], pose)), "wb").write(PNG)
        for name in ("Barry Keoghan", "Timothée Chalamet", "Austin Butler", "Jacob Elordi"):
            os.makedirs(os.path.dirname(L.p("stills", L.cut_rel(name))), exist_ok=True)
            open(L.p("stills", L.cut_rel(name)), "wb").write(PNG)
        os.makedirs(os.path.dirname(L.p("stills", L.CFG["axend"]["card"])), exist_ok=True)
        open(L.p("stills", L.CFG["axend"]["card"]), "wb").write(PNG)
        subs = L.subjects()
        for name, cr in (("Austin Butler", "Gabriel Hutchinson, CC BY-SA 4.0"), ("Timothée Chalamet", "Harald Krichel, CC BY-SA 4.0"), ("Jacob Elordi", "Raph_PH, CC BY 4.0")):
            subs.setdefault(L.slug(name), {"name": name})["credit"] = cr
        L.save_subjects(subs)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMP, ignore_errors=True)


class Hooks(Base):
    def test_templates_are_glowupmenclub_lines(self):
        t = {"template": "A", "subject": "Barry Keoghan", "gender": "M"}
        self.assertEqual(L.hook_lines(t), ["Why does Barry Keoghan look so attractive?"])
        t = {"template": "A'", "subject": "Timothée Chalamet", "gender": "M"}
        self.assertEqual(" ".join(L.hook_lines(t)), "What made Timothée Chalamet so attractive? He was every girl's crush.")
        t = {"template": "A'", "subject": "Sadie Sink", "gender": "W"}
        self.assertEqual(L.hook_lines(t)[1], "She was every guy's crush.")
        t = {"template": "A+", "subject": "Austin Butler", "gender": "M", "slots": {"event": "Elvis"}}
        self.assertEqual(L.hook_lines(t)[1], "And how did he completely change his look after Elvis?")

    def test_slot_whitelist(self):
        with self.assertRaises(L.Fatal):
            L.hook_lines({"template": "B", "subject": "X Y", "slots": {"noun": "footballer"}})
        self.assertEqual(L.hook_lines({"template": "B", "subject": "X Y", "slots": {"noun": "actor"}})[1], "His name is X Y.")

    def test_missing_slot(self):
        with self.assertRaises(L.Fatal):
            L.hook_lines({"template": "A+", "subject": "Austin Butler"})


class Script(Base):
    def test_seed_topics_build_and_lint_clean(self):
        for tid in ("RSG0001", "RSG0002"):
            t = seed_topic(tid)
            s = L.build_script(t)
            self.assertEqual(L.lint_script(s, t), [], tid)
            kinds = [b["kind"] for b in s["beats"]]
            self.assertEqual(kinds[:2], ["hook", "feature"], "SLA-1685: no spoken bridge, the hook cuts to the first feature")
            self.assertEqual(kinds[-2:], ["walkout", "axend"], "SLA-1685: the game card hands over to the Axend card")
            self.assertEqual(s["lane"], "B")
            self.assertNotIn("let's break down", " ".join(b["vo"] for b in s["beats"]))
            ax = s["beats"][-1]
            self.assertEqual((ax["img"], ax["card"], ax["vo"]), ("cut", "axend_card", "Want your own face card? Scan yours in Axend."))
            self.assertEqual(s["assets"]["axend_card"], L.CFG["axend"]["card"])
            self.assertIn("Wikimedia Commons", s["cite"])
            self.assertTrue(s["cite"].endswith("AI-edited images"))

    def test_lint_catches_reworded_hook_and_banned_framing(self):
        t = seed_topic("RSG0001")
        s = L.build_script(t)
        s["beats"][0]["vo"] = "If Barry Keoghan debuted in a boy group, which position would he get?"
        bad = L.lint_script(s, t)
        self.assertTrue(any(b.startswith("hook:") for b in bad))
        self.assertTrue(any("boy group" in b for b in bad))

    def test_lint_catches_score_link_and_long_lines(self):
        t = seed_topic("RSG0001")
        s = L.build_script(t)
        s["beats"][-1]["vo"] = "Comment link and I'll send you the app."
        s["beats"][2]["vo"] = "He is a solid 8/10 and that is honestly a really really really high score."
        bad = " | ".join(L.lint_script(s, t))
        for want in ("comment link", "score out of 10", "spoken line has"):
            self.assertIn(want, bad)

    def test_feature_count_and_missing_vo(self):
        t = seed_topic("RSG0001")
        t["features"] = t["features"][:3]
        with self.assertRaises(L.Fatal):
            L.build_script(t)
        t = seed_topic("RSG0001")
        t["features"][0].pop("vo")
        with self.assertRaises(L.Fatal):
            L.build_script(t)

    def test_hot_words_are_spoken(self):
        s = L.build_script(seed_topic("RSG0002"))
        for b in s["beats"]:
            spoken = {L.bare(w) for w in b["vo"].split()}
            for h in b.get("hot", []):
                self.assertIn(L.bare(h), spoken)

    def test_long_callout_label_stays_in_frame(self):
        for tid in ("RSG0001", "RSG0007"):
            t = seed_topic(tid)
            s = L.build_script(t)
            for b in s["beats"]:
                for c in b.get("callouts") or []:
                    self.assertLessEqual(L.label_right(c["pos"], c["label"]), L.CALLOUT_RIGHT, (tid, c["label"]))
            s["beats"][4]["callouts"][0]["pos"] = [580, 1120]
            self.assertIn("past the frame", " | ".join(L.lint_script(s, t)))


D_TOPIC = {"id": "RSG0009", "template": "D", "subject": "", "slots": {"a": "Blue eyes", "b": "brown eyes"},
           "sides": {"a": "Barry Keoghan", "b": "Jacob Elordi"}, "hook_card": {"head": ["BLUE OR", "*BROWN?*"]},
           "features": [{"label": "Eye colour", "chips": ["cooler", "warmer"], "vo": "Blue reads cooler. Brown reads warmer."},
                        {"label": "Bone structure", "vo": "But the frame around the eyes matters more."}],
           "turn": {"lines": ["colour is", "*not the point.*"], "vo": "Colour is not the point. Structure is."}}


class SelfDiagnosis(Base):
    """C, D and E have no celebrity: a topic card opens them, the body is checks / numbered types / A-B rounds, each kind has its own comment prompt."""

    def test_selftest_E_is_narrator_led(self):
        t = seed_topic("RSG0010")
        s = L.build_script(t)
        self.assertEqual(L.lint_script(s, t), [])
        self.assertEqual([b["kind"] for b in s["beats"]], ["topic", "narrator", "check", "check", "check", "cta"])
        hook = s["beats"][0]
        self.assertEqual(hook["vo"], "It is actually really easy to tell if you are attractive to girls.")
        self.assertNotIn("card", hook)  # no name photocard
        self.assertNotIn("imgs", hook)  # the narrator stands under the topic card
        self.assertEqual(hook["pills"], ["1", "2", "3"])
        self.assertEqual([b["n"] for b in s["beats"][2:5]], [1, 2, 3])
        self.assertEqual(s["beats"][2]["img"], "cut_austin_butler")
        self.assertNotIn("img", s["beats"][4])  # posture: the narrator alone
        self.assertEqual(s["beats"][-1]["vo"], "Comment which one you passed.")
        self.assertEqual(s["episode_type"], "self_diagnosis")
        self.assertNotIn("name", s)
        self.assertIn("Gabriel Hutchinson", s["cite"])
        self.assertIn("Harald Krichel", s["cite"])

    def test_types_C_number_every_type_on_one_demo_face(self):
        t = seed_topic("RSG0007")
        s = L.build_script(t)
        self.assertEqual(L.lint_script(s, t), [])
        kinds = [b["kind"] for b in s["beats"]]
        self.assertEqual(kinds, ["topic", "narrator"] + ["type"] * 6 + ["cta"])
        self.assertEqual(s["beats"][0]["imgs"], ["cut_austin_butler"])
        self.assertEqual([b["n"] for b in s["beats"][2:8]], [1, 2, 3, 4, 5, 6])
        self.assertEqual({b["img"] for b in s["beats"][2:8]}, {"cut_austin_butler"})
        self.assertEqual(s["beats"][-1]["vo"], "Comment your type.")
        self.assertEqual(s["beats"][-1]["pills"], ["1", "2", "3", "4", "5", "6"])

    def test_compare_D_side_by_side(self):
        t = dict(D_TOPIC)
        s = L.build_script(t)
        self.assertEqual(L.lint_script(s, t), [])
        self.assertEqual([b["kind"] for b in s["beats"]], ["topic", "narrator", "versus", "versus", "narrator", "cta"])
        self.assertEqual(s["beats"][0]["vo"], "Blue eyes or brown eyes? Which do you find more attractive?")
        self.assertEqual(s["beats"][0]["labels"], ["A", "B"])
        self.assertEqual(s["beats"][2]["imgs"], ["cut_barry_keoghan", "cut_jacob_elordi"])
        self.assertEqual(s["beats"][2]["chips"], ["cooler", "warmer"])
        self.assertEqual(s["beats"][-1]["vo"], "Comment A or B.")
        with self.assertRaises(L.Fatal):
            L.build_script(dict(D_TOPIC, sides={"a": "Barry Keoghan"}))

    def test_lint_wants_a_topic_card_and_a_comment_prompt(self):
        t = seed_topic("RSG0010")
        s = L.build_script(t)
        s["beats"][0]["kind"] = "hook"
        s["beats"][-1]["vo"] = "Download the app to check."
        bad = " | ".join(L.lint_script(s, t))
        self.assertIn("topic card", bad)
        self.assertIn("starts with", bad)
        t2 = seed_topic("RSG0001")
        s2 = L.build_script(t2)
        s2["beats"][0]["kind"] = "topic"
        self.assertTrue(any("name photocard" in b for b in L.lint_script(s2, t2)))

    def test_body_counts_per_kind(self):
        t = seed_topic("RSG0010")
        t["features"] = t["features"][:2]
        with self.assertRaises(L.Fatal):
            L.build_script(t)
        t = seed_topic("RSG0007")
        t["features"] = t["features"][:3]
        with self.assertRaises(L.Fatal):
            L.build_script(t)

    def test_caption_and_faces_without_subject(self):
        t = seed_topic("RSG0010")
        self.assertEqual(L.faces_of(t), ["Austin Butler", "Timothée Chalamet"])
        c = L.caption(t).split("\n")
        self.assertEqual(c[0], "It is actually really easy to tell if you are attractive to girls.")
        self.assertTrue(c[1].endswith("Comment which one you passed."))
        self.assertIn("Gabriel Hutchinson", c[2])
        self.assertEqual(c[3].split()[0], "#selftest")


class Memory(Base):
    def test_rotation_and_next(self):
        nx = L.next_topic()
        self.assertIsNotNone(nx)
        L.append("hooks.jsonl", {"t": L.now(), "id": nx["id"], "template": nx["template"], "subject": nx["subject"], "hook": "x"})
        self.assertEqual(L.rotation()[nx["template"]], 1)
        nx2 = L.next_topic()
        self.assertNotEqual(nx2["template"], nx["template"])

    def test_status_roundtrip(self):
        L.set_status("RSG0003", "ready")
        self.assertEqual({r["id"]: r["status"] for r in L.topics()}["RSG0003"], "ready")
        with self.assertRaises(L.Fatal):
            L.set_status("RSG0003", "nonsense")


class Schedule(Base):
    A, Y, T, P = (L.SCHED["accounts"][k] for k in ("instagram", "youtube", "threads", "pinterest"))

    def setUp(self):
        open(L.p("scheduled.jsonl"), "w").close()
        for tid, st in (("RSG0001", "qa_ok"), ("RSG0002", "approved")):
            L.set_status(tid, st)
            open(L.p("out", tid + ".mp4"), "wb").write(b"x")

    def tearDown(self):
        for tid in ("RSG0001", "RSG0002"):
            os.remove(L.p("out", tid + ".mp4"))

    def test_board_approved_first_then_qa_ok(self):
        pl = L.plan(L.dt.date(2030, 1, 1), 1)
        self.assertEqual([(f["publishAt"], f["reel"]) for f in pl["fills"]],
                         [("2030-01-01T13:00:00Z", "RSG0002"), ("2030-01-01T20:00:00Z", "RSG0001")])
        self.assertEqual(pl["short"], [])
        self.assertEqual(L.plan(L.dt.date(2030, 1, 1), 2)["short"], ["2030-01-02T13:00:00Z", "2030-01-02T20:00:00Z"])

    def test_scheduled_reel_is_not_reused_and_subject_cools_down(self):
        L.append("scheduled.jsonl", {"id": "RSG0002", "subject": "Timothée Chalamet", "publishAt": "2030-01-01T13:00:00Z", "groupId": "g1", "platforms": ["ig", "yt", "threads", "pinterest"]})
        pl = L.plan(L.dt.date(2030, 1, 1), 2)
        self.assertEqual([f["reel"] for f in pl["fills"]], ["RSG0001"])
        self.assertEqual(len(pl["short"]), 2)

    def test_calendar_gaps_mixing_and_missing(self):
        L.append("scheduled.jsonl", {"id": "RSG0002", "subject": "Timothée Chalamet", "publishAt": "2030-01-01T13:00:00Z", "groupId": "g1", "platforms": ["ig", "yt"]})
        L.append("scheduled.jsonl", {"id": "RSG0009", "subject": "Nobody", "publishAt": "2030-01-02T13:00:00Z", "groupId": "gone", "platforms": ["ig"]})
        acc = lambda i, prov, st="QUEUE": {"provider": prov, "account": {"id": i}, "state": st, "error": None}
        cal = {"posts": [
            {"groupId": "g1", "publishAt": "2030-01-01T13:00:00.000Z", "media": [{"url": "https://x/a.mp4"}], "posts": [acc(self.A, "instagram"), acc(self.Y, "youtube")]},
            {"groupId": "fm", "publishAt": "2030-01-01T20:00:00.000Z", "media": [{"url": "https://reel-remotion.w/publish/F0170/F0170.mp4"}], "posts": [acc(self.A, "instagram")]}]}
        f = L.p("tmp-cal.json")
        json.dump({"content": [{"type": "text", "text": json.dumps(cal)}]}, open(f, "w"))
        pl = L.plan(L.dt.date(2030, 1, 1), 2, f)
        self.assertEqual(pl["gaps"], [{"reel": "RSG0002", "publishAt": "2030-01-01T13:00:00Z", "missing": ["threads", "pinterest"]}])
        self.assertTrue(any(n.startswith("MIXING 2030-01-01T20:00:00Z") for n in pl["notes"]))
        self.assertTrue(any(n.startswith("MISSING 2030-01-02T13:00:00Z RSG0009") for n in pl["notes"]))
        self.assertEqual(pl["fills"][0], {"reel": "RSG0001", "publishAt": "2030-01-01T20:00:00Z", "status": "qa_ok", "subject": "Barry Keoghan"})

    def test_self_diagnosis_reels_skip_cooldown_and_blocked_templates_wait(self):
        rows = L.topics()
        for r in rows:
            if r["id"] in ("RSG0007", "RSG0010"):
                r["status"], r["subject"] = "qa_ok", ""
        L.save_topics(rows)
        for tid in ("RSG0007", "RSG0010"):
            open(L.p("out", tid + ".mp4"), "wb").write(b"x")
        try:
            blocked = dict(L.SCHED["blocked_templates"])
            L.SCHED["blocked_templates"] = {}
            pl = L.plan(L.dt.date(2030, 1, 1), 2)
            self.assertEqual(sorted(f["reel"] for f in pl["fills"]), ["RSG0001", "RSG0002", "RSG0007", "RSG0010"])  # two subject-less reels don't cool each other down
            L.SCHED["blocked_templates"] = {"C": "x", "E": "x"}
            pl = L.plan(L.dt.date(2030, 1, 1), 2)
            self.assertEqual(sorted(f["reel"] for f in pl["fills"]), ["RSG0001", "RSG0002"])
        finally:
            L.SCHED["blocked_templates"] = blocked
            for tid in ("RSG0007", "RSG0010"):
                os.remove(L.p("out", tid + ".mp4"))

    def test_caption(self):
        c = L.caption(seed_topic("RSG0001")).split("\n")
        self.assertEqual(c[0], "Why does Barry Keoghan look so attractive?")
        self.assertTrue(c[1].endswith("Comment who I should break down next."))
        self.assertTrue(c[2].endswith("AI-edited images."))
        self.assertLessEqual(len(c[3].split()), 5)


class Retention(Base):
    """SLA-1685: the loop tail, the full-frame hook crop and the Instagram cut (4 callouts, 20-30 s)."""

    def test_loop_tail_and_hook_crop(self):
        t = seed_topic("RSG0001")
        s = L.build_script(t)
        self.assertEqual(s["loop"], 0.8)
        self.assertNotIn("crop", s["beats"][0])
        self.assertEqual(L.lint_script(s, t), [])
        for bad in (0.2, 2.5):
            self.assertTrue(any(x.startswith("loop:") for x in L.lint_script(dict(s, loop=bad), t)), bad)
        s = L.build_script(dict(t, hook_crop={"w": 1500, "x": -210, "y": 200}))
        self.assertEqual(s["beats"][0]["crop"], {"w": 1500, "x": -210, "y": 200})

    def test_cut_seconds_match_the_engine_clock(self):
        # 3 clips: 2 pads of 0.2, end hold 1.2, loop 0.8 (engine timing.ts)
        self.assertAlmostEqual(L.cut_seconds([1, 2, 3], 0.8), 6 + 0.4 + 1.2 + 0.8)

    def test_ig_cut_keeps_four_features_and_every_other_beat(self):
        t = seed_topic("RSG0001")
        s = L.build_script(t)
        kinds = [b["kind"] for b in s["beats"]]
        feats = [i for i, k in enumerate(kinds) if k == "feature"]
        self.assertEqual(len(feats), 6)
        durs = [2.0] + [3.0] * 6 + [3.2, 2.8]
        keep = L.ig_keep(s, durs, t)
        self.assertEqual([kinds[i] for i in keep], ["hook"] + ["feature"] * 4 + ["walkout", "axend"])
        self.assertEqual([i for i in keep if i in feats], feats[:4], "the first four when they fit")
        self.assertTrue(20 <= L.cut_seconds([durs[i] for i in keep], s["loop"], L.IG["ig_end_hold_s"]) <= 30)
        # the first four run long: the four shortest, in order
        long = [2.0, 8.0, 8.0, 2.5, 2.5, 2.6, 2.6, 3.2, 2.8]
        keep = L.ig_keep(s, long, t)
        self.assertEqual([i for i in keep if i in feats], [3, 4, 5, 6])
        # the topic picks
        keep = L.ig_keep(s, durs, dict(t, ig_features=[0, 2, 3, 5]))
        self.assertEqual([i for i in keep if i in feats], [feats[0], feats[2], feats[3], feats[5]])
        with self.assertRaises(L.Fatal):
            L.ig_keep(s, durs, dict(t, ig_features=[0, 1, 9, 2]))
        # A+ (how did the look change?): the change feature always stays
        keep = L.ig_keep(s, long, dict(t, template="A+"))
        self.assertEqual([i for i in keep if i in feats], [3, 4, 5, feats[-1]])
        # four features: no IG cut
        t4 = dict(t, features=t["features"][:4])
        s4 = L.build_script(t4)
        self.assertIsNone(L.ig_keep(s4, [2.0] * len(s4["beats"]), t4))

    def test_lint_rejects_the_old_bridge_and_comment_ending(self):
        t = seed_topic("RSG0001")
        s = L.build_script(t)
        old = dict(s, beats=s["beats"][:1] + [{"kind": "narrator", "lines": ["x"], "vo": "So let's break down what his face actually has."}] + s["beats"][1:])
        self.assertTrue(any(x.startswith("bridge:") for x in L.lint_script(old, t)))
        old = dict(s, beats=s["beats"][:-1] + [{"kind": "cta", "head": ["COMMENT"], "pills": ["A", "B"], "vo": "Comment who I should break down next."}])
        self.assertTrue(any(x.startswith("cta:") for x in L.lint_script(old, t)))
        self.assertEqual(L.build_script(dict(t, gender="W"))["beats"][-1]["label"], "Eve")

    def test_caption_names_only_the_kept_features(self):
        t = seed_topic("RSG0001")
        wd = L.p("work", "RSG0001")
        os.makedirs(wd, exist_ok=True)
        s = L.build_script(t)
        json.dump(s, open(os.path.join(wd, "script.json"), "w"))
        json.dump([2.0] + [3.0] * 6 + [3.2, 2.8], open(os.path.join(wd, "durations.json"), "w"))
        L.save_topic(t)
        try:
            line = L.caption(t).split("\n")[1]
            labels = [f["label"].lower() for f in t["features"]]
            self.assertNotIn(labels[5], line)
            self.assertIn(labels[0].split()[0], line.lower())
            self.assertIn("Scan yours in Axend. Comment who I should break down next.", line)
        finally:
            shutil.rmtree(wd)


if __name__ == "__main__":
    unittest.main()
