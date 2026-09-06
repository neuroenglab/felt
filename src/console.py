"""Link to the calibration console.

The FELT service reads the sequence status of the console and sends the
painting of the named trial back to it. The tablet page talks to the FELT
service only, so one address configures the whole link (decision 017 of the
console repository).

The link uses ``urllib`` of the standard library, a short timeout, and a cache
of one second, so a room full of tablets polling once per second cannot flood
the console with requests.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

# Seconds a request may take before the console counts as unreachable.
TIMEOUT_S = 2.0
# Seconds a read status is served from the cache.
CACHE_S = 1.0

STATUS_PATH = "/calibration/sequence/status"
FELT_PATH = "/calibration/sequence/felt"

NOT_REACHABLE = "Console not reachable"


class ConsoleLink:
    """The console at ``base_url``. An empty address means not linked."""

    def __init__(self, base_url: str = "") -> None:
        self.base_url = (base_url or "").strip().rstrip("/")
        self._status: dict[str, Any] | None = None
        self._read_at: float | None = None

    @property
    def linked(self) -> bool:
        return bool(self.base_url)

    def status(self) -> dict[str, Any] | None:
        """The sequence status, or None when the console does not answer.

        A failed read is cached like a good one, so an unreachable console is
        asked once per second and not once per page poll.
        """
        if not self.linked:
            return None
        now = time.monotonic()
        if self._read_at is not None and now - self._read_at < CACHE_S:
            return self._status
        status: dict[str, Any] | None
        try:
            status = self._request("GET", STATUS_PATH)
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            status = None
        self._status = status
        self._read_at = now
        return status

    def trial(self) -> dict[str, Any]:
        """The answer of ``GET /api/trial`` of the FELT service."""
        if not self.linked:
            return {"linked": False}
        status = self.status()
        if status is None:
            return {
                "linked": True,
                "reachable": False,
                "state": None,
                "sentence": None,
                "subject_code": None,
                "sequence_id": None,
                "trial_id": None,
                "pass_index": None,
                "trial_saved": False,
                "felt_answered": False,
                "hand": None,
                "manual": False,
                "can_draw": False,
            }
        state = status.get("state")
        trial_saved = bool(status.get("trial_saved"))
        # No sequence runs: the page draws and exports on its own, as an
        # unlinked FELT does.
        manual = state == "IDLE"
        return {
            "linked": True,
            "reachable": True,
            "state": state,
            "sentence": status.get("sentence"),
            "subject_code": status.get("subject_code"),
            "sequence_id": status.get("sequence_id"),
            "trial_id": status.get("trial_id"),
            "pass_index": status.get("pass_index"),
            "trial_saved": trial_saved,
            "felt_answered": bool(status.get("felt_answered")),
            "hand": status.get("hand"),
            "manual": manual,
            # While a sequence runs the subject draws in SCORING only, and
            # only before Save.
            "can_draw": manual or (state == "SCORING" and not trial_saved),
        }

    def send_felt(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Post the FELT answer to the console and report what it answered.

        The answer of the console is the sequence status; its ``felt_feedback``
        carries the accepted regions and a problem line. A refusal (409) comes
        back as ``accepted`` false with the reason of the console.
        """
        if not self.linked:
            return self._refusal("Console not linked")
        try:
            answer = self._request("POST", FELT_PATH, payload)
        except urllib.error.HTTPError as error:
            return self._refusal(_detail(error))
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            return self._refusal(NOT_REACHABLE)
        # The post answers the fresh status, so the next poll needs no request.
        if isinstance(answer, dict):
            self._status = answer
            self._read_at = time.monotonic()
        feedback = (answer or {}).get("felt_feedback") or {}
        return {
            "accepted": True,
            "regions": list(feedback.get("regions") or []),
            "problem": feedback.get("problem"),
            "reason": None,
        }

    @staticmethod
    def _refusal(reason: str) -> dict[str, Any]:
        return {"accepted": False, "regions": [], "problem": None, "reason": reason}

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + path, data=data, headers=headers, method=method
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            text = response.read().decode("utf-8")
        answer = json.loads(text)
        if not isinstance(answer, dict):
            raise ValueError("The console answered no object")
        return answer


def _detail(error: urllib.error.HTTPError) -> str:
    """The reason of a refusal: the ``detail`` field, or the status line."""
    try:
        body = json.loads(error.read().decode("utf-8"))
    except (ValueError, OSError):
        body = None
    if isinstance(body, dict) and isinstance(body.get("detail"), str):
        return body["detail"]
    return f"Console refused the painting ({error.code})"
