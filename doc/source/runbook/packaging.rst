.. _runbook__packaging:

=========
Packaging
=========

This guide explains how to package ``Ænglisc Toolkit`` for distribution.

Prerequisites
=============

- Python 3.14+ installed
- Virtual environment activated
- PyInstaller installed (``pip install pyinstaller``)
- Bundled Tectonic assets prepared and verified (see below)

Bundled PDF Engine Assets (Required)
=====================================

``FullTranslationWindow`` PDF export uses a bundled Tectonic runtime and
offline bundle. These assets must exist before packaging.

Expected layout:

- ``assets/tectonic/binaries/macos/arm64/tectonic``
- ``assets/tectonic/binaries/macos/x86_64/tectonic``
- ``assets/tectonic/binaries/windows/x86_64/tectonic.exe``
- ``assets/tectonic/bundle/default/...``
- ``assets/tectonic/manifest.json``

Prepare/update assets:

.. code-block:: shell

   python scripts/prepare_tectonic_assets.py \
     --macos-arm64-binary /path/to/tectonic-macos-arm64 \
     --macos-x86_64-binary /path/to/tectonic-macos-x86_64 \
     --windows-x86_64-binary /path/to/tectonic-windows-x86_64.exe \
     --bundle-dir /path/to/tectonic-offline-bundle

Verify assets:

.. code-block:: shell

   python scripts/verify_tectonic_assets.py

Helper Make targets:

.. code-block:: shell

   # Download official binaries + default bundle, stage into assets/tectonic, and verify.
   make tectonic-assets

   # Only verify existing packaged assets.
   make tectonic-assets-verify

Optional overrides:

.. code-block:: shell

   # Pin a specific Tectonic release or bundle URL.
   make tectonic-assets \
     TECTONIC_VERSION=0.15.0 \
     TECTONIC_BUNDLE_URL=https://relay.fullyjustified.net/default_bundle_v33.tar

Resources Included
===================

The following resources are automatically included in the packaged
application:

- ``oeapp/help/assets/`` - QtHelp assets (``.qch``/``.qhc``/``.qhp``/``.qhcp`` + rendered HTML)
- ``oeapp/help/macos/AengliscToolkit.help/`` - Apple Help Book assets used by native macOS Help-menu search
- ``assets/tectonic/`` - Bundled Tectonic binaries + offline TeX bundle
- ``assets/*.ttf/`` - Bundled application fonts
- ``src/oeapp/themes/`` - Application themes (if any)

Building for macOS
==================

1. Ensure you're in the project root directory
2. Activate your virtual environment: ``source .venv/bin/activate``
3. Build help assets: ``python scripts/build_help.py``
4. Build Apple Help Book assets: ``python scripts/build_macos_helpbook.py``
5. Verify Tectonic assets: ``python scripts/verify_tectonic_assets.py``
6. Run the build script: ``./build_macos.sh``
7. The application will be created in ``dist/Ænglisc Toolkit.app``

Native macOS Help-menu search
------------------------------

- The search field at the top of the macOS Help menu is controlled by
  macOS Help Viewer.
- It uses the app bundle's Apple Help Book, not the in-app QtHelp UI
  directly.
- In development runs where the app menu bar shows **Python** (not
  **Ænglisc Toolkit**), that search field is associated with Python's
  help context.
- To validate native Help-menu search against Ænglisc Toolkit help
  content, test using the packaged ``dist/Ænglisc Toolkit.app``.

Creating a DMG (Optional)
--------------------------

To create a distributable DMG file:

.. code-block:: shell

   # Install create-dmg
   brew install create-dmg

   # Stage only the app bundle (dist/ also contains a standalone PyInstaller executable)
   mkdir -p dist/dmg-root
   rm -rf dist/dmg-root/*
   cp -R "dist/Ænglisc Toolkit.app" "dist/dmg-root/"

   # Create DMG
   create-dmg --volname "Ænglisc Toolkit" \
              --app-drop-link 600 185 \
              dist/Ænglisc Toolkit.dmg \
              dist/dmg-root

Building for Windows
======================

1. Ensure you're in the project root directory
2. Activate your virtual environment: ``.venv\Scripts\activate``
3. Build help assets: ``python scripts\build_help.py``
4. Verify Tectonic assets: ``python scripts\verify_tectonic_assets.py``
5. Run the build script: ``build_windows.bat``
6. The executable will be created in ``dist\Ænglisc Toolkit.exe``

Customizing the Build
=======================

Modifying the Spec File
-------------------------

The ``aenglisc_toolkit.spec`` file controls the build process. You can:

- Add an icon: Set ``icon='path/to/icon.ico'`` (Windows) or
  ``icon='path/to/icon.icns'`` (macOS)
- Enable console output: Set ``console=True`` for debugging
- Add additional data files: Add entries to the ``datas`` list
- Add hidden imports: Add module names to ``hiddenimports``

Rebuilding
-----------

After modifying the spec file, rebuild with:

.. code-block:: shell

   pyinstaller aenglisc_toolkit.spec --clean

Troubleshooting
================

Application Doesn't Start
---------------------------

- Try building with ``console=True`` in the spec file to see error
  messages
- Check that all dependencies are included in ``hiddenimports``
- Verify that resource paths use ``sys._MEIPASS`` for bundled applications

Missing Resources
-------------------

- Ensure all resources are listed in the ``datas`` section of the spec
  file
- Check that resource loading code uses ``get_resource_path()`` helper
  function
- Run ``python scripts/verify_tectonic_assets.py`` and fix any missing
  payloads

Large Executable Size
-----------------------

- PySide6 applications are typically 100-200MB
- Consider using ``--onefile`` for a single executable (slower startup)
- Or use ``--onedir`` (default) for faster startup with multiple files

Distribution
=============

- macOS: Distribute the ``.app`` bundle or a ``.dmg`` file
- Windows: Distribute the ``.exe`` file or create an installer using tools
  like Inno Setup or NSIS
