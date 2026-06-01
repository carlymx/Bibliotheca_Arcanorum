# -*- mode: python ; coding: utf-8 -*-
# build.spec — PyInstaller spec para Gestor_biblioteca
# Uso: pyinstaller build.spec

import os
import re
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

with open('tools/Gestor_biblioteca/src/app.py', encoding='utf-8') as _f:
    _m = re.search(r'^VERSION\s*=\s*"([^"]+)"', _f.read(), re.M)
    VERSION = _m.group(1) if _m else "0.0.0"

block_cipher = None

pdftoppm_path = os.environ.get('PDFTOPPM', '')

extra_binaries = []
if pdftoppm_path and os.path.isfile(pdftoppm_path):
    extra_binaries.append((pdftoppm_path, '.'))

sv_ttk_datas = collect_data_files('sv_ttk')
sv_ttk_submodules = collect_submodules('sv_ttk')

icon_datas = [
    ('tools/Gestor_biblioteca/src/assets/icons', 'src/assets/icons'),
]

a = Analysis(
    ['tools/Gestor_biblioteca/main.py'],
    pathex=[],
    binaries=extra_binaries,
    datas=sv_ttk_datas + icon_datas,
    hiddenimports=[
        'sv_ttk',
        'PIL', 'PIL.Image',
        'mutagen',
        'mutagen.mp3', 'mutagen.mp4', 'mutagen.oggvorbis', 'mutagen.flac',
        'mutagen.id3',
        'rarfile',
        'mobi',
        'certifi',
    ] + sv_ttk_submodules,
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
        target_arch=os.environ.get('MACOS_ARCH', None),
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
            'CFBundleShortVersionString': VERSION,
            'CFBundleVersion': VERSION,
        },
    )
else:
    icon_path = 'assets/icon.ico' if sys.platform == 'win32' else 'assets/icon.png'
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='Gestor_biblioteca',
        icon=icon_path,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
    )
