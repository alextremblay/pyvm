import logging
import subprocess
import os
import sys

import pytest

import pyvm

@pytest.mark.end_to_end
def test_install(fakefs, caplog):
    "`pyvm install 3.11` should install and symlink python 3.11"
    PYVM_HOME, PYVM_BIN, tmp = fakefs
    
    res = pyvm.install_version("3.11")

    # since our fake PYVM_BIN folder isn't on the PATH, pyvm should print a warning to stderr
    # reminding user to add it to their PATH
    stderr = caplog.text
    assert f"Please add {PYVM_BIN} to your PATH" in stderr

    assert res == PYVM_HOME / "3.11/bin/python3"

    # check that the shim was created
    shim = PYVM_BIN / "python3.11"
    assert shim.exists()
    assert str(res) in shim.read_text()

    # test python-build-standalone's ability to make virtual environments
    venv = tmp / "venv"
    subprocess.check_call([shim, "-m", "venv", venv])
    assert (venv / "bin" / "python").exists()
    assert "3.11" in subprocess.check_output([venv / "bin" / "python", "--version"]).decode()


def test_install_unit(mock_fetch, fakefs, caplog):
    "Unit test for `pyvm install`"
    test_install(fakefs, caplog)


@pytest.mark.end_to_end
def test_install_pipx(fakefs, caplog):
    "`pyvm install pipx` should install pipx into PYVM_HOME and create a shim for it in PYVM_BIN"


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


def test_idempotency_unit(mock_fetch, fakefs, caplog):
    "Unit test for `pyvm install` idempotency"
    test_idempotency(fakefs, caplog)


@pytest.mark.end_to_end
def test_update(fakefs, caplog):
    "`pyvm.update_all_versions` should update all installed versions"
    PYVM_HOME, PYVM_BIN, tmp = fakefs
    
    pyvm.PYVM_PBS_RELEASE = "20240107"
    res = pyvm.install_version("3.11")

    pyvm.PYVM_PIPX_RELEASE = "1.4.3"
    pipx_zipapp = pyvm.ensure_pipx()
    assert pipx_zipapp.exists()
    assert "1.4.3" in subprocess.check_output([res, pipx_zipapp, "--version"]).decode()

    # create a virtual environment with the older python patch version
    venv = tmp / "venv"
    venv_bin = (venv / "bin" / "python")
    subprocess.check_call([res, "-m", "venv", venv])
    assert venv_bin.exists()
    assert "3.11" in subprocess.check_output([venv / "bin" / "python", "--version"]).decode()

    pyvm.PYVM_PBS_RELEASE = "latest"
    pyvm.PYVM_PIPX_RELEASE = "latest"
    pyvm.update_all_versions()
    # since our fake PYVM_BIN folder isn't on the PATH, pyvm should print a warning to stderr
    # reminding user to add it to their PATH
    stderr = caplog.text
    assert f"Please add {PYVM_BIN} to your PATH" in stderr

    assert res == PYVM_HOME / "3.11/bin/python3"

    assert "1.5.0" in subprocess.check_output([res, pipx_zipapp, "--version"]).decode()

    # check that the shim was created
    shim = PYVM_BIN / "python3.11"
    assert shim.exists()
    assert str(res) in shim.read_text()

    # make sure virtual environments made with older patch versions still work
    assert "3.11" in subprocess.check_output([venv_bin, "--version"]).decode()



def test_update_unit(mock_fetch, fakefs, caplog):
    "Unit test for `pyvm install`"
    test_update(fakefs, caplog)


@pytest.mark.end_to_end
def test_run(fakefs, caplog):
    "`pyvm pipx install poetry` should bootstrap python, download the pipx zipapp into PYVM_HOME, and use it to install poetry"
    PYVM_HOME, PYVM_BIN, tmp = fakefs
    assert not (PYVM_HOME / "3.12").exists()
    assert not (tmp / "venv" / "bin" / "python").exists()   
    assert not (PYVM_BIN / "python3.12").exists()

    subprocess.run([sys.executable, pyvm.__file__, "run", "3.12", "-m", "venv", tmp / "venv"], env=os.environ, check=True)
    assert (PYVM_HOME / "3.12").exists()
    assert (tmp / "venv" / "bin" / "python").exists() 

    # the run command should not create a shim in user's PATH.
    # That would be an unexpected side effect  
    assert not (PYVM_BIN / "python3.12").exists()  


def test_run_unit(mock_fetch, fakefs, caplog):
    "Unit test for `pyvm run`"
    test_run(fakefs, caplog)


@pytest.mark.end_to_end
def test_pipx(fakefs, caplog, mocker):
    "`pyvm pipx install poetry` should bootstrap python, download the pipx zipapp into PYVM_HOME, and use it to install poetry"
    PYVM_HOME, PYVM_BIN, tmp = fakefs
    assert not (PYVM_HOME / "3.12").exists()
    assert not (PYVM_BIN / "python3.12").exists()
    assert not (PYVM_BIN / "pipx").exists()

    subprocess.run([sys.executable, pyvm.__file__, "pipx", "3.12", "run", "cowsay", "-t", "hello"], env=os.environ, check=True)
    assert (PYVM_HOME / "3.12").exists()

    # the pipx command should not create a shim in user's PATH.
    # That would be an unexpected side effect  
    assert not (PYVM_BIN / "python3.12").exists()  
    assert not (PYVM_BIN / "pipx").exists()


def test_pipx_unit(mock_fetch, fakefs, caplog, mocker):
    "Unit test for `pyvm pipx`"
    test_pipx(fakefs, caplog, mocker)


def test_override(fakefs, mock_fetch, tmp_path):
    "Test pyvm.override's ability to temporarily override pyvm config"
    original_home = pyvm.PYVM_HOME
    assert pyvm.PYVM_HOME == original_home
    original_bin = pyvm.PYVM_BIN
    assert pyvm.PYVM_BIN == original_bin

    with pyvm.override():
        pyvm.PYVM_HOME = tmp_path / "pyvm"
        pyvm.PYVM_BIN = tmp_path / "bin"

        pyvm.install_version("3.11")
    
    assert (tmp_path / "pyvm" / "3.11" / "bin" / "python3.11").exists()
    assert (tmp_path / "bin" / "python3.11").exists()

    assert not (original_home / "3.11" / "bin" / "python3.11").exists()
    assert not (original_bin / "python3").exists()
    
    assert pyvm.PYVM_HOME == original_home
    assert pyvm.PYVM_BIN == original_bin

