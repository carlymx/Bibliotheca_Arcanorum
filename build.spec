# -*- mode: python ; coding: utf-8 -*-
# build.spec — PyInstaller spec para Gestor_biblioteca
# Uso: pyinstaller build.spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['tools/Gestor_biblioteca/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'sv_ttk',
        'PIL', 'PIL.Image',
        'mutagen',
        'mutagen.mp3', 'mutagen.mp4', 'mutagen.oggvorbis', 'mutagen.flac',
        'mutagen.id3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'notebook', 'ipython', 'jupyter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='Gestor_biblioteca',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    app = BUNDLE(
        exe,
        name='Gestor_biblioteca.app',
        icon='assets/icon.icns',
        bundle_identifier='com.aquelarre.gestor-biblioteca',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '0.8.0',
            'CFBundleVersion': '0.8.0',
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='Gestor_biblioteca',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
    )
