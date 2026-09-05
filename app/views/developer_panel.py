"""
DeveloperPanel — tab showing developer information.
Simple, minimal, no emoji.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
)

from app.version import APP_NAME, DEVELOPER, VERSION
from app.utils.platform import open_url_in_browser
from app.utils.paths import paths


class DeveloperPanel(QWidget):
    """
    Displays developer contact information.

    Content:
        - App name and version
        - Developer name
        - GitHub link (clickable)
        - Website link (clickable)
    """

    GITHUB_URL = "https://github.com/AlfandoXeon"
    WEBSITE_URL = "https://alfandoxeon.freedev.app"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        # High-res Icon
        icon_label = QLabel()
        icon_file = paths.icon_png if paths.icon_png.exists() else paths.icon_path()
        if icon_file.exists():
            pix = QPixmap(str(icon_file))
            icon_label.setPixmap(
                pix.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(icon_label)

        # App name
        name_label = QLabel(APP_NAME)
        name_font = QFont()
        name_font.setPointSize(13)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(name_label)

        # Version
        ver_label = QLabel(f"Version {VERSION}")
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(ver_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(sep)

        # Developer info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("Developer :"))
        dev_name = QLabel(DEVELOPER)
        dev_row.addWidget(dev_name)
        dev_row.addStretch()
        info_layout.addLayout(dev_row)

        # GitHub link
        gh_row = QHBoxLayout()
        gh_label = QLabel("GitHub   :")
        gh_label.setStyleSheet("color: #888888;")
        gh_row.addWidget(gh_label)
        gh_btn = QPushButton("github.com/AlfandoXeon")
        gh_btn.setFlat(True)
        gh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gh_btn.setStyleSheet(
            "QPushButton { color: #4a9eff; text-decoration: underline; "
            "background: transparent; border: none; padding: 0; text-align: left; font-size: 9pt; }"
            "QPushButton:hover { color: #7abfff; }"
        )
        gh_btn.clicked.connect(lambda: open_url_in_browser(self.GITHUB_URL))
        gh_row.addWidget(gh_btn)
        gh_row.addStretch()
        info_layout.addLayout(gh_row)

        # Website link
        web_row = QHBoxLayout()
        web_label = QLabel("Website  :")
        web_label.setStyleSheet("color: #888888;")
        web_row.addWidget(web_label)
        web_btn = QPushButton("alfandoxeon.freedev.app")
        web_btn.setFlat(True)
        web_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        web_btn.setStyleSheet(
            "QPushButton { color: #4a9eff; text-decoration: underline; "
            "background: transparent; border: none; padding: 0; text-align: left; font-size: 9pt; }"
            "QPushButton:hover { color: #7abfff; }"
        )
        web_btn.clicked.connect(lambda: open_url_in_browser(self.WEBSITE_URL))
        web_row.addWidget(web_btn)
        web_row.addStretch()
        info_layout.addLayout(web_row)

        outer.addLayout(info_layout)
        outer.addStretch()
