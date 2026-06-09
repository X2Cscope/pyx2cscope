VSCode Integration
==================

If you develop firmware with MPLAB X and the MPLAB VSCode extension, you can
add a task to ``.vscode/tasks.json`` in your project that launches
pyX2Cscope automatically after a build or flash, pointing directly at the
generated ELF file.

tasks.json example
------------------

Create or edit ``.vscode/tasks.json`` in your firmware project:

**Single-folder workspace** — use ``${workspaceFolder}`` when the workspace
contains only one project:

.. code-block:: json

   {
       "version": "2.0.0",
       "tasks": [
           {
               "label": "Run pyX2Cscope",
               "type": "process",
               "command": "${workspaceFolder}/../pyX2Cscope/pyX2Cscope.exe",
               "args": [
                   "-p", "AUTO",
                   "-e", "${workspaceFolder}/out/default.elf"
               ],
               "options": {
                   "cwd": "${workspaceFolder}/../pyX2Cscope"
               },
               "presentation": {
                   "reveal": "always",
                   "panel": "new"
               },
               "problemMatcher": []
           }
       ]
   }

**Multi-folder workspace** — when the ``.code-workspace`` file contains
several folders (e.g. ``MY_Project1``, ``MY_Project2``), use
``${workspaceFolder:MY_Project1}`` to refer to a specific folder by name:

.. code-block:: json

   {
       "version": "2.0.0",
       "tasks": [
           {
               "label": "Run pyX2Cscope (MY_Project1)",
               "type": "process",
               "command": "${workspaceFolder:MY_Project1}/../pyX2Cscope/pyX2Cscope.exe",
               "args": [
                   "-p", "AUTO",
                   "-e", "${workspaceFolder:MY_Project1}/out/MY_Project1/default.elf"
               ],
               "options": {
                   "cwd": "${workspaceFolder:MY_Project1}/../pyX2Cscope"
               },
               "presentation": {
                   "reveal": "always",
                   "panel": "new"
               },
               "problemMatcher": []
           }
       ]
   }

Adapt the ``command`` path to where ``pyX2Cscope.exe`` is located on your
machine, and update the ``-e`` path to match your project's output ELF.
For multi-folder workspaces, replace ``MY_Project1`` with the folder name
as it appears in your ``.code-workspace`` file.

To launch the Web GUI instead of the Qt GUI, add ``"-w"`` to the ``args``
list:

.. code-block:: json

   "args": ["-p", "AUTO", "-e", "${workspaceFolder:MY_Project1}/out/MY_Project1/default.elf", "-w"]

Running the task
----------------

Once configured, run it from **Terminal → Run Task → Run pyX2Cscope** (or
bind it to a keyboard shortcut).  pyX2Cscope will open with the correct ELF
loaded and attempt to connect to the device on the first available port —
no manual input needed.

.. tip::

   Combine this with a build or flash task using ``dependsOn`` so that
   pyX2Cscope launches automatically after every successful firmware flash:

   .. code-block:: json

      {
          "label": "Flash and Run pyX2Cscope",
          "dependsOn": ["Flash Device", "Run pyX2Cscope"],
          "dependsOrder": "sequence",
          "problemMatcher": []
      }
