# Python Package for Tool/Model Development

This package will contain all the data analysis, model development, and other utilities developed as part of the BHF HBR project.

## Package Installation

The intention is to host `pyhbr` on PyPI. For now, it is available on TestPyPi, and can be installed using:

```bash
pip install -i https://test.pypi.org/simple/ pyhbr
```

Dependency versions have not yet been worked out in detail, so you might encounter problems. For now, the dependencies used in the development environment are stored in `requirements.txt`. (This is a wider set of dependencies than is required for `pyhbr`, and includes the dependencies for all scripts in this repository.)

Instead of using pip, it is possible to install the package on from this git repository. On Windows, using VS Code, follow these steps:

1. Install Python 3 (>= 3.11)
2. Create a new virtual environment (`Ctrl-Shift-P`, run `Python: Create Environment...`, pick `Venv`). Ensure it is activated
3. Clone this repository and change directory to the `pyhbr/` folder.
4. In the VS Code terminal, install from the requirements file using `pip install -r requirements.txt`
5. To install the package, run `pip install .` (If you want to make edits, use `pip install -e .`)

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

### Linux System Dependencies

If you are using Linux, ensure the following packages are installed:

```bash
# For PyQt6
sudo apt-get install libxcb-cursor0
```

### Further Development Notes

Ordinarily, running `pip install -e .` will automatically fetch dependencies from PyPi. However, if you are unable to access PyPI due to networking limitations (on computer `A`), but are able to move a (~ 250 MiB) file from a computer (`B`) which does have access to PyPI, then you can perform the steps below to install the dependencies and this package on `A`.

These instructions were tested on Windows using VS Code virtual environments. Everything should work the same on Linux, except that the Python 3 executable is typically called `python3` (when creating virtual environments). Both computers `A` and `B` were set up with the same version of Python (3.11.4).

1. On `B`
    1. Create a new virtual environment using `python -m venv .venv`. Activate it in VS code (on Linux, or if you have bash, run `source .venv/bin/activate`).
    2. Using any process (manual pip install, pip install from requirements, or automatic installation of dependencies), install all the packages you need in the virtual environment.
    3. Run `pip freeze --all > requirements.txt`
    4. Download all the package wheels into a folder `packages` using 
       ```bash
       pip download -r requirements.txt -d packages
       ```
    5. Compress the `packages` folder using any tool; e.g. to produce `packages.7z`
2. Move the `packages.7z` folder, and the `requirements.txt` file, from `B` to `A`
3. On `A`
    1. Extract `packages.7z` to `packages`
    2. Create a new virtual environment as above
    3. Install all the dependencies from the `packages` folder using 
       ```bash
       python -m pip install --no-index --find-links packages -r requirements.txt
       ```
       The `--no-index` switch disables querying PyPI, and `--find-links` provides a path to the wheels. Note the use of `python -m pip`, which will also allow pip to be upgraded.

It should now be possible to install the `pyhbr` package using `pip install -e .`
