"""Startup safety checks, per plan.md §7: "framework should warn loudly if it detects
[config/secure/] is tracked"."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("maya.app")

_WARNING_MESSAGE = """
SECURITY WARNING: {path} is tracked by git!
Secrets/credentials stored under this path may already be committed to history.
Run `git rm --cached -r {path}` and rotate any credentials that were exposed.
""".strip()


def check_secure_config_not_tracked(secure_dir: Path = Path("framework-data/config/secure")) -> bool:
    """Returns True if `secure_dir` is safe (not tracked by git, or git is unavailable/
    not a repo here). Returns False if any file under it is currently tracked.

    Deliberately checks `git ls-files` (currently-tracked files) rather than
    `git check-ignore` (would-future-adds-be-ignored) — the real risk is a file
    committed before .gitignore excluded it, which check-ignore can't detect."""
    try:
        result = subprocess.run(
            ["git", "ls-files", str(secure_dir)],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        logger.info("skipping git-tracking check for %s: git is not installed", secure_dir)
        return True

    if result.returncode != 0:
        logger.info("skipping git-tracking check for %s: not a git repository", secure_dir)
        return True

    if result.stdout.strip():
        logger.warning(_WARNING_MESSAGE.format(path=secure_dir))
        return False

    return True
