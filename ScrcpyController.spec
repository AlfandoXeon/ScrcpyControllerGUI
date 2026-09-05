# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Xeon - Scrcpy Controller.
Mode: onedir (runtime files stay visible, modular, and portable with _internal).
"""

import sys
from pathlib import Path

block_cipher = None

datas = [
    ('app/resources/icon.ico', 'app/resources'),
    ('app/resources/icon.png', 'app/resources'),
    ('LogoAplikasi/icon.png', 'LogoAplikasi'),
]
datas = [(src, dst) for src, dst in datas if Path(src).exists()]

a = Analysis(
    ['app/main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'PyQt6.sip',
        'app',
        'app.main',
        'app.controllers.device_controller',
        'app.controllers.scrcpy_controller',
        'app.controllers.main_controller',
        'app.models.config',
        'app.models.device',
        'app.models.preset',
        'app.services.adb_service',
        'app.services.command_builder',
        'app.services.config_service',
        'app.services.preset_service',
        'app.services.scrcpy_service',
        'app.utils.logger',
        'app.utils.paths',
        'app.utils.platform',
        'app.views.main_window',
        'app.views.device_panel',
        'app.views.display_panel',
        'app.views.audio_panel',
        'app.views.window_panel',
        'app.views.advanced_panel',
        'app.views.camera_panel',
        'app.views.tools_panel',
        'app.views.otg_panel',
        'app.views.developer_panel',
        'app.views.dialogs.command_preview_dialog',
        'app.views.dialogs.device_info_dialog',
        'app.views.dialogs.preset_manager_dialog',
        'app.views.dialogs.wireless_dialog',
        'app.views.dialogs.adb_shell_dialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ScrcpyController',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,         # No console window for end users
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app/resources/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ScrcpyController',
)
