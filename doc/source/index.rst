===============
Ænglisc Toolkit
===============

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :hidden:

   overview/installation
   overview/quickstart
   overview/domain_language

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   :hidden:

   overview/projects
   overview/project_organization
   overview/annotation
   overview/presets
   overview/remembered_annotations
   overview/translation
   overview/backups
   overview/updating
   overview/faq

.. toctree::
   :maxdepth: 2
   :caption: Development
   :hidden:

   architecture/index
   runbook/contributing
   runbook/coding_standards
   runbook/packaging

.. toctree::
   :maxdepth: 2
   :caption: Reference
   :hidden:

   changelog

Current version is |release|.

.. thumbnail:: /_static/screenshot-themes.png
   :alt: The Ænglisc Toolkit main window, showing both the light and dark themes.
   :title: The Ænglisc Toolkit main window

   The Ænglisc Toolkit main window, showing both the light and dark themes.

``Ænglisc Toolkit`` is a desktop application for translating Old English /
Anglo-Saxon source material to Modern English and persisting the original text
and translation to a local database.  It is built for scholars first: preserve
philological signal in the original text, and allow the user to annotate words
and idioms with their:

- Root word
- Modern English definition
- Part of speech
- Parameters of the part of speech (e.g. gender, number, case, etc.)

And use that to write an inline Modern English translation of the original text.

Getting Started
---------------

1. **Installation**: :doc:`/overview/installation` (macOS ``.dmg``, or
   source + ``uv``; Python 3.13+)
2. **Quick Start**: :doc:`/overview/quickstart`
3. **Working on translation projects**: :doc:`/overview/projects`
4. **Annotation**: :doc:`/overview/annotation`
5. **Presets**: :doc:`/overview/presets`
6. **Remembered annotations**: :doc:`/overview/remembered_annotations`
7. **Translation and export**: :doc:`/overview/translation`
8. **Backups**: :doc:`/overview/backups`
9. **Updating**: :doc:`/overview/updating`
10. **Domain language**: :doc:`/overview/domain_language`
11. **FAQ**: :doc:`/overview/faq`

For developers, see :doc:`/runbook/contributing` and
:doc:`/runbook/coding_standards`.

Requirements
------------

- Python **3.13** or later