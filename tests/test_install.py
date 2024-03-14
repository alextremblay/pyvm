import logging
import sys
import pathlib

import pytest

import pyvm

@pytest.mark.end_to_end
def test_install(fakefs, caplog):
    "`pyvm install 3.11` should install and symlink python 3.11"
    PYVM_HOME, PYVM_BIN, _ = fakefs
    
    res = pyvm.install_version("3.11")

    # since our fake PYVM_BIN folder isn't on the PATH, pyvm should print a warning to stderr
    # reminding user to add it to their PATH
    stderr = caplog.text
    assert f"Please add {PYVM_BIN} to your PATH" in stderr

    assert res == PYVM_HOME / "3.11/bin/python3.11"

    # check that the shim was created
    shim = PYVM_BIN / "python3.11"
    assert shim.exists()
    assert str(res) in shim.read_text()


def test_install_unit(fakefs, caplog, mock_fetch):
    "Unit test for `pyvm install`"
    test_install(fakefs, caplog)


@pytest.mark.end_to_end
def test_idempotency(fakefs, caplog):
    "`pyvm install 3.11` should only install once, and then use it from cache"
    caplog.set_level(logging.INFO)
    
    pyvm.install_version("3.11")
    assert "Installing python 3.11" in caplog.text

    caplog.clear()
    pyvm.install_version("3.11")
    assert "Python version 3.11 is already installed" in caplog.text
    assert "Installing python 3.11" not in caplog.text


def test_idempotency_unit(fakefs, caplog, mock_fetch):
    "Unit test for `pyvm install` idempotency"
    test_idempotency(fakefs, caplog)


