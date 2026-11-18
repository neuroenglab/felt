"""This PC's Tailscale address, so tablets on the tailnet reach FELT.

The lookup shells out to the ``tailscale`` executable.
"""

from __future__ import annotations

import os
import shutil
import subprocess

COMMAND_TIMEOUT_S = 10.0

INSTALL_PATHS = (
    "/usr/bin/tailscale",
    "/usr/local/bin/tailscale",
    "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
)

WITHOUT_TAILSCALE = "Start FELT without --tailscale, or with --tailscale auto, to serve on this machine instead."


class TailscaleError(RuntimeError):
    """Tailscale is not installed, not running or not logged in."""


def _windows_path() -> str:
    program_files = os.environ.get("ProgramFiles", "")
    return os.path.join(program_files, "Tailscale", "tailscale.exe") if program_files else ""


def find_executable() -> str | None:
    """The tailscale executable from PATH, else a known install path, else None."""
    found = shutil.which("tailscale")
    if found:
        return found
    for candidate in (_windows_path(), *INSTALL_PATHS):
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def tailscale_ipv4() -> str:
    """This PC's Tailscale IPv4 address, the first line of ``tailscale ip -4``.

    Raises:
        TailscaleError: The executable is missing, the command fails, or
            Tailscale is not running or not logged in.
    """
    exe = find_executable()
    if exe is None:
        raise TailscaleError("Tailscale is not installed. " + WITHOUT_TAILSCALE)
    try:
        result = subprocess.run(
            [exe, "ip", "-4"], capture_output=True, text=True, timeout=COMMAND_TIMEOUT_S
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise TailscaleError(f"Could not run {exe} ip -4: {error}. " + WITHOUT_TAILSCALE) from error
    lines = (result.stdout or "").strip().splitlines()
    if result.returncode != 0 or not lines:
        detail = (result.stderr or result.stdout or "").strip()
        raise TailscaleError(
            f"Tailscale is not running or not logged in ({detail or 'no output'}). " + WITHOUT_TAILSCALE
        )
    return lines[0].strip()
