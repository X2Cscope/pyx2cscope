Installation
============

Create a virtual environment and install pyx2cscope using the following commands (Windows):

.. code-block:: python

   python -m venv .venv
   .venv\Scripts\activate
   pip install pyx2cscope


It is highly recommended to install python libraries underneath a virtual environment.

Nevertheless, to install at system level, we advise to install it on user area. (Global insallation may not work.) 
Execute the following lines:

.. code-block:: python
   
   pip install --user pyx2cscope

.. code-block:: python

   pip install --upgrade pyx2cscope

In case of unexpected issues executing pyx2cscope try to reinstall manually:

.. code-block:: python
   
   pip uninstall pyx2cscope
   pip cache purge
   pip install --user pyx2cscope 


After install you may check the current pyx2cscope version, in a terminal, run the following command:

.. code-block:: python

   pyx2cscope --version

For help or additional command line options, type:

.. code-block:: bash

   pyx2cscope --help

The log level used by pyX2Cscope is ERROR by default, possible values are
DEBUG, INFO, WARNING, ERROR, and  CRITICAL. To set a different log level start
pyX2Cscope with argument **-l** or **--log-level**

.. code-block:: bash

   pyx2cscope --log-level DEBUG