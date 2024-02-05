# Python Package for Tool/Model Development

This package will contain all the data analysis, model development, and other utilities developed as part of the BHF HBR project.

## Package Installation

For now, the dependencies are stored in `requirements.txt` (they will eventually be moved into the package itself). To install the package on Windows, using VS Code:

1. Install Python 3 (>= 3.11)
2. Create a new virtual environment (`Ctrl-Shift-P`, run `Python: Create Environment...`, pick `Venv`). Ensure it is activated
3. In the VS Code terminal, install from the requirements file using `pip install -r requirements.txt`
4. To install the package, run `pip install .` (If you want to make edits, using `pip install -e .`)

## Development Instructions

Do all installation/development work inside a virtual environment:

* On Linux, create and activate it using `python3 -m venv venv` and `. venv/bin/activate`
* On Windows (in VS Code), type Ctrl-Shift-P, run `Python: Create Environment...`, pick `Venv`, and ensure that it is activated (look for something like `3.11.4 ('.venv': venv)` in the bottom right corner of your screen). It may not activate automatically unless you open a python file in the IDE first.

Currently, dependencies are not yet stored in the package, but the state of the development environment is stored in `requirements.txt` (generated using `pip freeze --all > requirements.txt`). To install these dependencies, run:

```bash
pip install -r requirements.txt
```

You can install this package in editable mode (which will make the installation track live edits to this folder) by changing to this folder and running

```bash
pip install -e .
```

You should now be able to run the tests and doctests using:

```bash
pytest --doctest-modules
```

You can generate the documentation for viewing live using:

```bash
mkdocs serve
```

### Further Development Notes

Ordinarily, running `pip install -e .` will automatically fetch dependencies from PyPi. However, if you are unable to access PyPI due to networking limitations (on computer `A`), but are able to move a (~ 250 MiB) file from a computer (`B`) which does have access to PyPI, then you can perform the steps below to install the dependencies and this package on `A`.

These instructions were tested on Windows using VS Code virtual environments. Everything should work the same on Linux, except that the Python 3 executable is typically called `python3` (when creating virtual environments). Both computers `A` and `B` were set up with the same version of Python (3.11.4).

1. On `B`
    1. Create a new virtual environment using `python -m venv .venv`. Activate it in VS code (on Linux, or if you have bash, run `source .venv/bin/activate`).
    2. Using any process (manual pip install, pip install from requirements, or automatic installation of dependencies), install all the packages you need in the virtual environment.
    3. Run `pip freeze --all > requirements.txt`
    4. Download all the package wheels into a folder `packages` using `pip download -r requirements.txt -d packages`
    5. Compress the `packages` folder using any tool; e.g. to produce `packages.7z`
2. Move the `packages.7z` folder, and the `requirements.txt` file, from `B` to `A`
3. On `A`
    1. Extract






1. First, create a virtual environment and manually install the requirements listed in `../prototypes/requirements.txt`.
2. Run `pip install -e .`. Since the dependencies are already installed, there will be no need to query PyPi.



# This is a better way:
#
# -1: Make a venv and install all the packages you need
# 0. pip freeze --all > prototypes/requirements.txt
# 1. pip download -r requirements.txt -d packages
# 1b. Download pip and wheel wheels and add them to 
#     the packages folder
# 2. Zip the packages folder and transfer to other computer
# 3. On computer with PyPi access, download latest pip
#    wheel, and move to other computer
# 4. On new computer, run python -m venv .venv (note: not python3;
#    on Windows, Python 3 executable is called python)
# 5. Run this line: python -m pip install --no-index --find-links packages -r prototypes/requirements.txt
#    The key points here are --no-index (do not use PyPi) and --find-links (path to the wheels).
# 