# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../version.py', '.'),
        ('../config/default_config.py', 'config'),
        ('../database/schema.py', 'database'),
        ('../resources/icons/*', 'resources/icons'),
    ],
    hiddenimports=[
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 
        'sqlite3', 'chromadb', 'requests', 'pymupdf', 'fitz'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['IPython', 'sphinx', 'matplotlib', 'tkinter', 'numba', 'llvmlite', 'docutils', 'babel', 'pytz'],
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
    name='rootChat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='rootChat',
)
