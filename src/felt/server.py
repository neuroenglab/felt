"""Start and stop a FELT service from Python.

    import felt

    server = felt.start(port=5000, tailscale=True, console_url="http://127.0.0.1:8765")
    server.wait_for_marking_page()
    ...
    server.stop()

``felt.serve(...)`` does the same in the foreground until Ctrl+C, which is
what the ``felt`` command runs.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn

from felt.app import create_app
from felt.settings import Settings
from felt.tailscale import tailscale_ipv4

logger = logging.getLogger("felt")

START_TIMEOUT_S = 15.0
STOP_TIMEOUT_S = 10.0


class FeltError(RuntimeError):
    """The service could not start, or stopped on its own."""


def resolve_host(host: str | None, tailscale: bool) -> str:
    """The interface to bind: this PC's Tailscale address, else ``host``.

    Raises:
        TailscaleError: ``tailscale`` is True and Tailscale is missing or not running.
    """
    if tailscale:
        return tailscale_ipv4()
    return host or Settings.host


def settings_for(
    *,
    host: str | None = None,
    port: int | None = None,
    tailscale: bool = False,
    log_dir: str | Path | None = None,
    images_dir: str | Path | None = None,
    console_url: str | None = None,
    root_path: str | None = None,
) -> Settings:
    """The settings of a service, from keyword arguments over the environment.

    Raises:
        TailscaleError: ``tailscale`` is True and Tailscale is missing or not running.
    """
    return Settings.from_env(
        host=resolve_host(host, tailscale) if tailscale else host,
        port=port,
        log_dir=log_dir,
        images_dir=images_dir,
        console_url=console_url,
        root_path=root_path,
    )


class FeltServer:
    """One FELT service, run on a background thread of this process.

    Args:
        settings: What to serve, where, and which console to link.
        log_level: The uvicorn log level.
    """

    def __init__(self, settings: Settings | None = None, *, log_level: str = "info") -> None:
        self.settings = settings or Settings()
        self.app = create_app(self.settings)
        self._config = uvicorn.Config(
            self.app,
            host=self.settings.host,
            port=self.settings.port,
            log_level=log_level,
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
        self._server = uvicorn.Server(self._config)
        self._thread: threading.Thread | None = None
        self._failure: BaseException | None = None

    # --- state ---

    @property
    def url(self) -> str:
        """The address of the service, for a browser on the same network."""
        return self.settings.url

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and self._server.started

    def marking_page_open(self) -> bool:
        """True when at least one marking page is open on a tablet or browser."""
        return bool(self.app.state.clients.status()["connected"])

    def marking_clients(self) -> dict[str, Any]:
        """``connected`` and ``count`` of the open marking pages."""
        return self.app.state.clients.status()

    def wait_for_marking_page(self, timeout_s: float | None = None, poll_s: float = 1.0) -> bool:
        """Wait until a marking page is open. False when ``timeout_s`` runs out."""
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        while not self.marking_page_open():
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(poll_s)
        return True

    # --- lifecycle ---

    def _run(self) -> None:
        """Run uvicorn on this thread and keep its failure, instead of letting the
        thread die with an unhandled SystemExit."""
        try:
            self._server.run()
        except BaseException as error:  # noqa: BLE001 - SystemExit included
            self._failure = error

    def start(self, timeout_s: float = START_TIMEOUT_S) -> "FeltServer":
        """Start serving on a background thread and return once the port is open.

        Raises:
            FeltError: The service did not come up, for example because the
                port is taken or the interface does not exist.
        """
        if self.running:
            return self
        self._failure = None
        self._thread = threading.Thread(target=self._run, name="felt", daemon=True)
        self._thread.start()
        deadline = time.monotonic() + timeout_s
        while not self._server.started:
            if not self._thread.is_alive():
                detail = f" ({self._failure!r})" if self._failure else ""
                raise FeltError(
                    f"FELT did not start on {self.url}: is the port free and the interface up?"
                    f"{detail} See the uvicorn error above."
                )
            if time.monotonic() >= deadline:
                self.stop()
                raise FeltError(f"FELT did not start on {self.url} within {timeout_s:.0f} s")
            time.sleep(0.05)
        logger.info("FELT serving on %s", self.url)
        logger.info(
            "logs in %s, images in %s",
            self.settings.log_dir.resolve(), self.settings.images_dir.resolve(),
        )
        logger.info("console link %s", self.settings.console_url or "none (unlinked)")
        return self

    def stop(self, timeout_s: float = STOP_TIMEOUT_S) -> None:
        """Stop serving. Safe to call twice, or on a server that never started."""
        self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout_s)
            self._thread = None

    def serve_forever(self) -> None:
        """Serve on this thread until Ctrl+C or ``stop()`` from another thread."""
        self._server.run()

    def __enter__(self) -> "FeltServer":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def __repr__(self) -> str:
        state = "running" if self.running else "stopped"
        return f"FeltServer({self.url}, {state})"


def start(
    *,
    host: str | None = None,
    port: int | None = None,
    tailscale: bool = False,
    log_dir: str | Path | None = None,
    images_dir: str | Path | None = None,
    console_url: str | None = None,
    root_path: str | None = None,
    log_level: str = "info",
) -> FeltServer:
    """Start a FELT service in the background and return it once it answers.

    Args:
        host: The interface to bind, ``127.0.0.1`` by default. Ignored when
            ``tailscale`` is True.
        port: The TCP port, 5000 by default.
        tailscale: Bind this PC's Tailscale address, so tablets on the tailnet
            reach the page and nothing else does.
        log_dir: Where the feedback logs go, ``./logs`` by default.
        images_dir: Where uploaded images go, ``./uploads`` by default.
        console_url: The calibration console to link, or None for an unlinked FELT.
        root_path: The prefix a reverse proxy strips, or None.
        log_level: The uvicorn log level.

    Raises:
        TailscaleError: ``tailscale`` is True and Tailscale is missing or not running.
        FeltError: The service did not come up.
    """
    settings = settings_for(
        host=host, port=port, tailscale=tailscale, log_dir=log_dir,
        images_dir=images_dir, console_url=console_url, root_path=root_path,
    )
    return FeltServer(settings, log_level=log_level).start()


def serve(
    *,
    host: str | None = None,
    port: int | None = None,
    tailscale: bool = False,
    log_dir: str | Path | None = None,
    images_dir: str | Path | None = None,
    console_url: str | None = None,
    root_path: str | None = None,
    log_level: str = "info",
) -> None:
    """Serve FELT on this thread until Ctrl+C. Same arguments as ``start``."""
    settings = settings_for(
        host=host, port=port, tailscale=tailscale, log_dir=log_dir,
        images_dir=images_dir, console_url=console_url, root_path=root_path,
    )
    FeltServer(settings, log_level=log_level).serve_forever()
