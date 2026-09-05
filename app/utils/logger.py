"""
Logging setup for Xeon - Scrcpy Controller.
"""

import sys
import logging
import logging.handlers
from pathlib import Path


from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal

_qt_log_handler: Optional["QtLogHandler"] = None


class QtLogHandler(QObject, logging.Handler):
    """
    Thread-safe logging handler emitting PyQt signal for GUI log viewer.
    """
    log_emitted = pyqtSignal(str, int)  # (formatted_message, levelno)

    def __init__(self) -> None:
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.log_emitted.emit(msg, record.levelno)
        except Exception:
            self.handleError(record)


def get_qt_log_handler() -> Optional[QtLogHandler]:
    """Return the global QtLogHandler instance if initialized."""
    global _qt_log_handler
    if _qt_log_handler is None:
        _qt_log_handler = QtLogHandler()
        _qt_log_handler.setLevel(logging.DEBUG)
    return _qt_log_handler


def setup_logging(log_file: Path, level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure root logger with:
      - application.log: DEBUG, INFO, WARNING, ERROR, CRITICAL
      - error.log: dedicated log for ERROR and CRITICAL
      - console: INFO and above
      - QtLogHandler: live GUI logging signal

    Args:
        log_file: Absolute path to the primary application log file.
        level: Root logging level (default DEBUG).

    Returns:
        Configured root logger.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Primary rotating file handler (application.log) — max 5 MB, keep 3 backups
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    # Dedicated error file handler (error.log) — max 5 MB, keep 3 backups
    error_file = log_file.parent / "error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setFormatter(fmt)
    error_handler.setLevel(logging.ERROR)

    # Console handler — INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers to prevent duplicates if called again
    root.handlers.clear()

    root.addHandler(file_handler)
    root.addHandler(error_handler)
    root.addHandler(console_handler)

    qt_handler = get_qt_log_handler()
    if qt_handler and qt_handler not in root.handlers:
        root.addHandler(qt_handler)

    return root


def setup_exception_hook() -> None:
    """Redirect any unhandled Python exception to the logger with full traceback."""
    def _handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root = logging.getLogger("unhandled")
        root.critical("Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = _handle_exception


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
