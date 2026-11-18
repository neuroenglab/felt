"""Ask a running FELT service about itself, from another process.

A pipeline that did not start FELT itself uses this to wait for the tablet:

    from felt import FeltClient

    tablet = FeltClient("http://100.64.0.12:5000")
    tablet.wait_for_marking_page(timeout_s=120)
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

TIMEOUT_S = 2.0
CLIENTS_PATH = "/api/clients"
TRIAL_PATH = "/api/trial"


class FeltClient:
    """The FELT service at ``url``."""

    def __init__(self, url: str, timeout_s: float = TIMEOUT_S) -> None:
        self.url = url.rstrip("/")
        self.timeout_s = timeout_s

    def reachable(self) -> bool:
        """True when the service answers."""
        try:
            self.clients()
        except OSError:
            return False
        return True

    def clients(self) -> dict[str, Any]:
        """``connected`` and ``count`` of the open marking pages.

        Raises:
            OSError: The service does not answer.
        """
        return self._get(CLIENTS_PATH)

    def marking_page_open(self) -> bool:
        """True when a marking page is open. An unreachable service counts as closed."""
        try:
            return bool(self.clients().get("connected"))
        except OSError:
            return False

    def trial(self, wait: float = 0) -> dict[str, Any]:
        """What the page shows about the console link, the answer of ``GET /api/trial``."""
        path = TRIAL_PATH if wait <= 0 else f"{TRIAL_PATH}?wait={wait}"
        return self._get(path, timeout_s=self.timeout_s + wait)

    def wait_for_marking_page(self, timeout_s: float | None = None, poll_s: float = 1.0) -> bool:
        """Wait until a marking page is open. False when ``timeout_s`` runs out."""
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        while not self.marking_page_open():
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(poll_s)
        return True

    def _get(self, path: str, timeout_s: float | None = None) -> dict[str, Any]:
        request = urllib.request.Request(self.url + path, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout_s or self.timeout_s) as response:
                payload = json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            raise OSError(f"GET {path}: HTTP {error.code}") from error
        except ValueError as error:
            raise OSError(f"GET {path}: {error}") from error
        return payload if isinstance(payload, dict) else {"value": payload}
