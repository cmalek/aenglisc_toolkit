Installation
============

There are two ways to get ``Ænglisc Toolkit`` running: install the packaged
application (recommended for translators and students), or run it from
source (for contributors and developers).

.. note::

   **Platform availability:** Today ``Ænglisc Toolkit`` is only built for
   **macOS** (Apple Silicon and Intel). Windows and Linux builds are not
   available yet, but are planned for a future release. Until then,
   Windows/Linux users can run the app from source — see
   :ref:`installation-from-source` below.

Installing the packaged app (macOS)
------------------------------------

1. Download the latest ``.dmg`` from the
   `Releases page <https://github.com/cmalek/aenglisc_toolkit/releases>`_.
2. Open the downloaded ``.dmg`` file.
3. Drag **Ænglisc Toolkit** into your **Applications** folder.
4. Open **Applications** and double-click **Ænglisc Toolkit** to launch it.

.. note::

   The first time you open the app, macOS Gatekeeper may warn that it's
   from an unidentified developer, since the app isn't notarized through
   the Mac App Store. Right-click (or Control-click) the app and choose
   **Open**, then confirm in the dialog that appears. You only need to do
   this once.

That's it — no Python, ``git``, or command line required for this path. See
:doc:`/overview/quickstart` to start your first project.

.. _installation-from-source:

Installing from source (contributors and developers)
-------------------------------------------------------

Use this path if you want to modify the app, run the test suite, or build
your own packaged app (see :doc:`/runbook/packaging`). It's also currently
the only way to run ``Ænglisc Toolkit`` on Windows or Linux.

Prerequisites
~~~~~~~~~~~~~~

- Python **3.13** or later (matches ``requires-python`` in ``pyproject.toml``)
- `uv <https://docs.astral.sh/uv/>`_ — installs Python packages and manages
  an isolated Python environment for this project
- ``git`` — used to download (``clone``) the project's source code

If you have never used a command-line terminal before, see
:ref:`new-to-the-command-line` below before continuing.

Clone and run
~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/cmalek/aenglisc_toolkit.git
   cd aenglisc_toolkit
   # Install uv if needed: https://docs.astral.sh/uv/getting-started/installation/
   uv sync
   source .venv/bin/activate
   python -m oeapp.main

What each line does:

1. ``git clone ...`` downloads a copy of the project's source code into a
   new ``aenglisc_toolkit`` folder.
2. ``cd aenglisc_toolkit`` moves your terminal into that folder, so the
   following commands run against these project files.
3. ``uv sync`` creates an isolated Python environment (a folder named
   ``.venv``) containing exactly the Python packages this project needs,
   without affecting any other Python software on your computer.
4. ``source .venv/bin/activate`` switches your terminal to use that
   isolated environment. You need to run this line again every time you
   open a new terminal window to work with the project.
5. ``python -m oeapp.main`` launches the application.

If you're working on the project day-to-day, ``make dev`` does the same
thing plus rebuilds the in-app help content if it's out of date.

.. _new-to-the-command-line:

New to the command line?
~~~~~~~~~~~~~~~~~~~~~~~~~~

- A **terminal** is a text-based window for typing commands instead of
  clicking icons. On macOS, open ``Terminal.app``.
- Type each ``code-block`` line above exactly as written, then press
  Enter. Do not type the ``$`` or ``#`` characters some tutorials show —
  they are not part of the command.
- A **virtual environment** (``.venv``) is a private, disposable copy of
  Python's package installer scoped to this one project, so installing
  this project's dependencies never conflicts with other software on your
  machine.

Next steps
----------

- :doc:`/overview/quickstart` — create your first project
- :doc:`/runbook/packaging` — build your own standalone app
