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
        for name in ("Barry Keoghan", "Timothée Chalamet"):
            os.makedirs(os.path.dirname(L.p("stills", L.cut_rel(name))), exist_ok=True)
            open(L.p("stills", L.cut_rel(name)), "wb").write(PNG)

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
            self.assertEqual(kinds[:2], ["hook", "narrator"])
            self.assertEqual(kinds[-2:], ["walkout", "cta"])
            self.assertEqual(s["lane"], "B")
            self.assertEqual(s["beats"][1]["vo"], "So let's break down what his face actually has.")
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


if __name__ == "__main__":
    unittest.main()
