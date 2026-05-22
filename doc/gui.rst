Graphical User Interfaces
=========================

pyX2Cscope ships with two ready-to-use graphical interfaces: a **Qt desktop
application** and a **Web interface** built on Flask.  Both expose the same
core functionality — connecting to a target, reading and writing variables,
recording scope data, and running Python scripts — but they are designed for
different use cases and deployment scenarios.

.. list-table::
   :widths: 20 40 40
   :header-rows: 1

   * -
     - Qt GUI
     - Web GUI
   * - **Best for**
     - Desktop / laptop, single user
     - Remote access, shared setups, headless machines
   * - **How to start**
     - ``python -m pyx2cscope``
     - ``python -m pyx2cscope -w``
   * - **Access**
     - Native window on the local machine
     - Any browser, including phones and tablets on the same network
   * - **Scripting**
     - Built-in editor, output in a dedicated tab
     - Browser-based editor, output streamed via WebSocket
   * - **Standalone exe**
     - ``pyX2Cscope.exe`` (default)
     - ``pyX2Cscope.exe -w``

Both interfaces are also examples of how to build your own custom GUI on top
of the pyX2Cscope API — the source code is part of the package and can be
used as a starting point.

See the following sections for details:

.. toctree::
   :maxdepth: 1

   cli
   gui_qt
   gui_web
   scripting_scripts
   vscode
