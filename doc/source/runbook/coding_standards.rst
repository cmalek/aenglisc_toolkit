Python coding standards
=======================

Type hinting
------------

- We expect you to use type hints for all functions, methods, classes, and variables.  You may skip type hints for variables that are not used outside of the function, method, class, or module.
- Use python 3.10+ sytle type hints for all functions and classes.
- For example, this means do not use ``Dict``, ``List``, ``Tuple``, ``Type`` or ``Optional``; use ``dict``, ``list``, ``tuple``, ``type`` or ``<type> | None`` instead.  This is not an exhaustive list.
- Be specific for collection types.  Try not to use the plain ``dict`` or ``list`` types; use ``dict[<key_type>, <value_type>]`` or ``list[<subtype>]`` instead.
- For complicated types, add a type alias to ``<project>/types.py`` and use that alias instead.

**Example:**

.. code-block:: python

    def my_function(arg1: str, arg2: list[str], kwarg1: str = "default", kwarg2: int = 10) -> str:
        # contents of function


Documentation
-------------

- Document all functions and classes using docstrings in `Sphinx Napoleon format <https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html>`_.
- When documenting methods, put positional arguments in the ``Args:`` section, keyword arguments in the ``Keyword Arguments:`` section, include any exceptions raised in the ``Raises:`` section, and of course include a ``Returns:`` section.  Leave a blank line after the ``Returns:`` section so ``ruff`` doesn't complain about the docstring.
- Use ``#:`` notation for type hints on attributes, variables or constants.

**Examples:**

.. code-block:: python

    @dataclass
    class Person:
        """
        A dataclass representing a person.
        """"
        #: The name of the person
        name: str
        #: The age of the person
        age: int

    def my_function(arg1: str, arg2: int, kwarg1: str = "default", kwarg2: int = 10) -> str:
        """
        My function description

        Args:
            arg1: The first argument
            arg2: The second argument

        Keyword Arguments:
            kwarg1: The first keyword argument
            kwarg2: The second keyword argument

        Raises:
            ValueError: If kwarg1 is not 'foo' or 'bar'
            ValueError: If kwarg2 is less than 0

        Returns:
            The result of the function

        """
        if kwarg1 not in ['foo', 'bar']:
            raise ValueError("kwarg1 must be 'foo' or 'bar'")
        if kwarg2 < 0:
            raise ValueError("kwarg2 must be greater than 0")

        return f"{arg1} {arg2}"

Structure
---------

- Implement proper separation of concerns.  For example, do not put all your code in a single file or class.  Put related code in the same file or class.
- Try to limit the number of lines of code in a function or method to 60 lines.  If it is longer, break it up into smaller functions if this is a function, or methods if this is a method.
- **Do not commit code that has linting errors.**  Your pull request will be rejected if it has linting errors.
- in ``try:`` blocks, include specific exceptions that are expected to be raised; do not use a catch-all ``except Exception`` block unless you have no choice.  **Your pull request will be rejected if you do not have good reasons for not doing this.**
- Put any custom exceptions into the top-level ``exc.py`` module.
- Try to avoid using basic dictionaries for any return value or method parameter that requrie simple key-value store type data.  Use ``@dataclass``, ``pydantic`` models, or ``TypedDict`` instead.
- If the model is user facing (they will consume it in their own code, or we will consume it in other major sections of the code), use ``pydantic`` models.  If the model is internal only, use ``@dataclass`` or ``TypedDict``.

**Not this:**

.. code-block:: python

    def my_function(arg1: str, arg2: int, kwarg1: str = "default", kwarg2: int = 10) -> dict[str, str]:
        return {
            "arg1": arg1,
            "arg2": arg2,
        }

**Do this:**

.. code-block:: python

    from pydantic import BaseModel, AnyUrl

    class Person(BaseModel):
        """"
        Describes an AWS service, e.g. ``ecs``
        """"

        #: The person's name
        name: str
        #: The person's age
        age: int

**Or this:**

.. code-block:: python

    from dataclasses import dataclass

    @dataclass
    class Person:
        """"
        Describes a person
        """"

        #: The person's name
        name: str
        #: The person's age
        age: int

**Or this:**

.. code-block:: python

    from typing import TypedDict

    class Person(TypedDict):
        """"
        Describes a person
        """"

        #: The person's name
        name: str
        #: The person's age
        age: int


Linting
-------

- Use ``ruff`` to lint the code, according to the settings in ``pyproject.toml``. Try to fix the lint errors by either fixing the code or adding a ``# noqa: <rule>`` comment to the line.
- Use ``mypy`` to type check the code, according to the settings in ``pyproject.toml``.  For any imported modules that lack type hints, add a section like this to the appropriate place in the ``pyproject.toml`` file:

To silence mypy errors about missing type hints in a dependency, you can add the following to your ``pyproject.toml`` file:

.. code-block:: toml

    [tool.mypy.overrides]
    module = "<module_name>.*"
    ignore_missing_imports = true

- **Your pull request will be rejected if it has linting problems.**
