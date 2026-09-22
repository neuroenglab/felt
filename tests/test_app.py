"""The application and the Python API, on a throwaway folder and a spare port."""

import json
import socket
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import felt
from felt.app import create_app
from felt.settings import Settings


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.settings = Settings(log_dir=self.tmp / "logs", images_dir=self.tmp / "uploads")
        self.client = TestClient(create_app(self.settings))

    def test_the_folders_are_created(self):
        self.assertTrue((self.tmp / "logs").is_dir())
        self.assertTrue((self.tmp / "uploads").is_dir())

    def test_no_marking_page_until_a_heartbeat(self):
        self.assertEqual(self.client.get("/api/clients").json(), {"connected": False, "count": 0})
        self.assertEqual(self.client.put("/api/clients/tab1").status_code, 204)
        self.assertEqual(self.client.get("/api/clients").json(), {"connected": True, "count": 1})
        self.assertEqual(self.client.delete("/api/clients/tab1").status_code, 204)
        self.assertFalse(self.client.get("/api/clients").json()["connected"])

    def test_an_unlinked_service_reports_no_link(self):
        self.assertEqual(self.client.get("/api/trial").json(), {"linked": False})

    def test_a_painting_is_written_to_the_log_folder(self):
        answer = self.client.post("/api/save-feedback", json={
            "log_id": "S01", "filename": "left.svg", "feedbackLocation": {"chosenPoints": {}},
        })
        self.assertEqual(answer.status_code, 200, answer.text)
        written = list((self.tmp / "logs").glob("S01_left_svg_*.json"))
        self.assertEqual(len(written), 1)
        payload = json.loads(written[0].read_text())
        self.assertNotIn("trial", payload)
        self.assertIn("exported_at", payload["feedbackLocation"])

    def test_the_hand_images_ship_with_the_package(self):
        answer = self.client.get("/hands/hand-left-Left_Hand.svg")
        self.assertEqual(answer.status_code, 200)
        self.assertIn(b"<svg", answer.content)

    def test_the_page_is_served_and_never_cached(self):
        if not self.settings.frontend_built:
            self.skipTest("the marking page is not built")
        for path in ("/", "/process"):
            answer = self.client.get(path)
            self.assertEqual(answer.status_code, 200)
            self.assertEqual(answer.headers.get("cache-control"), "no-cache")
            self.assertIn(b"<div id=\"root\">", answer.content)

    def test_a_missing_page_says_so(self):
        client = TestClient(create_app(self.settings.with_(static_dir=self.tmp / "nowhere")))
        self.assertEqual(client.get("/").json()["detail"][:19], "Frontend not built:")


class ServerTests(unittest.TestCase):
    def test_start_serves_until_stop(self):
        tmp = Path(tempfile.mkdtemp())
        port = free_port()
        server = felt.start(port=port, log_dir=tmp / "logs", images_dir=tmp / "uploads", log_level="warning")
        try:
            self.assertTrue(server.running)
            self.assertEqual(server.url, f"http://127.0.0.1:{port}")
            remote = felt.FeltClient(server.url)
            self.assertTrue(remote.reachable())
            self.assertFalse(remote.marking_page_open())
            server.app.state.clients.touch("tab1")
            self.assertTrue(remote.marking_page_open())
            self.assertTrue(server.wait_for_marking_page(timeout_s=1))
        finally:
            server.stop()
        self.assertFalse(server.running)
        self.assertFalse(remote.reachable())

    def test_a_taken_port_fails_loudly(self):
        tmp = Path(tempfile.mkdtemp())
        port = free_port()
        first = felt.start(port=port, log_dir=tmp / "a", images_dir=tmp / "a", log_level="critical")
        try:
            with self.assertRaises(felt.FeltError):
                felt.start(port=port, log_dir=tmp / "b", images_dir=tmp / "b", log_level="critical")
        finally:
            first.stop()

    def test_the_context_manager_stops_the_server(self):
        tmp = Path(tempfile.mkdtemp())
        settings = Settings(port=free_port(), log_dir=tmp / "logs", images_dir=tmp / "uploads")
        with felt.FeltServer(settings, log_level="warning") as server:
            self.assertTrue(server.running)
        self.assertFalse(server.running)


class TailscaleTests(unittest.TestCase):
    def test_a_missing_executable_names_the_way_out(self):
        from felt import tailscale

        original = tailscale.find_executable
        tailscale.find_executable = lambda: None
        try:
            with self.assertRaises(felt.TailscaleError) as caught:
                felt.settings_for(tailscale=True)
        finally:
            tailscale.find_executable = original
        message = str(caught.exception)
        self.assertIn("tailscale.com/download", message)
        self.assertIn("host='0.0.0.0'", message)
        self.assertIn("--host 0.0.0.0", message)

    def test_auto_binds_every_interface_without_tailscale(self):
        from felt import tailscale

        original = tailscale.find_executable
        tailscale.find_executable = lambda: None
        try:
            settings = felt.settings_for(tailscale="auto", port=5002)
        finally:
            tailscale.find_executable = original
        self.assertEqual(settings.url, "http://0.0.0.0:5002")

    def test_without_the_flag_tailscale_is_never_consulted(self):
        settings = felt.settings_for(host="0.0.0.0", port=5001)
        self.assertEqual(settings.url, "http://0.0.0.0:5001")
