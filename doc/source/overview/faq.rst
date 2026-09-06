Frequently Asked Questions
==========================

General
-------

What is Ænglisc Toolkit?
^^^^^^^^^^^^^^^^^^^^^^^^

A desktop application that helps a translator organize the work of turning
Old English (Anglo-Saxon) source text into Modern English: morphological
annotation of every word, notes, and a parallel translation, all kept
together in one project. It does not translate or annotate for you — every
linguistic decision is yours.

Is this production-ready?
^^^^^^^^^^^^^^^^^^^^^^^^^

Yes. The application is production-ready. It is safe to use as a
translation aid for translating Old English/Anglo-Saxon source material to
Modern English and persisting the original text and translation to a local
database.

Does it require an internet connection?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No. All project data lives in a local SQLite database on your machine, in the OS specific default location for SQLite databases:

- macOS: ``~/Library/Application Support/Ænglisc Toolkit/default.db``
- Windows: ``%APPDATA%\Ænglisc Toolkit\default.db``
- Linux: ``~/.config/Ænglisc Toolkit/default.db``

Are the database files backed up automatically?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes. Automatic backups are performed every 24 hours, and written to the same directory as the database file, with a filename like ``backups/default-2026-09-06-12-00-00.db.gz``.

You can also manually trigger a backup by pressing **Project → Tools → Backup ow**

How can I backup the database files?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can backup the database files by copying them to a safe location.

Installation
------------

How should I install it?
^^^^^^^^^^^^^^^^^^^^^^^^

Download the ``.dmg`` from the
`GitHub Releases page <https://github.com/cmalek/aenglisc_toolkit/releases>`_.
See :doc:`installation` for the full walkthrough, including the source
install path for contributors.

Is there a Windows or Linux build?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Not yet — only macOS builds are published today. Windows and Linux support
is planned; until then you can run the app from source on those platforms
(see :ref:`installation-from-source`).

Usage
-----

What features exist?
^^^^^^^^^^^^^^^^^^^^^^

The following major features exist:
- Token-by-token morphological annotation
- Multi-word idiom annotation
- Incremental annotation
- Remembered annotations
- Word-span notes
- A side-by-side Full Translation reading/export view
- PDF export with auto-generated glossaries
- DOCX export with annotations as superscripts/subscripts on the Old English text, translation below, for exporting to a word processor for further editing.
- JSON project export/import for sharing, backing up a specific project, or moving it between machines.
- Automatic backups
See :doc:`/overview/annotation` and :doc:`/overview/translation` for the full walkthrough.

Can the app translate or annotate the text for me?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No, deliberately. ``Ænglisc Toolkit`` is an efficiency scaffold for a human
translator, not an automatic translation or parsing tool — it never
assigns annotations or disambiguates grammar on its own.

Troubleshooting
---------------

Something isn't working the way I expect — where do I look first?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Press **F1** to open the in-app Help Center's Troubleshooting topic, which
covers database, annotation, export, and performance issues with concrete
fixes.

Getting help
------------

1. Look at the help documentation inside the application (press **F1**).
2. Read the documentation at https://aenglisc-toolkit.readthedocs.io
3. GitHub issues on the project repository.

When reporting bugs, include the exact steps to reproduce, full error
text, OS, and the application version.
