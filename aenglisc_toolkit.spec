# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

helpbook_source = Path('oeapp/help/macos/AengliscToolkit.help')
helpbook_datas = []
if helpbook_source.exists():
    helpbook_datas.append((str(helpbook_source), 'AengliscToolkit.help'))

a = Analysis(
    ['oeapp/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('oeapp/help/assets', 'oeapp/help/assets'),
        *helpbook_datas,
        ('oeapp/etc', 'oeapp/etc'),
        ('oeapp/models/alembic', 'oeapp/models/alembic'),
        ('assets/logo.icns', 'assets'),
        ('assets/tectonic', 'assets/tectonic'),
        ('assets/*.ttf', 'assets'),
        *collect_data_files('qt_themes'),
    ],
    hiddenimports=[],
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
    name='Ænglisc Toolkit',
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
    icon='assets/logo.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Ænglisc Toolkit',
)

app = BUNDLE(
    coll,
    name='Ænglisc Toolkit.app',
    icon='assets/logo.png',
    bundle_identifier='org.placodermi.aenglisc-toolkit',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleName': 'Ænglisc Toolkit',
        'CFBundleDisplayName': 'Ænglisc Toolkit',
        'CFBundleGetInfoString': 'Ænglisc Toolkit',
        'CFBundleIdentifier': 'org.placodermi.aenglisc-toolkit',
        'CFBundleVersion': '1.0.1',
        'CFBundleShortVersionString': '1.0.1',
        'CFBundleHelpBookFolder': 'AengliscToolkit.help',
        'CFBundleHelpBookName': 'Ænglisc Toolkit Help',
        'NSHumanReadableCopyright': 'Copyright © 2026',
    },
)
