"""What a FELT service needs to know before it starts."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent
# The built marking page, shipped inside the package.
STATIC_DIR = PACKAGE_DIR / "static"
# The two hand images of the linked page.
HANDS_DIR = PACKAGE_DIR / "hands"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


@dataclass(frozen=True)
class Settings:
    """The configuration of one FELT service.

    Args:
        host: The interface to bind. ``127.0.0.1`` serves this PC only,
            ``0.0.0.0`` every network of the host, a Tailscale address the tailnet.
        port: The TCP port.
        log_dir: Where the feedback logs are written. Created when missing.
        images_dir: Where uploaded body-part SVGs live. Created when missing.
        console_url: The calibration console FELT links to, for example
            ``http://127.0.0.1:8765``. Empty means unlinked.
        root_path: The prefix a reverse proxy strips, for example ``/felt``.
            Empty when FELT is served at the root.
        static_dir: The folder of the built marking page. The package's own
            copy by default.
        hands_dir: The folder of the hand images. The package's own copy by
            default.
    """

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    log_dir: Path = Path("logs")
    images_dir: Path = Path("uploads")
    console_url: str = ""
    root_path: str = ""
    static_dir: Path = STATIC_DIR
    hands_dir: Path = HANDS_DIR

    def __post_init__(self) -> None:
        object.__setattr__(self, "log_dir", Path(self.log_dir))
        object.__setattr__(self, "images_dir", Path(self.images_dir))
        object.__setattr__(self, "static_dir", Path(self.static_dir))
        object.__setattr__(self, "hands_dir", Path(self.hands_dir))
        object.__setattr__(self, "console_url", (self.console_url or "").strip().rstrip("/"))
        object.__setattr__(self, "root_path", (self.root_path or "").strip().rstrip("/"))
        object.__setattr__(self, "port", int(self.port))

    @property
    def url(self) -> str:
        """The address of the service on this host."""
        return f"http://{self.host}:{self.port}"

    @property
    def linked(self) -> bool:
        """True when a console address is set."""
        return bool(self.console_url)

    @property
    def frontend_built(self) -> bool:
        """True when the marking page is available under ``static_dir``."""
        return (self.static_dir / "index.html").is_file()

    def with_(self, **changes: Any) -> "Settings":
        """A copy with some fields replaced."""
        return replace(self, **changes)

    @classmethod
    def from_env(cls, **overrides: Any) -> "Settings":
        """Settings from the environment, then the given overrides.

        The variables are ``FELT_HOST``, ``FELT_PORT``, ``LOGS_DIR``,
        ``IMAGES_DIR``, ``CONSOLE_URL`` and ``ROOT_PATH``. The Docker image
        sets them; a Python caller passes the fields instead.
        """
        values: dict[str, Any] = {}
        env = os.environ
        if env.get("FELT_HOST"):
            values["host"] = env["FELT_HOST"]
        if env.get("FELT_PORT"):
            values["port"] = int(env["FELT_PORT"])
        if env.get("LOGS_DIR"):
            values["log_dir"] = env["LOGS_DIR"]
        if env.get("IMAGES_DIR"):
            values["images_dir"] = env["IMAGES_DIR"]
        if env.get("CONSOLE_URL"):
            values["console_url"] = env["CONSOLE_URL"]
        if env.get("ROOT_PATH"):
            values["root_path"] = env["ROOT_PATH"]
        values.update({key: value for key, value in overrides.items() if value is not None})
        return cls(**values)
