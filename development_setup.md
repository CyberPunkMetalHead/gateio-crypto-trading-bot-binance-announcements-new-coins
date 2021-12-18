## 1. Create venv (recommended to use python>=3.8, check with `python --version`)

    python3 -m venv env

## 2 Activate venv

    Linux:
    source env/bin/activate

    Windows:
    env\Scripts\activate.bat

## 3. Install program requirements

    python -m pip install -r requirements.txt

This contains the requirements for the program itself.

## 4. Install the source code as module

    python -m pip install -e .

This installs the source code as a module so dependencies can be referenced easier.
If you just wanna test/use the bot, you can stop here.

## 5. Install dev requirements

    python -m pip install -r dev_requirements.txt

This is necessary make verifying of the code easier and formats the code automatically to match the coding style.

## 6. Install pre-commit hooks

    pre-commit install

This installs the pre-commit git hooks for the project and makes it possible to run the pre-commit script automatically when committing.

## 7. Run Tests and pre-commit scripts manually
### pre-commit checks
To manually run the pre-commit script:

    pre-commit run --all-files

### Tox
Make sure you enabled the virtual environment.
Tox tests the code for multiple environments (3.8, 3.9) and checks code with flake8 and mypy (only on Python Version 3.8).
To run Tox:

        tox

### PyTest
Make sure you enabled the virtual environment.
PyTest runs the unit tests for the code.
To run PyTest:

        pytest


### Flake8
Make sure you enabled the virtual environment.
Flake8 checks the code for errors and warnings.
To run Flake8:

        flake8 src

### Black
Make sure you enabled the virtual environment.
Black formats the code to match the coding style.
To run Black:

        black src
