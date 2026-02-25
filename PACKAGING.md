# Packaging Guide

This guide explains how to package the Ænglisc Toolkit application for distribution.

## Prerequisites

- Python 3.14+ installed
- Virtual environment activated
- PyInstaller installed (`pip install pyinstaller`)
- Bundled Tectonic assets prepared and verified (see below)

## Bundled PDF Engine Assets (Required)

FullTranslationWindow PDF export uses a bundled Tectonic runtime and offline
bundle. These assets must exist before packaging.

Expected layout:

- `assets/tectonic/binaries/macos/arm64/tectonic`
- `assets/tectonic/binaries/macos/x86_64/tectonic`
- `assets/tectonic/binaries/windows/x86_64/tectonic.exe`
- `assets/tectonic/bundle/default/...`
- `assets/tectonic/manifest.json`

Prepare/update assets:

```bash
python scripts/prepare_tectonic_assets.py \
  --macos-arm64-binary /path/to/tectonic-macos-arm64 \
  --macos-x86_64-binary /path/to/tectonic-macos-x86_64 \
  --windows-x86_64-binary /path/to/tectonic-windows-x86_64.exe \
  --bundle-dir /path/to/tectonic-offline-bundle
```

Verify assets:

```bash
python scripts/verify_tectonic_assets.py
```

## Resources Included

The following resources are automatically included in the packaged application:

- `oeapp/help/assets/` - QtHelp assets (`.qch/.qhc/.qhp/.qhcp` + rendered HTML)
- `assets/tectonic/` - Bundled Tectonic binaries + offline TeX bundle
- `src/oeapp/themes/` - Application themes (if any)

## Building for macOS

1. Ensure you're in the project root directory
2. Activate your virtual environment: `source .venv/bin/activate`
3. Build help assets: `python scripts/build_help.py`
4. Verify Tectonic assets: `python scripts/verify_tectonic_assets.py`
5. Run the build script: `./build_macos.sh`
6. The application will be created in `dist/Ænglisc Toolkit.app`

### Creating a DMG (Optional)

To create a distributable DMG file:

```bash
# Install create-dmg
brew install create-dmg

# Create DMG
create-dmg --volname "Ænglisc Toolkit" \
           --window-pos 200 120 \
           --window-size 800 400 \
           --icon-size 100 \
           --icon "Ænglisc Toolkit.app" 200 190 \
           --hide-extension "Ænglisc Toolkit.app" \
           --app-drop-link 600 185 \
           dist/Ænglisc Toolkit.dmg \
           dist/
```

## Building for Windows

1. Ensure you're in the project root directory
2. Activate your virtual environment: `.venv\Scripts\activate`
3. Build help assets: `python scripts\build_help.py`
4. Verify Tectonic assets: `python scripts\verify_tectonic_assets.py`
5. Run the build script: `build_windows.bat`
6. The executable will be created in `dist\Ænglisc Toolkit.exe`

## Customizing the Build

### Modifying the Spec File

The `oe_annotator.spec` file controls the build process. You can:

- Add an icon: Set `icon='path/to/icon.ico'` (Windows) or `icon='path/to/icon.icns'` (macOS)
- Enable console output: Set `console=True` for debugging
- Add additional data files: Add entries to the `datas` list
- Add hidden imports: Add module names to `hiddenimports`

### Rebuilding

After modifying the spec file, rebuild with:

```bash
pyinstaller oe_annotator.spec --clean
```

## Troubleshooting

### Application Doesn't Start

- Try building with `console=True` in the spec file to see error messages
- Check that all dependencies are included in `hiddenimports`
- Verify that resource paths use `sys._MEIPASS` for bundled applications

### Missing Resources

- Ensure all resources are listed in the `datas` section of the spec file
- Check that resource loading code uses `get_resource_path()` helper function
- Run `python scripts/verify_tectonic_assets.py` and fix any missing payloads

### Large Executable Size

- PySide6 applications are typically 100-200MB
- Consider using `--onefile` for a single executable (slower startup)
- Or use `--onedir` (default) for faster startup with multiple files

## Distribution

- macOS: Distribute the `.app` bundle or a `.dmg` file
- Windows: Distribute the `.exe` file or create an installer using tools like Inno Setup or NSIS
