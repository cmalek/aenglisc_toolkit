CHANGELOG
=========

1.0.1 (2026-09-06)
------------------

Enhancements
^^^^^^^^^^^^

- Published the full Sphinx user's guide for readthedocs.org.

Fixes
^^^^^

- Fixed the macOS app bundle not including the Qt theme files, which
  silently left dark/light themes unavailable.
- Reduced macOS app startup time by switching the PyInstaller build from
  onefile to onedir mode, which previously required re-extracting the
  entire app on every launch.
- Fixed missing ``.ttf`` font files in the macOS PyInstaller bundle.
- Fixed dark text being used for OE token selection highlighting in dark
  mode.
- Fixed the Bosworth-Toller dictionary icon not following the light/dark
  theme.

Changed
^^^^^^^

- Renamed the ``OE_ANNOTATOR_*`` environment variables to
  ``AENGLISC_TOOLKIT_*`` (affects ``AENGLISC_TOOLKIT_TECTONIC_BINARY`` and
  ``AENGLISC_TOOLKIT_TECTONIC_BUNDLE``). Update any scripts or environment
  configuration that set the old names.
- Renamed the application log file from ``oe_annotator.log.json`` to
  ``aenglisc_toolkit.log.json``.

1.0.0 (2026-09-04)
------------------

Enhancements
^^^^^^^^^^^^

- Initial release.
