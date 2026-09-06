.. _runbook__contributing:

Contributing
============

Instructions for contributors
-----------------------------

Workflow is pretty straightforward:

1. Fork the repository.
2. Checkout your fork: ``git clone https://github.com/your-username/wordwending.git``
3. Setup your machine with the required development environment
4. Make your changes, adding or updating tests as appropriate.
5. Update the Sphinx documentation to reflect your changes.
6. ``cd doc; make clean && make html; open build/html/index.html``.  Ensure the docs build without crashing and then review the docs for accuracy.
7. Commit your changes into master.
8. Create a pull request at `<https://github.com/cmalek/wordwending/pulls>`_ and wait for it to be reviewed and merged.


Setting up your development environment
---------------------------------------

.. code-block:: shell

    $ curl -fsSL https://astral.sh/uv/install | sh
    $ uv venv
    $ uv sync --dev

Python Conventions for this project
-----------------------------------

Read :doc:`coding_standards` in its entirety to see the coding conventions for this project.


Managing dependencies
---------------------

- Use ``uv`` for package management.
- The ``uv`` configuration is in ``pyproject.toml``.
- Use ``uv sync --dev`` to install the development dependencies.
- Use ``uv add <package>`` to add a main dependency package to the project.
- Use ``uv add --group=test <package>`` to add a testing dependency package to the project.
- Use ``uv add --group=docs <package>`` to add a documentation dependency package to the project.


Testing
-------

We use ``pytest`` to run the tests.  Add tests for any new functionality you add to the ``tests/`` folder.  To run the tests, use the following command:

.. code-block:: shell

    $ pytest -v tests/


Updating the documentation
--------------------------

As you work on the app, put some effort into making the Sphinx docs build
cleanly and be accurate.

doc/source/index.rst
^^^^^^^^^^^^^^^^^^^^

* Check the "Overview" section and maybe update if you've added some big new
  features
* Check the "Important People" section and update as appropriate

doc/source/changelog.rst
^^^^^^^^^^^^^^^^^^^^^^^^

* Add a section for a new version
* Add a subsection for each change you made in that version.  Use these subsection names:

    * Bugfixes
    * Enhancements
    * Documentation

  and put your changes under the appropriate heading.

Example:

.. code-block:: rst

    .. _changelog__v0.1.0:

    0.1.0 (2025-01-01)
    ------------------

    Enhancements
    ^^^^^^^^^^^^

    - Add a new ``my_function2`` function.

    Bugfixes
    ^^^^^^^^

    - Fix a bug in the ``my_function`` function.

    Documentation
    ^^^^^^^^^^^^^

    - Documented how to use submit a pull request.

autodoc
^^^^^^^

Please try to add appropriate documentation to your classes, methods and
attributes as docstrings, add them if appropriate to files in
``doc/source/api/``

etc.
^^^^

Review the other files to see if they need updating.

Then build the docs and look at them:

.. code-block:: shell

    $ cd doc
    $ make html
    $ open build/html/index.html

If you can build the docs with no critical errors and the docs seem to look ok
when you look through all the HTML pages, that's good enough at this point.