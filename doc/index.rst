.. image:: images/pyx2cscope_logo.png
   :width: 180
   :alt: pyx2cscope
   :align: left

The pyx2cscope Python package communicates with X2Cscope enabled firmwares running on Microchip microcontrollers.
This comprehensive package offers developers a powerful toolkit for embedded software development, 
combining real-time debugging capabilities with advanced data visualization features directly within
the Python environment.
pyx2cscope makes use of lnet protocol to communicate with the embedded hardware via different communication interfaces
like UART, CAN, LIN, USB, TCP/IP, etc.

pyX2Cscope
==========

The pyx2cscope Python package communicates with X2Cscope enabled firmwares running on microcontrollers. Focusing real time control applications like motor control and power conversion.
It allows user to:
* Read - Write variables to the embedded target in runtime
* Record and Plot fast, continuous signals from the target firmware
* Implement Automated Unit Tests (TDD) and HIL tests for embedded development
* Record data in run-time for AI models
* Implement custom user interface, dashboards (QT, Tkinter, Web)

.. image:: images/overview.gif
   :width: 420
   :alt: MCU<->PC
   :align: center


Following you will find specific information about Installation, API, GUIs, and Firmware implementation.
See the section examples to check some of the usages you may get by pyX2Cscope.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   install.rst
   scripting.rst
   gui_qt.md
   gui_web.md
   FW_Support
   example
   development.md

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



