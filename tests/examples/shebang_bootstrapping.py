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