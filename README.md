![PyVM Logo](logo.png)

# PyVM
dead-simple python version manager powered by [python-build-standalone](https://github.com/indygreg/python-build-standalone)

# Installation

## If you already have python3

```console
python3 -m pip install pyvm-cli

pyvm install 3.12 # for example
```



```console
mkdir -p ~/.local/bin
wget -o ~/.local/bin/pyvm https://raw.githubusercontent.com/alextremblay/pyvm/main/pyvm

echo 'export PATH="$PATH:~/.local/bin"' >> ~/.bashrc
```

# early days
This project is still in its infancy, but its goals are thus:

provide a single-file executable `pyvm` that can be installed into a user's PATH

make it so that `pyvm install 3.8` will download cpython 3.8.x from https://github.com/indygreg/python-build-standalone/releases/latest
into `${PYVM_HOME:-$HOME/.pyvm}/3.8` and symlink `${PYVM_HOME:-$HOME/.pyvm}/3.8/bin/python3.8` into `${PYVM_BIN:-$HOME/.local/bin}/3.8`
and `pyvm install all` will do the same for all available versions of python

## stretch goals
- ability to upgrade python installations when new releases of https://github.com/indygreg/python-build-standalone come out
- a `--global` flag which will set `$PYVM_HOME` default value to `/opt/pyvm` and `$PYVM_BIN` to `/usr/local/bin`
- windows support
- MacOS / homebrew support
- musl support

# contributing
Contributions are more than welcome! The design of pyvm is deliberately simple. Feel free to fork it, vendor it, modify it as you please
If you make an improvement that you think others might like, please feel free to submit a PR, I'd be more than happy to work with you on it :)
