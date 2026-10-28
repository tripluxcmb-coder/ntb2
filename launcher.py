"""Set up and run the dashboard using Python alone: python launcher.py."""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def prepare_environment(root: Path = ROOT) -> Path:
    environment = root / ".venv"
    executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        print("Preparing the application's Python environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    requirements = root / "requirements.txt"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = environment / "copilot_requirements.sha256"
    previous = marker.read_text(encoding="utf-8").strip() if marker.exists() else ""
    probe = subprocess.run(
        [str(executable), "-c", "import flask, waitress, requests, dotenv"],
        cwd=root, capture_output=True, text=True,
    )
    if previous != digest or probe.returncode != 0:
        print("Installing the required Python packages...", flush=True)
        subprocess.run([str(executable), "-m", "pip", "install", "-r", str(requirements)],
                       cwd=root, check=True)
        marker.write_text(digest, encoding="utf-8")
    settings = root / ".env"
    if not settings.exists():
        shutil.copyfile(root / ".env.example", settings)
        print("Created .env. Add your OpenRouter key there to enable AI recommendations.", flush=True)
    return executable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Set up and start Relationship Intelligence using Python.")
    parser.add_argument("--setup", "--setup-only", action="store_true",
                        help="Prepare the environment and .env, then exit without starting the app.")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        print("Python 3.11 or later is required.", file=sys.stderr)
        return 1
    try:
        executable = prepare_environment()
        if args.setup:
            print("Setup complete. Add your OpenRouter key to .env, then run: python launcher.py")
            return 0
        return subprocess.call([str(executable), str(ROOT / "run.py")], cwd=ROOT)
    except KeyboardInterrupt:
        return 0
    except (OSError, subprocess.CalledProcessError) as error:
        print("Could not prepare or start the application. Check Python, package-install access, "
              "and the manual PowerShell instructions in README.md.", file=sys.stderr)
        return error.returncode if isinstance(error, subprocess.CalledProcessError) else 1


if __name__ == "__main__":
    raise SystemExit(main())
