"""
ADBShellDialog — custom interactive terminal window for direct ADB shell access.

Features:
- Standalone resizable window with dark modern console aesthetic (zero emojis).
- Real-time command streaming via QProcess.
- Command history buffer navigable with Up/Down arrow keys.
- Quick action command chips (pm list, getprop, df, battery, ip).
- Output auto-scrolling with color differentiation (stdout, stderr, exit code).
- Interrupt / Stop button to terminate running commands.
- Built-in clear and exit commands.
"""

import html
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QProcess, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
)

from app.utils.paths import paths


class ShellInputLineEdit(QLineEdit):
    """Command input field that traps Up and Down keys for history navigation."""

    up_pressed = pyqtSignal()
    down_pressed = pyqtSignal()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Up:
            self.up_pressed.emit()
            return
        elif event.key() == Qt.Key.Key_Down:
            self.down_pressed.emit()
            return
        super().keyPressEvent(event)


class ADBShellDialog(QDialog):
    """
    Dedicated interactive terminal dialog for communicating with Android ADB Shell.
    """

    def __init__(
        self,
        serial: str,
        device_name: str = "",
        adb_path: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window)  # Independent top-level window
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._serial = serial
        self._device_name = device_name or serial
        self._adb_path = adb_path or paths.adb_exe

        # History buffer
        self._history: list[str] = []
        self._history_index: int = -1

        # Execution process
        self._process: Optional[QProcess] = None

        self.setWindowTitle(f"Xeon — ADB Shell Terminal [{self._device_name}]")
        self.resize(800, 540)
        self.setMinimumSize(620, 400)

        # Set window icon
        icon_file = paths.icon_png if paths.icon_png.exists() else paths.icon_path()
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))

        self._init_ui()
        self._print_welcome_banner()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # 1. Top Header Row: Device label, status, and control actions
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        lbl_device = QLabel(f"Target: {self._device_name} ({self._serial})")
        lbl_device.setStyleSheet("font-weight: bold; color: #abb2bf; font-size: 12px;")
        header_layout.addWidget(lbl_device)

        header_layout.addStretch()

        self._status_badge = QLabel("Ready")
        self._status_badge.setStyleSheet(
            "background-color: #1e2530; color: #98c379; border: 1px solid #2e3a4e; "
            "border-radius: 3px; padding: 2px 8px; font-size: 11px;"
        )
        header_layout.addWidget(self._status_badge)

        self._btn_interrupt = QPushButton("Interrupt (Ctrl+C)")
        self._btn_interrupt.setEnabled(False)
        self._btn_interrupt.clicked.connect(self._on_interrupt)
        header_layout.addWidget(self._btn_interrupt)

        self._btn_clear = QPushButton("Clear Screen")
        self._btn_clear.clicked.connect(self._on_clear)
        header_layout.addWidget(self._btn_clear)

        root_layout.addLayout(header_layout)

        # 2. Quick Command Chips Row
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)

        lbl_quick = QLabel("Quick Commands:")
        lbl_quick.setStyleSheet("color: #7b889b; font-size: 11px;")
        quick_layout.addWidget(lbl_quick)

        quick_cmds = [
            ("Apps (3rd Party)", "pm list packages -3"),
            ("OS Version", "getprop ro.build.version.release"),
            ("Storage", "df -h /data"),
            ("Battery", "dumpsys battery"),
            ("Network IP", "ip -f inet addr show wlan0"),
        ]

        for label, cmd in quick_cmds:
            btn = QPushButton(label)
            btn.setStyleSheet("font-size: 11px; padding: 3px 8px;")
            btn.clicked.connect(lambda checked=False, c=cmd: self._run_quick_command(c))
            quick_layout.addWidget(btn)

        quick_layout.addStretch()
        root_layout.addLayout(quick_layout)

        # 3. Terminal Console Output
        self._terminal_output = QPlainTextEdit()
        self._terminal_output.setReadOnly(True)
        self._terminal_output.setMaximumBlockCount(4000)
        self._terminal_output.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #111418;"
            "  color: #abb2bf;"
            "  border: 1px solid #232833;"
            "  border-radius: 4px;"
            "  padding: 8px;"
            "  font-family: Consolas, 'Courier New', monospace;"
            "  font-size: 11px;"
            "  line-height: 1.4;"
            "}"
        )
        root_layout.addWidget(self._terminal_output, 1)

        # 4. Input Row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        lbl_prompt = QLabel("$")
        lbl_prompt.setStyleSheet(
            "font-weight: bold; color: #98c379; font-size: 13px; font-family: monospace;"
        )
        input_layout.addWidget(lbl_prompt)

        self._cmd_input = ShellInputLineEdit()
        self._cmd_input.setPlaceholderText("Enter Android shell command (e.g. ls, getprop, pm, logcat)...")
        self._cmd_input.setStyleSheet(
            "QLineEdit {"
            "  background-color: #171b22;"
            "  color: #dcdfe4;"
            "  border: 1px solid #2c3340;"
            "  border-radius: 4px;"
            "  padding: 6px 10px;"
            "  font-family: Consolas, 'Courier New', monospace;"
            "  font-size: 11px;"
            "}"
            "QLineEdit:focus {"
            "  border-color: #4b89dc;"
            "}"
        )
        self._cmd_input.returnPressed.connect(self._on_execute_pressed)
        self._cmd_input.up_pressed.connect(self._on_history_up)
        self._cmd_input.down_pressed.connect(self._on_history_down)
        input_layout.addWidget(self._cmd_input, 1)

        self._btn_execute = QPushButton("Execute")
        self._btn_execute.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        self._btn_execute.clicked.connect(self._on_execute_pressed)
        input_layout.addWidget(self._btn_execute)

        root_layout.addLayout(input_layout)

    # -------------------------------------------------------------------------
    # Banner and Printing Helpers
    # -------------------------------------------------------------------------

    def _print_welcome_banner(self) -> None:
        banner = (
            f"<div style='color: #61afef; font-weight: bold;'>"
            f"=== Android Shell Session: {html.escape(self._device_name)} ===</div>"
            f"<div style='color: #7b889b;'>Serial: {html.escape(self._serial)} | "
            f"Type 'clear' to clear console, 'exit' to close window.</div>"
            f"<div style='color: #5c6370;'>-----------------------------------------------------------------------</div>"
        )
        self._terminal_output.appendHtml(banner)

    def _append_raw_text(self, text: str, color: str = "#abb2bf") -> None:
        escaped = html.escape(text)
        formatted = f"<span style='color: {color}; white-space: pre-wrap;'>{escaped}</span>"
        self._terminal_output.appendHtml(formatted)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        sb = self._terminal_output.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    # -------------------------------------------------------------------------
    # Execution Logic
    # -------------------------------------------------------------------------

    def _run_quick_command(self, cmd: str) -> None:
        self._cmd_input.setText(cmd)
        self._on_execute_pressed()

    def _on_execute_pressed(self) -> None:
        cmd = self._cmd_input.text().strip()
        if not cmd:
            return

        # Built-in handlers
        if cmd.lower() in ("clear", "cls"):
            self._on_clear()
            self._cmd_input.clear()
            return

        if cmd.lower() in ("exit", "quit"):
            self.close()
            return

        # Record history
        if not self._history or self._history[-1] != cmd:
            self._history.append(cmd)
        self._history_index = len(self._history)
        self._cmd_input.clear()

        # Print command line in terminal
        cmd_html = (
            f"<div style='margin-top: 4px;'>"
            f"<span style='color: #98c379; font-weight: bold;'>$ </span>"
            f"<span style='color: #ffffff; font-weight: bold;'>{html.escape(cmd)}</span>"
            f"</div>"
        )
        self._terminal_output.appendHtml(cmd_html)
        self._scroll_to_bottom()

        # If a process is already running, terminate it before running new command
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._append_raw_text("[Previous command still running — terminating]\n", color="#e5c07b")
            self._process.kill()
            self._process.waitForFinished(1000)

        # Launch QProcess
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._on_stdout_ready)
        self._process.readyReadStandardError.connect(self._on_stderr_ready)
        self._process.finished.connect(self._on_process_finished)

        args = ["-s", self._serial, "shell", cmd]
        self._status_badge.setText("Running...")
        self._status_badge.setStyleSheet(
            "background-color: #2b2313; color: #e5c07b; border: 1px solid #5a451e; "
            "border-radius: 3px; padding: 2px 8px; font-size: 11px;"
        )
        self._btn_interrupt.setEnabled(True)

        self._process.start(str(self._adb_path), args)

    def _on_stdout_ready(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self._append_raw_text(data, color="#abb2bf")

    def _on_stderr_ready(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self._append_raw_text(data, color="#e06c75")

    def _on_process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._btn_interrupt.setEnabled(False)
        self._status_badge.setText("Ready")
        self._status_badge.setStyleSheet(
            "background-color: #1e2530; color: #98c379; border: 1px solid #2e3a4e; "
            "border-radius: 3px; padding: 2px 8px; font-size: 11px;"
        )
        msg = f"[Process finished with exit code {exit_code}]"
        color = "#5c6370" if exit_code == 0 else "#e06c75"
        self._append_raw_text(f"{msg}\n", color=color)

    def _on_interrupt(self) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self._append_raw_text("[Command interrupted by user]\n", color="#e5c07b")
            self._btn_interrupt.setEnabled(False)
            self._status_badge.setText("Ready")
            self._status_badge.setStyleSheet(
                "background-color: #1e2530; color: #98c379; border: 1px solid #2e3a4e; "
                "border-radius: 3px; padding: 2px 8px; font-size: 11px;"
            )

    def _on_clear(self) -> None:
        self._terminal_output.clear()
        self._print_welcome_banner()

    # -------------------------------------------------------------------------
    # Command History Navigation
    # -------------------------------------------------------------------------

    def _on_history_up(self) -> None:
        if not self._history:
            return
        if self._history_index > 0:
            self._history_index -= 1
            self._cmd_input.setText(self._history[self._history_index])

    def _on_history_down(self) -> None:
        if not self._history:
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self._cmd_input.setText(self._history[self._history_index])
        else:
            self._history_index = len(self._history)
            self._cmd_input.clear()

    def closeEvent(self, event) -> None:
        """Terminate any ongoing process when the dialog is closed."""
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self._process.waitForFinished(500)
        super().closeEvent(event)
