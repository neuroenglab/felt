import unittest
from felt.clients import MarkingClients


class PresenceTests(unittest.TestCase):
    def test_probing_does_not_register_a_client_and_expiry_clears_disconnected_pages(self):
        now = [0.0]
        clients = MarkingClients(clock=lambda: now[0])
        self.assertEqual(clients.status(), {"count": 0, "connected": False})
        clients.touch("tablet")
        now[0] = 4
        clients.touch("laptop")
        now[0] = 8
        self.assertEqual(clients.status(), {"count": 1, "connected": True})
        clients.remove("laptop")
        self.assertFalse(clients.status()["connected"])

