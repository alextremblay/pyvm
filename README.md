![PyVM Logo](logo.png)

# PyVM
dead-simple python version manager powered by [python-build-standalone](https://github.com/indygreg/python-build-standalone)

# Installation

`pyvm` is a single-file self-bootstrapping script, all you need to do to install it is put it somewhere on your $PATH.

```console
mkdir -p ~/.local/bin
wget -o ~/.local/bin/pyvm alextremblay.github.io/pyvm/pyvm.py

echo 'export PATH="$PATH:~/.local/bin"' >> ~/.bashrc
```

`pyvm` will work on any modern-ish Linux/MacOS computer that has either `curl` or `wget` installed.

# features
- Can manage multiple portable python installations sourced from the amazing [PBS](https://github.com/indygreg/python-build-standalone) project
- installs python versions to isolated location, doesn't interfere with or interact with any version of python installed/used by your operating system

# Use Cases

## I want python3.10 and 3.11 on my PATH

```console
pyvm install 3.10
pyvm install 3.11
```

## I have a python script i want to run with Python3.12

Make your script executable and add the following [shebang](https://linuxhandbook.com/shebang/) line to the top of it:

```sh
#!/usr/bin/env pyvm run 3.12
```

## I want to use pyvm as a library to manage python distributions in my own application

Install pyvm as a python library from PYPI

```console
$ pip install python-version-manager
```

and use it in your application like so:

```python
import pathlib
import subprocess

import pyvm

with pyvm.override():
    pyvm.PYVM_HOME = pathlib.Path('/your/preferred/python/installation/path')
    pyvm.PYVM_BIN = pathlib.Path('/your/preferred/PATH/directory')

    py311_binary = pyvm.install_version("3.11")
    assert 'Python 3.11' in subprocess.run([py311_binary, "--version"], capture_output=True).stdout.decode()
```

# Command Line Interface

```console
$ pyvm -h
usage: pyvm [-h] {list,install,uninstall,update,run} ...

Python Version Manager

This tool is designed to download and install python versions from the 
https://github.com/indygreg/python-build-standalone project into /home/atremblay/.pyvm
and add versioned executables (ie `python3.12` for python 3.12) into a directory on the PATH.

Environment Variables:
    PYVM_PBS_RELEASE: The release of python-build-standalone to target. Defaults to 'latest', can be set to a release name (eg '20240224')
    PYVM_HOME: The directory to install python versions into. Defaults to $HOME/.pyvm
    PYVM_BIN: The directory to install versioned executables into. Defaults to $HOME/.local/bin

positional arguments:
  {list,install,uninstall,update,run}
    list                List installed python versions
    install             Install a python version
    uninstall           Uninstall a python version
    update              Update all installed python versions
    run                 Run a python version

options:
  -h, --help            show this help message and exit
```

# Extra Info

These python installations are isolated from any version of python that may already be installed on your system. They are installed into `~/.pyvm` by default, but this location can be changed by setting the `$PYVM_HOME` environment variable
Every installed version of python gets a small versioned shim added into a folder on your PATH. By default, these shims are installed into `~/.local/bin`, but this location can be changed by setting the `$PYVM_BIN` environment variable

For example, the command `pyvm install 3.11` will install python 3.11 into `~/.pyvm/3.11`, and `~/.local/bin/python3.11` will be a shim which executes `~/.pyvm/3.11/bin/python3.11`

## Why a shim, and not a symlink?
A symlink would also work, but only in certain circumstances. with a symlink, the following works: opening a REPL, executing an expression with `python3.11 -c '<expr>'`, running a script with `python3.11 <script>.py`, piping python code into the interpreter like `echo 'print("hello")' | python3.11`, BUT one thing that **doesn't** work is executing a module:
```console
$ python3.12 -m venv test312
Error: Command '['/home/atremblay/pyvm/test312/bin/python3.12', '-m', 'ensurepip', '--upgrade', '--default-pip']' returned non-zero exit status 1.
```
it seems in some cases, portable python fails to find its own lib folder when it's executed through a symlink. manually setting `$PYTHONHOME` to the installed location of the portable python distribution would fix this issue, but that would require a shim anyway.


# Compatibility
`pyvm` has been tested in linux (ubuntu x86_64 14.04+ and fedora 32+) and macos (macOS 13.6 aarch64), but should theoretically work in any linux x86_64 or aarch64 distribution (as long as `curl` or `wget` are installed), and any version of macOS

# Stretch goals
`pyvm` is still a very young project, and there are many features that have yet to be implemented:

- pipx integration (possibly by bootstrapping the pipx pex file into PYVM_HOME)
- a `--global` flag which will set `$PYVM_HOME` default value to `/opt/pyvm` and `$PYVM_BIN` to `/usr/local/bin`
- test coverage >=80%
- windows support
- musl support
- an install script for people who think copy-pasting 3 lines into their terminal is 2 too many :P

# contributing
Contributions are more than welcome! The design of pyvm is deliberately simple. Feel free to fork it, vendor it, modify it as you please
If you make an improvement that you think others might like, please feel free to submit a PR, I'd be more than happy to work with you on it :)
