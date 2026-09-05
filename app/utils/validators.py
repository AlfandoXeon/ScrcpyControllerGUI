"""
Input validators for Xeon - Scrcpy Controller.
"""

import re
import shlex


def is_valid_ip(address: str) -> bool:
    """
    Validate an IPv4 address.

    Args:
        address: IP address string to validate.

    Returns:
        True if valid IPv4 address.
    """
    pattern = re.compile(
        r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"
    )
    match = pattern.match(address.strip())
    if not match:
        return False
    return all(0 <= int(g) <= 255 for g in match.groups())


def is_valid_port(port: str | int) -> bool:
    """
    Validate a TCP port number (1–65535).

    Args:
        port: Port value as string or int.

    Returns:
        True if valid port.
    """
    try:
        p = int(port)
        return 1 <= p <= 65535
    except (ValueError, TypeError):
        return False


def parse_custom_args(raw: str) -> list[str]:
    """
    Parse a custom argument string into a list of tokens using shell-like rules.

    Args:
        raw: Raw custom argument string, e.g. "--no-control --show-touches".

    Returns:
        List of argument tokens.

    Raises:
        ValueError: If the string contains unclosed quotes or invalid syntax.
    """
    try:
        return shlex.split(raw, posix=True)
    except ValueError as exc:
        raise ValueError(f"Invalid custom arguments: {exc}") from exc


def validate_custom_args(raw: str) -> tuple[bool, str]:
    """
    Validate a raw custom argument string.

    Args:
        raw: Raw custom argument string.

    Returns:
        (is_valid, error_message) — error_message is empty string on success.
    """
    if not raw.strip():
        return True, ""
    try:
        tokens = parse_custom_args(raw)
    except ValueError as exc:
        return False, str(exc)

    # Disallow dangerous constructs
    forbidden = ["&&", "||", ";", "|", ">", "<", "`", "$("]
    for token in tokens:
        for f in forbidden:
            if f in token:
                return False, f"Forbidden character sequence '{f}' in custom arguments."
    return True, ""


def is_valid_window_title(title: str) -> bool:
    """
    Validate a scrcpy window title (non-empty, reasonable length).

    Args:
        title: Window title string.

    Returns:
        True if acceptable.
    """
    return 0 < len(title.strip()) <= 256
