import logging

import pytest

import pyvm

@pytest.fixture()
def fakefs(tmp_path, mocker):
    "A fake filesystem for testing"
    PYVM_HOME = tmp_path / ".pyvm"
    PYVM_HOME.mkdir()
    mocker.patch("pyvm.PYVM_HOME", PYVM_HOME)
    PYVM_BIN = PYVM_HOME / "bin"
    PYVM_BIN.mkdir()
    mocker.patch("pyvm.PYVM_BIN", PYVM_BIN)
    return PYVM_HOME, PYVM_BIN

def test_install(fakefs, caplog):
    "`pyvm install 3.11` should install and symlink python 3.11"
    PYVM_HOME, PYVM_BIN = fakefs
    
    res = pyvm.install_version("3.11")

    # since our fake PYVM_BIN folder isn't on the PATH, pyvm should print a warning to stderr
    # reminding user to add it to their PATH
    stderr = caplog.text
    assert f"Please add {PYVM_BIN} to your PATH" in stderr

    assert res == PYVM_HOME / "3.11/bin/python3.11"

    # check that the symlink was created
    assert (PYVM_BIN / "python3.11").is_symlink()
    assert (PYVM_BIN / "python3.11").resolve() == res

def test_idempotency(fakefs, caplog):
    "`pyvm install 3.11` should only install once, and then use it from cache"
    caplog.set_level(logging.INFO)
    
    pyvm.install_version("3.11")
    assert "Installing python 3.11" in caplog.text

    caplog.clear()
    pyvm.install_version("3.11")
    assert "Python version 3.11 is already installed" in caplog.text
    assert "Installing python 3.11" not in caplog.text



