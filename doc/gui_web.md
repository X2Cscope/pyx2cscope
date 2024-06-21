# GUI Web

The Web Graphic User Interface is implemented unsing Flask, bootstrap 4, jquery and chart.js
It is also an example on how to build a custom GUI using pyX2Cscope. This interface allows
you to use multiple windows or even access functions from smart-devices. The server runs
by default on your local machine and does not allow external access. 
The server has default port 5000 and will be accessible on http://localhost:5000

## Starting the Web GUI

The Web GUI start with following command below:

```
python -m pyx2cscope -w
``` 

To open the server for external access include the argument --host 0.0.0.0

```
python -m pyx2cscope -w --host 0.0.0.0
``` 

Additional information you may find on the API documentation.

