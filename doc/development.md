
# Development

There is a mailing group to receive your inputs and questions: MotorControl@microchip.com

## Contribution
Contribute to source code, documentation, examples and report issues: https://github.com/X2Cscope/pyx2cscope

If you want to contribute to the project, please follow these steps:

1. Fork the pyX2Cscope repository.
2. Create a new branch for your changes.
3. Make the necessary changes and commit them. 
4. Push your changes to your forked repository. 
5. Open a pull request on the main pyX2Cscope repository, describing your changes.

We appreciate your contribution!

## Set-up the dev system

Create virtual envrionment with make venv

```bash
git clone https://github.com/X2Cscope/pyx2cscope.git
cd pyx2cscope
python -m venv .venv

#Windows
.venv\Scripts\activate

#linux
source .venv\bin\activate
```

## Installing dev requirements

```bash
pip install -r requirements.txt
pip install -r quality.txt
```

## Running tests

### ruff syntax check
```bash
ruff check .
```

### pytest
```bash
pytest
```

## Building docs
```bash
sphinx-build -M html doc build --keep-going  
```

## Creating executables
```bash
pyinstaller --noconfirm .\pyx2cscope_win.spec 
```
