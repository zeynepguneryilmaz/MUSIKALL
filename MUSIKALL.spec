# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['MUSIKALL_gui1.py'],
    pathex=[],
    binaries=[],
    datas=[('welcome.png', '.'), ('icon.ico', '.')],
    hiddenimports=['tkinterweb', 'py3Dmol', 'mplcursors', 'pygame', 'Bio', 'sklearn', 'scipy', 'pandas', 'numpy', 'networkx'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MUSIKALL',
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
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MUSIKALL',
)
