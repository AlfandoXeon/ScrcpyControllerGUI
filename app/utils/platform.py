"""
Platform utilities for Windows-specific operations.
"""

import os
import subprocess
import sys
from pathlib import Path


def is_windows() -> bool:
    """Return True if running on Windows."""
    return sys.platform == "win32"


def open_folder_in_explorer(path: Path) -> None:
    """
    Open a directory in Windows Explorer.

    Args:
        path: Directory to open.
    """
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["explorer", str(path)])


def open_url_in_browser(url: str) -> None:
    """
    Open a URL in the default system browser.

    Args:
        url: URL to open.
    """
    import webbrowser
    webbrowser.open(url)


def get_env_path() -> list[str]:
    """
    Return the current PATH environment variable as a list of entries.

    Returns:
        List of directory strings from PATH.
    """
    raw = os.environ.get("PATH", "")
    return [p for p in raw.split(os.pathsep) if p]
