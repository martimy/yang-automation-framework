"""
Puts framework/ on sys.path so we can import its modules the same way
deploy.py does (bare names like `intent.interface`, not
`framework.intent.interface`).

framework/ is not an installable package today -- its modules assume
they're run with framework/ as the working directory / on sys.path.
Rather than restructure that teaching code, the GUI backend adapts to it.
Import this module (for its side effect) before importing anything
from the framework.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_DIR = REPO_ROOT / "framework"
DEVICES_YML = FRAMEWORK_DIR / "devices.yml"

if not FRAMEWORK_DIR.is_dir():
    raise RuntimeError(
        f"Expected framework/ at {FRAMEWORK_DIR}, but it doesn't exist. "
        "gui/backend assumes it lives at <repo_root>/gui/backend."
    )

if str(FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_DIR))
