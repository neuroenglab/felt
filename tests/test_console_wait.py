import threading
import unittest
from src.console import ConsoleLink


class ConsoleWaitTests(unittest.TestCase):
    def test_idle_waits_for_a_revision_and_wakes_for_the_next_sequence(self):
        link = ConsoleLink("http://console.test")
        link._status = {"state": "IDLE", "revision": 42}
        link._read_at = 0
        calls = []
        def request(method, path, **kwargs):
            calls.append((method, path, kwargs))
            return {"state": "WAIT_PLAY", "revision": 43, "sequence_id": "seq_new"}
        link._request = request
        trial = link.trial(wait=25)
        self.assertEqual(calls, [("GET", "/calibration/sequence/status?after=42&wait=25", {"timeout_s": 27.0})])
        self.assertEqual(trial["sequence_id"], "seq_new")
        self.assertFalse(trial["manual"])
        self.assertFalse(trial["can_draw"])
        link.trial(wait=25)
        self.assertEqual(len(calls), 1)

    def test_concurrent_tablets_share_one_console_wait(self):
        link = ConsoleLink("http://console.test")
        link._status = {"state": "IDLE", "revision": 2}
        gate, entered = threading.Event(), threading.Event()
        calls = []
        def request(*args, **kwargs):
            calls.append(args)
            entered.set()
            gate.wait(2)
            return {"state": "IDLE", "revision": 2}
        link._request = request
        threads = [threading.Thread(target=lambda: link.trial(wait=25)) for _ in range(3)]
        for thread in threads: thread.start()
        self.assertTrue(entered.wait(1))
        gate.set()
        for thread in threads: thread.join(2)
        self.assertEqual(len(calls), 1)

    def test_unlinked_felt_does_not_request_console_status(self):
        link = ConsoleLink()
        link._request = lambda *a, **kw: self.fail("unexpected console request")
        self.assertEqual(link.trial(wait=25), {"linked": False})
