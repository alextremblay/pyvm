![PyVM Logo](logo.png)

# PyVM
dead-simple python version manager powered by [python-build-standalone](https://github.com/indygreg/python-build-standalone)

# Installation

```console
mkdir -p ~/.local/bin
wget -o ~/.local/bin/pyvm https://raw.githubusercontent.com/alextremblay/pyvm/main/pyvm

echo 'export PATH="$PATH:~/.local/bin"' >> ~/.bashrc
```

# features
This project provides a single-file executable `pyvm` that can be installed anywhere in a user's PATH
You don't need to have any version of python installed in order to use it. the only thing this script needs
in order to bootstrap itself is either `curl` or `wget`

## install python
the `pyvm` script is able to install and manage multiple portable python installations sourced from the amazing [PBS](https://github.com/indygreg/python-build-standalone) project
These python installations are isolated from any version of python that may already be installed on your system. They are installed into `~/.pyvm` by default, but this location can be changed by setting the `$PYVM_HOME` environment variable
Every installed version of python gets symlinked into a folder on your PATH. By default, these symlinks are installed into `~/.local/bin`, but this location can be changed by setting the `$PYVM_BIN` environment variable

For example, the command `pyvm install 3.11` will install python 3.11 into `~/.pyvm/3.11`, and `~/.local/bin/python3.11` will be symlinked to `~/.pyvm/3.11/bin/python3.11`

## run python
the command `pyvm run 3.11` can install (if not already installed) python 3.11 and immediately execute it. This allows pyvm to be used as a script's [shebang](https://linuxhandbook.com/shebang/) interpreter. This allows python script writers to define the version of python their script needs, and share that script with ease. Anyone can then run that script without needing to have that specific python version installed (or any version really), as the only thing they'll need to run that script is `pyvm`

Example:
```python
#!/usr/bin/env -S pyvm run 3.11
import sys
print(sys.executable)
```

# compatability
`pyvm` has been tested in linux (ubuntu x86_64) and macos (macOS 13.6 aarch64), but should theoretically work in any linux x86_64 or aarch64 distribution (as long as `curl` or `wget` are installed), and any version of macOS

# stretch goals
- ability to upgrade python installations when new releases of https://github.com/indygreg/python-build-standalone come out
- a `--global` flag which will set `$PYVM_HOME` default value to `/opt/pyvm` and `$PYVM_BIN` to `/usr/local/bin`
- a proper test suite
- windows support
- musl support

# contributing
Contributions are more than welcome! The design of pyvm is deliberately simple. Feel free to fork it, vendor it, modify it as you please
If you make an improvement that you think others might like, please feel free to submit a PR, I'd be more than happy to work with you on it :)
