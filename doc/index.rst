

.. image:: images/pyx2cscope_logo.png
   :width: 180
   :alt: pyx2cscope
   :align: left

The pyx2cscope Python package communicates with X2Cscope enabled firmwares running on Microchip microcontrollers.
This comprehensive package offers developers a powerful toolkit for embedded software development, 
combining real-time debugging capabilities with advanced data visualization features directly within the Python environment.
pyx2cscope is using lnet protocol to communicate with the embedded hardware via different communication interfaces like UART, CAN, LIN, USB, TCP/IP, etc.

Installation
--------------------------------------

Create a virtual environment and install pyx2cscope using the following commands:

.. code-block:: python

   python -m venv .venv
   source .venv/bin/activate
   pip install pyx2cscope

Start GUI example
--------------------------------------

.. code-block:: bash
   
   python -m pyx2cscope

Simplest scripting example
--------------------------------------

.. literalinclude:: ../pyx2cscope/examples/simplest.py
    :language: python
    :linenos:


.. toctree::
   :maxdepth: 2
   :caption: Contents:


   introduction
   how_to
   HW_Support
   example

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



