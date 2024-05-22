![PyVM Logo](https://alextremblay.github.io/pyvm/logo.png)

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
- Can cache and run python installations without altering your PATH
- Can bootstrap and run pipx commands without needing to install any pipx or python version beforehand

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

## I want to run a python script without installing anything in my PATH (including pyvm)

This works too! 

Assuming you have a script called `myscript.py`, simply download pyvm to your current directory and run it:

```console
$ curl -sSfLo ./pyvm alextremblay.github.io/pyvm/pyvm.py && chmod +x ./pyvm

$ ./pyvm run 3.12 myscript.py
```


## I want to run a script that has dependencies, installing nothing other than pyvm

Let's say you have a script called `myscript.py`, and it depends on external PYPI packages `requests` and `rich`

you want to be able to run this script as a shell script/command and have it bootstrap its preferred python version (eg 3.11) AND all of its dependencies

That's a tall order! but with PyVM installed, it's possible!

Add this code block to the top of your script:

```sh
#!/usr/bin/env -S pyvm pipx 3.11 run --path

# /// script
# dependencies = [
#   "requests",
#   "rich",
# ]
# ///
```

Then make your script executable:

```console
$ chmod +x ./myscript.py
```

and run it!

```console
$ ./myscript.py
```

## I want to share a script with colleagues that requires NO pre-installed dependencies (even on PyVM)

You wrote a script that requires a specific version of python, specific dependencies/libraries installed,

and you want to be able to send your script to friends and colleagues such that they can execute your script and have it bootstrap all of its own dependencies, without having to install any other software before running your script, not even PyVM itself...

Well, this will look weird, but it works! and it should work on every POSIX-compliant python-build-standalone-compatible UNIX OS

`example.py`:
```python
#!/bin/bash
""":"
set -euo pipefail

PYTHON_VERSION="3.12"

HERE="$( dirname -- "$( readlink -f -- "$0"; )"; )"
PYVM="$HERE/pyvm"
if [ ! -f "$PYVM" ]; then

  # define a function which selects curl or wget based on availability
  download() {
      if command -v curl &> /dev/null; then
          curl -s -L -o $1 $2
      elif command -v wget &> /dev/null; then
          wget -q -O $1 $2
      else
          echo "Neither curl nor wget found. Please install one of these packages."
          exit 1
      fi
  }

  echo "Bootstrapping PyVM..."
  download $PYVM alextremblay.github.io/pyvm/pyvm.py
  chmod +x $PYVM

fi

exec "$PYVM" pipx $PYTHON_VERSION run --path "$0" "$@"
"""

# /// script
# dependencies = [
#   "requests",
#   "rich",
# ]
# ///


import requests
from rich import print

print(requests.get("https://httpbin.org").text)
```

You set your preferred python version with the shell variable on line 5, you set your dependencies within the `# /// script` comment block, and your python code goes in after the `# ///` at the end of the comment block

# Command Line Interface

```console
$ pyvm -h
usage: pyvm [-h] {list,install,uninstall,update,run,pipx} ...

Python Version Manager

This tool is designed to download and install python versions from the 
https://github.com/indygreg/python-build-standalone project into /home/atremblay/.pyvm
and add versioned executables (ie `python3.12` for python 3.12) into a directory on the PATH.

Environment Variables:
    PYVM_HOME: The directory to install python versions into. Defaults to $HOME/.pyvm
    PYVM_BIN: The directory to install versioned executables into. Defaults to $HOME/.local/bin
    PYVM_PBS_RELEASE: The release of python-build-standalone to target. Defaults to 'latest', can be set to a release name (eg '20240224')
    PYVM_PIPX_RELEASE: The release of pipx to target. Defaults to 'latest', can be set to a release name (eg '1.5.0')
    PYVM_PIPX_DEFAULT_PYTHON_VERSION: The default python version to use when installing pipx onto your PATH. Defaults to '3.12'

positional arguments:
  {list,install,uninstall,update,run,pipx}
    list                List installed python versions
    install             Install a python version
    uninstall           Uninstall a python version
    update              Update all installed python versions
    run                 Run a python version
    pipx                Run pipx

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

- a `--global` flag which will set `$PYVM_HOME` default value to `/opt/pyvm` and `$PYVM_BIN` to `/usr/local/bin`
- test coverage >=80%
- windows support
- musl support
- an install script for people who think copy-pasting 3 lines into their terminal is 2 too many :P

# contributing
Contributions are more than welcome! The design of pyvm is deliberately simple. Feel free to fork it, vendor it, modify it as you please
If you make an improvement that you think others might like, please feel free to submit a PR, I'd be more than happy to work with you on it :)
