# Settings

## Overview

Use Settings to control backup behavior and the application theme.

## Open Settings

- **macOS**: Application menu -> **Preferences...** (`Ctrl+,`)
- **Windows/Linux**: **File** -> **Settings...**

## Available Settings

### Backup Settings

- **Number of backups to keep**: rolling backup retention (1-100)
- **Backup interval (minutes)**: how often automatic backups are created (1-1440)

### Theme Setting

- **Theme**: choose `dark` or `light`

## Theme Changes Require Restart

When you change the theme, the app shows a confirmation message. The new theme is saved immediately, but it does **not** apply until you fully quit and restart Ænglisc Toolkit.

Recommended sequence:

1. Open Settings.
2. Select `dark` or `light`.
3. Click **OK**.
4. Quit the app completely.
5. Launch the app again.

## Notes

- Manual backup is always available from **Tools -> Backup Now**.
- Backup settings affect automatic backups; they do not remove existing export files.

## Undo Support

> **Undo support:** Settings changes are not part of the editor undo stack. `Ctrl+Z` does not revert settings. To revert, open Settings and change values back manually. Theme changes still require restart.

## Back to Start Here

- [Start Here](start-here.html)
