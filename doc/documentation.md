# Building the documentation

In a terminal run the following commands:

```
cd doc
make clean
sphinx-apidoc -o source ../pyx2cscope
make html
```