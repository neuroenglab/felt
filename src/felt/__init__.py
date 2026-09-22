"""FELT, the perception feedback tool: a marking page for tablets, served from Python.

    import felt

    server = felt.start(tailscale=True, console_url="http://127.0.0.1:8765")
    server.wait_for_marking_page()
    ...
    server.stop()
"""

from importlib.metadata import PackageNotFoundError, version

from felt.client import FeltClient
from felt.server import FeltError, FeltServer, resolve_host, serve, settings_for, start
from felt.settings import Settings
from felt.tailscale import TailscaleError, tailscale_ipv4

try:
    __version__ = version("felt")
except PackageNotFoundError:  # a checkout that is not installed
    __version__ = "0.0.0"

__all__ = [
    "FeltClient",
    "FeltError",
    "FeltServer",
    "Settings",
    "TailscaleError",
    "__version__",
    "resolve_host",
    "serve",
    "settings_for",
    "start",
    "tailscale_ipv4",
]
