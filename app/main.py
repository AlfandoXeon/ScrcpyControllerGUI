"""
Xeon - Scrcpy Controller
Entry point.

Initializes logging, validates runtime, creates all services and controllers,
then launches the main window.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path when running from source
# ---------------------------------------------------------------------------
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from app.version import APP_NAME, VERSION
from app.utils.paths import paths
from app.utils.logger import setup_logging, get_logger


def _check_runtime() -> list[str]:
    """
    Verify that required runtime binaries exist.

    Returns:
        List of error messages (empty = all OK).
    """
    errors: list[str] = []
    if not paths.adb_exists():
        errors.append(f"ADB runtime not found.\nExpected: {paths.adb_exe}")
    if not paths.scrcpy_exists():
        errors.append(f"Scrcpy runtime not found.\nExpected: {paths.scrcpy_exe}")
    return errors


def main() -> None:
    """Application entry point."""

    # Ensure user data directories exist before logging starts
    paths.ensure_dirs()

    # Setup logging (application.log and dedicated error.log in logs/)
    setup_logging(paths.log_file)
    from app.utils.logger import setup_exception_hook
    setup_exception_hook()

    logger = get_logger(__name__)
    logger.info("=" * 60)
    logger.info("%s v%s starting up.", APP_NAME, VERSION)
    logger.info("App root: %s", paths.app_root)
    logger.info("ADB path: %s", paths.adb_exe)
    logger.info("Scrcpy path: %s", paths.scrcpy_exe)
    logger.info("Config: %s", paths.settings_file)
    logger.info("Logs folder: %s", paths.logs_dir)
    logger.info("Primary log: %s", paths.log_file)

    # Forward Qt internal warnings/errors to python logger
    from PyQt6.QtCore import qInstallMessageHandler, QtMsgType
    def _qt_message_handler(mode, context, message):
        if mode == QtMsgType.QtWarningMsg:
            logger.warning("[Qt] %s", message)
        elif mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            logger.error("[Qt] %s", message)
    qInstallMessageHandler(_qt_message_handler)

    # Create QApplication first (required for QMessageBox)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("AlfandoXeon")

    # Set high-res application icon (crisp PNG)
    icon_file = paths.icon_png if paths.icon_png.exists() else paths.icon_path()
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))

    # Apply stylesheet
    _apply_stylesheet(app)

    # Check runtime files
    errors = _check_runtime()
    if errors:
        msg = "\n\n".join(errors)
        logger.error("Runtime check failed:\n%s", msg)
        QMessageBox.critical(
            None,
            "Runtime Error",
            f"{APP_NAME} could not start.\n\n{msg}\n\n"
            "Please ensure scrcpy and ADB are present in the 'runtime' folder.",
        )
        sys.exit(1)

    # Import services and controllers
    from app.services.adb_service import ADBService
    from app.services.scrcpy_service import ScrcpyService
    from app.services.command_builder import CommandBuilder, CameraCommandBuilder, OTGCommandBuilder
    from app.services.config_service import ConfigService
    from app.services.preset_service import PresetService
    from app.controllers.device_controller import DeviceController
    from app.controllers.scrcpy_controller import ScrcpyController
    from app.controllers.main_controller import MainController
    from app.views.main_window import MainWindow

    # Instantiate services
    config_svc = ConfigService(paths.settings_file)
    preset_svc = PresetService(paths.presets_file)
    adb_svc = ADBService()
    scrcpy_svc = ScrcpyService()
    cmd_builder = CommandBuilder()
    cam_builder = CameraCommandBuilder()
    otg_builder = OTGCommandBuilder()

    # Instantiate controllers
    device_ctrl = DeviceController(adb_svc)
    scrcpy_ctrl = ScrcpyController(scrcpy_svc, cmd_builder, cam_builder, otg_builder)

    # Create and show window
    window = MainWindow()
    main_ctrl = MainController(
        window=window,
        device_ctrl=device_ctrl,
        scrcpy_ctrl=scrcpy_ctrl,
        config_service=config_svc,
        preset_service=preset_svc,
    )

    window.show()
    main_ctrl.start()

    logger.info("Main window shown. Entering event loop.")
    exit_code = app.exec()
    logger.info("%s exited with code %d.", APP_NAME, exit_code)
    sys.exit(exit_code)


def _apply_stylesheet(app: QApplication) -> None:
    """
    Dark theme stylesheet — professional desktop software aesthetic.
    High contrast text on dark backgrounds, clean tab and form styling.
    """
    qss = """
    /* ── Base ─────────────────────────────────────────────────── */
    QWidget {
        background-color: #1e1e1e;
        color: #e8e8e8;
        font-family: "Segoe UI", sans-serif;
        font-size: 9pt;
    }

    QMainWindow {
        background-color: #1e1e1e;
    }

    /* ── ScrollArea ────────────────────────────────────────────── */
    QScrollArea {
        background: transparent;
        background-color: transparent;
        border: none;
    }

    QScrollArea > QWidget > QWidget {
        background: transparent;
        background-color: transparent;
    }

    /* ── Tab Widget ───────────────────────────────────────────── */
    QTabWidget::pane {
        border: 1px solid #3a3a3a;
        background-color: #252525;
        padding: 0px;
    }

    QTabWidget::tab-bar {
        alignment: left;
    }

    QTabBar {
        background: transparent;
        qproperty-expanding: true;
    }

    QTabBar::tab {
        background-color: #2a2a2a;
        color: #aaaaaa;
        border: 1px solid #3a3a3a;
        border-bottom: 1px solid #3a3a3a;
        padding: 8px 12px;
        min-width: 60px;
        margin-right: 0px;
        text-align: center;
    }

    QTabBar::tab:selected {
        background-color: #252525;
        color: #ffffff;
        border-bottom: 2px solid #4a9eff;
        font-weight: bold;
    }

    QTabBar::tab:hover:!selected {
        background-color: #333333;
        color: #dddddd;
    }

    QTabBar::scroller {
        width: 20px;
    }

    QTabBar QToolButton {
        background-color: #2a2a2a;
        border: 1px solid #3a3a3a;
        color: #aaaaaa;
        padding: 2px;
    }

    QTabBar QToolButton:hover {
        background-color: #3a3a3a;
        color: #ffffff;
    }

    /* ── GroupBox ─────────────────────────────────────────────── */
    QGroupBox {
        background-color: #252525;
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        margin-top: 10px;
        padding: 8px 8px 8px 8px;
        font-weight: bold;
        color: #cccccc;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        top: -1px;
        padding: 0 4px;
        color: #4a9eff;
        background-color: transparent;
    }

    /* ── Labels ───────────────────────────────────────────────── */
    QLabel {
        color: #e0e0e0;
        background: transparent;
    }

    /* ── Buttons ──────────────────────────────────────────────── */
    QPushButton {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #4a4a4a;
        border-radius: 3px;
        padding: 5px 12px;
        min-height: 24px;
    }

    QPushButton:hover {
        background-color: #383838;
        border-color: #5a5a5a;
        color: #ffffff;
    }

    QPushButton:pressed {
        background-color: #222222;
        border-color: #4a9eff;
    }

    QPushButton:disabled {
        background-color: #252525;
        color: #555555;
        border-color: #333333;
    }

    /* START button — green */
    QPushButton[running="false"] {
        background-color: #1a6b35;
        color: #ffffff;
        border-color: #14522a;
        font-weight: bold;
        font-size: 10pt;
        min-height: 34px;
    }

    QPushButton[running="false"]:hover {
        background-color: #1f7e3f;
        border-color: #18603a;
    }

    QPushButton[running="false"]:disabled {
        background-color: #1a3325;
        color: #556655;
        border-color: #223322;
    }

    /* STOP button — red */
    QPushButton[running="true"] {
        background-color: #8b1a1a;
        color: #ffffff;
        border-color: #6b1414;
        font-weight: bold;
        font-size: 10pt;
        min-height: 34px;
    }

    QPushButton[running="true"]:hover {
        background-color: #a32020;
        border-color: #7a1818;
    }

    /* Flat / link-style buttons (developer panel) */
    QPushButton[flat="true"],
    QPushButton:flat {
        background: transparent;
        border: none;
        color: #4a9eff;
        padding: 0px;
        text-align: left;
    }

    QPushButton:flat:hover {
        color: #7abfff;
        text-decoration: underline;
    }

    /* ── ComboBox ─────────────────────────────────────────────── */
    QComboBox {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #4a4a4a;
        border-radius: 3px;
        padding: 4px 8px;
        min-height: 24px;
        selection-background-color: #3a5a8a;
    }

    QComboBox:hover {
        border-color: #5a5a5a;
    }

    QComboBox:on {
        border-color: #4a9eff;
    }

    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #4a4a4a;
        background: #333333;
    }

    QComboBox::down-arrow {
        width: 8px;
        height: 8px;
    }

    QComboBox QAbstractItemView {
        background-color: #2a2a2a;
        color: #e0e0e0;
        border: 1px solid #4a4a4a;
        selection-background-color: #3a5a8a;
        selection-color: #ffffff;
        outline: none;
    }

    /* ── Text inputs ──────────────────────────────────────────── */
    QLineEdit,
    QPlainTextEdit,
    QSpinBox {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #4a4a4a;
        border-radius: 3px;
        padding: 4px 6px;
        selection-background-color: #3a5a8a;
    }

    QLineEdit:focus,
    QPlainTextEdit:focus,
    QSpinBox:focus {
        border-color: #4a9eff;
        outline: none;
    }

    QLineEdit::placeholder,
    QPlainTextEdit::placeholder {
        color: #606060;
    }

    QSpinBox::up-button,
    QSpinBox::down-button {
        background-color: #333333;
        border: none;
        width: 16px;
    }

    QSpinBox::up-button:hover,
    QSpinBox::down-button:hover {
        background-color: #444444;
    }

    /* ── CheckBox ─────────────────────────────────────────────── */
    QCheckBox {
        color: #e0e0e0;
        spacing: 6px;
        background: transparent;
    }

    QCheckBox::indicator {
        width: 14px;
        height: 14px;
        border: 1px solid #5a5a5a;
        border-radius: 2px;
        background-color: #2d2d2d;
    }

    QCheckBox::indicator:checked {
        background-color: #4a9eff;
        border-color: #4a9eff;
    }

    QCheckBox::indicator:hover {
        border-color: #7abfff;
    }

    QCheckBox:disabled {
        color: #555555;
    }

    /* ── ListWidget ───────────────────────────────────────────── */
    QListWidget {
        background-color: #2a2a2a;
        color: #e0e0e0;
        border: 1px solid #3a3a3a;
        border-radius: 3px;
        outline: none;
    }

    QListWidget::item {
        padding: 4px 8px;
        border-bottom: 1px solid #333333;
    }

    QListWidget::item:selected {
        background-color: #3a5a8a;
        color: #ffffff;
    }

    QListWidget::item:hover:!selected {
        background-color: #333333;
    }

    /* ── ScrollBar ────────────────────────────────────────────── */
    QScrollBar:vertical {
        background: #1e1e1e;
        width: 10px;
        margin: 0px;
    }

    QScrollBar::handle:vertical {
        background: #4a4a4a;
        border-radius: 4px;
        min-height: 24px;
        margin: 1px 2px;
    }

    QScrollBar::handle:vertical:hover {
        background: #5a5a5a;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background: #1e1e1e;
        height: 10px;
        margin: 0px;
    }

    QScrollBar::handle:horizontal {
        background: #4a4a4a;
        border-radius: 4px;
        min-width: 24px;
        margin: 2px 1px;
    }

    QScrollBar::handle:horizontal:hover {
        background: #5a5a5a;
    }

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* ── StatusBar ────────────────────────────────────────────── */
    QStatusBar {
        background-color: #181818;
        color: #aaaaaa;
        border-top: 1px solid #333333;
        font-size: 8pt;
    }

    QStatusBar QLabel {
        color: #aaaaaa;
        background: transparent;
        padding: 2px 8px;
        border-left: 1px solid #333333;
    }

    QStatusBar QLabel#status_msg {
        border-left: none;
        padding-left: 6px;
    }

    /* ── Dialog ───────────────────────────────────────────────── */
    QDialog {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }

    /* ── MessageBox ───────────────────────────────────────────── */
    QMessageBox {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }

    QMessageBox QLabel {
        color: #e0e0e0;
    }

    /* ── Tooltip ──────────────────────────────────────────────── */
    QToolTip {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #4a4a4a;
        padding: 4px;
    }

    /* ── Separator / Frame ───────────────────────────────────── */
    QFrame[frameShape="4"],
    QFrame[frameShape="5"] {
        color: #3a3a3a;
    }

    /* ── InputDialog ──────────────────────────────────────────── */
    QInputDialog {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }

    /* ── DialogButtonBox ──────────────────────────────────────── */
    QDialogButtonBox QPushButton {
        min-width: 72px;
    }
    """
    app.setStyleSheet(qss)


if __name__ == "__main__":
    main()
