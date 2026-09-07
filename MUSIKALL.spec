# -*- mode: python ; coding: utf-8 -*-

hiddenimports = [
    'tkinterweb',
    'py3Dmol',
    'mplcursors',
    'pygame',
    'Bio',
    'Bio.PDB',
    'Bio.Align',
    'Bio.SeqUtils',
    'scipy',
    'scipy.spatial',
    'pandas',
    'numpy',
    'networkx',
    'sklearn',
    'sklearn.cluster',
    'sklearn.cluster._kmeans',
    'openpyxl',
    'xlsxwriter',
    'midiutil',
    'PIL',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore',
]

datas = [
    ('welcome.png', '.'),
    ('icon.ico', '.'),
    ('icon.png', '.'),
    ('icon_256.png', '.'),
    ('3Dmol-min.js', '.'),
    ('README.md', '.'),
    ('LICENSE', '.'),
    ('CITATION.cff', '.'),
    ('THIRD_PARTY_NOTICES.md', '.'),
    ('requirements.txt', '.'),
]

a = Analysis(
    ['MUSIKALL_gui1.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    icon='icon.ico',
)

viewer_a = Analysis(
    ['MUSIKALL_3d_viewer.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

viewer_pyz = PYZ(viewer_a.pure)

viewer_exe = EXE(
    viewer_pyz,
    viewer_a.scripts,
    [],
    exclude_binaries=True,
    name='MUSIKALL_3d_viewer',
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
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    viewer_exe,
    a.binaries,
    viewer_a.binaries,
    a.datas,
    viewer_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MUSIKALL',
)
