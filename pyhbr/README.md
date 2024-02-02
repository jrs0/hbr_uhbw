# Python Package for Tool/Model Development

This package will contain all the data analysis, model development, and other utilities developed as part of the BHF HBR project.

Do all installation/development work inside a virtual environment:

* On Linux, create and activate it using `python3 -m venv venv` and `. venv/bin/activate`
* On Windows (in VS Code), type Ctrl-Shift-P, run `Python: Create Environment...`, pick `Venv`, and ensure that it is activated (look for something like `3.11.4 ('.venv': venv)` in the bottom right corner of your screen). It may not activate automatically unless you open a python file in the IDE first.

You can install this package in editable mode (which will make the installation track live edits to this folder) by changing to this folder and running

```bash
pip install -e .
```

You should now 

## Further Development Notes

Ordinarily, running `pip install -e .` will automatically fetch dependencies from PyPi. However, if you are unable to access PyPi due to networking limitations, but are able to install packages in some other manual way, then you can still install this package:

1. First, create a virtual environment and manually install the requirements listed in `../prototypes/requirements.txt`.
2. Run `pip install -e .`. Since the dependencies are already installed, there will be no need to query PyPi.
