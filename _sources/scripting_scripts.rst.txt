Running Scripts in the GUI
==========================

Both the Qt and Web interfaces include a built-in scripting tab that lets you
load and execute Python scripts without leaving the application.  Scripts have
access to the live ``x2cscope`` connection and can read/write firmware variables,
collect scope data, and use any Python library installed on the system.

.. contents:: On this page
   :local:
   :depth: 2

How scripts are executed
------------------------

Scripts run inside the application process via Python's ``exec()`` built-in.
Two variables are automatically injected into every script's namespace:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Name
     - Description
   * - ``x2cscope``
     - The active :class:`~pyx2cscope.x2cscope.X2CScope` instance, or ``None``
       if the GUI is not connected to a target.
   * - ``stop_requested``
     - A callable that returns ``True`` when the user clicks the **Stop** button.
       Use it to exit loops gracefully.

A minimal script:

.. code-block:: python

    import time

    while not stop_requested():
        var = x2cscope.get_variable("myVar")
        print(f"Value: {var.get_value()}")
        time.sleep(0.5)

Scripts that work both standalone and inside the GUI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``globals().get()`` to detect whether the script is running inside the GUI
or directly from the command line:

.. code-block:: python

    from pyx2cscope.x2cscope import X2CScope
    from pyx2cscope.utils import get_elf_file_path
    import time

    # Use the injected connection or create a standalone one
    if globals().get("x2cscope") is None:
        x2cscope = X2CScope(port="COM3", elf_file=get_elf_file_path())

    stop_requested = globals().get("stop_requested", lambda: False)

    while not stop_requested():
        var = x2cscope.get_variable("myVar")
        print(var.get_value())
        time.sleep(0.5)

.. note::

   Creating a new ``X2CScope`` connection while the GUI is already connected to
   the same port will cause a conflict.  Always check ``globals().get("x2cscope")``
   before opening your own connection.


Installing extra libraries (standalone executable only)
-------------------------------------------------------

When using the **standalone executable** (``pyX2Cscope.exe``), only the packages
that were bundled at build time are available.  If a script needs an additional
library — for example ``scipy`` or ``pandas`` — it must be installed into the
``libs/`` folder that lives next to the executable.

The ``--install`` flag
^^^^^^^^^^^^^^^^^^^^^^

The executable ships with a built-in installer that uses the **same Python
version** that is embedded in the executable.  This guarantees that binary
packages (C extensions such as ``scipy``, ``numpy``, ``pandas``) are compiled
for the correct interpreter:

.. code-block:: console

   pyX2Cscope.exe --install scipy
   pyX2Cscope.exe --install pandas openpyxl

After the command completes, the packages are immediately available to all
scripts — no rebuild or restart required.

.. note::

   ``--install`` requires that the matching Python version is installed on the
   system (e.g. Python 3.12 if the executable was built with Python 3.12).
   The installer searches common Windows paths automatically.  If it cannot
   find a matching interpreter it will print an error with a download link.

Installing with transitive dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default ``--install`` passes ``--no-deps`` to pip.  This prevents pip from
pulling in packages that are already bundled in the executable (such as
``numpy``), which would otherwise overwrite the bundled version and cause
version-conflict errors.

If a package requires dependencies that are **not** bundled, add
``--with-deps`` to let pip resolve and install them:

.. code-block:: console

   pyX2Cscope.exe --install mypackage --with-deps

Where packages are stored
^^^^^^^^^^^^^^^^^^^^^^^^^^

All user-installed packages go into the ``libs/`` folder next to the
executable:

.. code-block:: text

   pyX2Cscope/
   ├── pyX2Cscope.exe
   ├── libs/
   │   ├── scipy/
   │   ├── pandas/
   │   └── ...
   └── _internal/
       └── ...

The ``libs/`` folder is added to ``sys.path`` automatically when the
executable starts, *after* the bundled packages, so bundled versions always
take priority.

When the executable is not enough
----------------------------------

The standalone executable is convenient but it bundles a fixed set of
packages.  If you need a complex library environment — many extra packages,
specific version combinations, or packages with heavy native dependencies —
the simplest solution is to **install pyX2Cscope directly with pip** into your
own Python environment and run it from there.  This way pip manages all
dependencies normally and every package you install is immediately available
to scripts.

.. code-block:: console

   pip install pyx2cscope
   python -m pyx2cscope -e firmware.elf

Or, to get a specific interface:

.. code-block:: console

   python -m pyx2cscope -e firmware.elf          # Qt GUI (default)
   python -m pyx2cscope -e firmware.elf -w        # Web GUI

With this approach you install extra libraries the normal way:

.. code-block:: console

   pip install scipy pandas

And they are available to scripts immediately, with no version-conflict risk.

.. tip::

   Using a virtual environment (``python -m venv .venv``) keeps your
   pyx2cscope dependencies isolated from other projects on the same machine.

Troubleshooting
---------------

``No module named 'X'`` after installing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Cause:** The package was installed but a stdlib module it depends on is not
bundled in the executable.

**Solution:** This is a known limitation.  Common missing stdlib modules
(``timeit``, ``html.parser``, ``csv``, ``xml``, ``doctest``, …) are pre-listed
in the build spec and bundled by default.  If you encounter one that is not
bundled, please open an issue on the
`pyx2cscope repository <https://github.com/X2Cscope/pyx2cscope/issues>`_ with
the full traceback.

NumPy / binary version conflict
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Symptom:**

.. code-block:: text

   A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x …

**Cause:** pip pulled a newer version of NumPy into ``libs/`` which shadows the
bundled one.

**Solution:** Delete any ``numpy`` folder inside ``libs/`` and reinstall the
offending package using the default ``--no-deps`` flag:

.. code-block:: console

   pyX2Cscope.exe --install scipy

If the package genuinely requires a different NumPy version, contact the
pyx2cscope maintainers to request an updated executable build.

``ERROR: Could not find Python X.Y``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Cause:** The ``--install`` flag needs the matching system Python to invoke
``pip``.  It was not found on ``PATH`` or in the common install directories.

**Solution:** Install the exact Python version shown in the error message from
`python.org <https://www.python.org/downloads/>`_ and re-run the command.

Package installs but script still fails to import it
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check that the package actually landed in ``libs/``:

.. code-block:: console

   dir pyX2Cscope\libs

If the folder is empty or missing the package, re-run ``--install``.  Also
confirm that no error was printed during installation.

Pip dependency resolver warning
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Symptom:**

.. code-block:: text

   ERROR: pip's dependency resolver does not currently take into account all
   the packages that are installed …

**Cause:** This is a non-fatal warning from pip.  It appears because the
bundled packages are not visible to pip when it resolves dependencies.  The
installation still completes and the package will work correctly as long as
the bundled versions satisfy the requirements.
