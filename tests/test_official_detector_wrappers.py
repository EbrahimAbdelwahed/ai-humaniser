from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_official_detector_wrappers_expose_help():
    wrappers = [
        ROOT / "scripts" / "official" / "binoculars_official_cli.py",
        ROOT / "scripts" / "official" / "ghostbuster_official_cli.py",
        ROOT / "scripts" / "official" / "fast_detectgpt_official_cli.py",
        ROOT / "scripts" / "official" / "runpod_official_cli.py",
    ]

    for wrapper in wrappers:
        completed = subprocess.run([sys.executable, str(wrapper), "--help"], text=True, capture_output=True, check=False)

        assert completed.returncode == 0
        assert "stdin-to-JSON" in completed.stdout
