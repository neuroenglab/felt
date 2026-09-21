import unittest
from src.console import ConsoleLink


def link_with(status):
    link = ConsoleLink("http://console.test")
    link._request = lambda *a, **kw: status
    return link


class ConsoleTargetTests(unittest.TestCase):
    def test_target_state_lets_the_subject_paint_the_target(self):
        trial = link_with({
            "state": "TARGET", "purpose": "target", "trial_id": "target-reach",
            "subject_code": "S01", "trial_saved": False,
        }).trial()
        self.assertTrue(trial["can_draw"])
        self.assertFalse(trial["manual"])
        self.assertEqual(trial["purpose"], "target")
        self.assertEqual(trial["trial_id"], "target-reach")

    def test_scoring_state_names_the_sensation_purpose(self):
        trial = link_with({
            "state": "SCORING", "purpose": "sensation", "trial_id": "tr_0001",
            "trial_saved": False,
        }).trial()
        self.assertTrue(trial["can_draw"])
        self.assertEqual(trial["purpose"], "sensation")

    def test_wait_play_locks_the_drawing_without_a_purpose(self):
        trial = link_with({"state": "WAIT_PLAY", "purpose": None}).trial()
        self.assertFalse(trial["can_draw"])
        self.assertFalse(trial["manual"])
        self.assertIsNone(trial["purpose"])

    def test_unreachable_console_answers_no_purpose(self):
        link = ConsoleLink("http://console.test")
        def request(*a, **kw):
            raise OSError("down")
        link._request = request
        trial = link.trial()
        self.assertFalse(trial["reachable"])
        self.assertFalse(trial["can_draw"])
        self.assertIsNone(trial["purpose"])
