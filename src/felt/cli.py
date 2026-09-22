"""The ``felt`` command: the same service as ``felt.serve()``, from a terminal."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from felt.settings import DEFAULT_HOST, DEFAULT_PORT, PACKAGE_DIR, Settings
from felt.tailscale import TailscaleError


def _frontend_dir() -> Path:
    """The frontend sources, present in a clone of the repository only."""
    return PACKAGE_DIR.parents[1] / "frontend"


def build_frontend() -> None:
    """Run ``npm run build`` in a clone, so the package serves a current page.

    Raises:
        SystemExit: npm or the frontend sources are missing, or the build fails.
    """
    frontend_dir = _frontend_dir()
    if not (frontend_dir / "package.json").is_file():
        raise SystemExit(
            "--build needs a clone of the repository with its frontend folder; "
            "an installed package already carries the built page."
        )
    # On Windows the bare "npm" on PATH is a shell script that CreateProcess
    # cannot execute; npm.cmd is the real entry point.
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm is None:
        raise SystemExit("--build: npm not found on PATH.")
    print("Building frontend...", flush=True)
    result = subprocess.run([npm, "run", "build"], cwd=str(frontend_dir))
    if result.returncode != 0:
        raise SystemExit("--build: frontend build failed (see output above).")
    print("Frontend build complete.\n", flush=True)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="felt", description="Run the FELT perception feedback service")
    p.add_argument("--host", default=None, help=f"interface to bind (default {DEFAULT_HOST})")
    p.add_argument("--port", type=int, default=None, help=f"TCP port (default {DEFAULT_PORT})")
    p.add_argument(
        "--tailscale", nargs="?", const=True, default=False, choices=[True, "auto"], metavar="auto",
        help="bind this PC's Tailscale address, so tablets on the tailnet reach the page; "
             "--tailscale auto binds every interface instead when Tailscale is missing",
    )
    p.add_argument("--log-dir", default=None, help="where feedback logs are written (default ./logs)")
    p.add_argument("--images-dir", default=None, help="where uploaded images live (default ./uploads)")
    p.add_argument(
        "--console-url", default=None,
        help="calibration console to link, for example http://127.0.0.1:8765; "
             "overrides CONSOLE_URL; without either, FELT runs unlinked",
    )
    p.add_argument("--root-path", default=None, help="prefix a reverse proxy strips, for example /felt")
    p.add_argument("--log-level", default="info", help="uvicorn log level (default info)")
    p.add_argument("--build", action="store_true", help="run `npm run build` first (needs a clone)")
    p.add_argument("--reload", action="store_true", help="restart on source changes (development)")
    p.add_argument("--version", action="store_true", help="print the version and exit")
    return p


def main(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    if args.version:
        from felt import __version__
        print(__version__)
        return
    if args.build:
        build_frontend()

    from felt.server import FeltServer, settings_for

    try:
        settings = settings_for(
            host=args.host, port=args.port, tailscale=args.tailscale, log_dir=args.log_dir,
            images_dir=args.images_dir, console_url=args.console_url, root_path=args.root_path,
        )
    except TailscaleError as error:
        raise SystemExit(f"felt: {error}") from error

    print(f"\n  FELT serving on  {settings.url}")
    print(f"  Logs are written to  {settings.log_dir.resolve()}")
    print(f"  Images live in  {settings.images_dir.resolve()}")
    print(f"  Console link  {settings.console_url or 'none (unlinked)'}")
    if not settings.frontend_built:
        print("  The marking page is missing: run with --build in a clone, or install a release", file=sys.stderr)
    print(flush=True)

    if args.reload:
        # The reloader runs the app in a child process, which reads the
        # settings from the environment.
        import uvicorn

        os.environ.update({
            "FELT_HOST": settings.host, "FELT_PORT": str(settings.port),
            "LOGS_DIR": str(settings.log_dir), "IMAGES_DIR": str(settings.images_dir),
            "CONSOLE_URL": settings.console_url, "ROOT_PATH": settings.root_path,
        })
        uvicorn.run(
            "felt.app:factory", factory=True, reload=True, host=settings.host, port=settings.port,
            log_level=args.log_level, proxy_headers=True, forwarded_allow_ips="*",
        )
        return

    FeltServer(settings, log_level=args.log_level).serve_forever()


if __name__ == "__main__":
    main()
