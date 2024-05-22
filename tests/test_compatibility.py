import os
import subprocess
import shutil
from pathlib import Path

import pytest

@pytest.mark.end_to_end
@pytest.mark.parametrize("version", ["20", "18", "16", "14"])
def test_ubuntu(version, compose):
    "pyvm should work on all recentish versions of ubuntu (14.04 and up)"
    c = compose[f'ubuntu_{version}']
    res = c.exec_run("./pyvm -h")
    out = str(res.output)
    assert "extracting python 3.12..." in out
    assert "usage: pyvm [-h]" in out

@pytest.mark.end_to_end
@pytest.mark.parametrize("version", ["40", "38", "36", "34", "32"])
def test_fedora(version, compose):
    "pyvm should work on all recentish versions of fedora (32 and up)"
    c = compose[f'fedora_{version}']
    res = c.exec_run("./pyvm -h")
    out = str(res.output)
    assert "extracting python 3.12..." in out
    assert "usage: pyvm [-h]" in out

@pytest.mark.end_to_end
def test_pyvm_local(fakefs, caplog):
    "pyvm should work when run from a local directory"
    PYVM_HOME, PYVM_BIN, tmp = fakefs
    assert not (PYVM_HOME / "3.12").exists()
    assert not (PYVM_BIN / "python3.12").exists()

    subprocess.run(f"cd {tmp} && curl -sSfLo ./pyvm alextremblay.github.io/pyvm/pyvm.py && chmod +x ./pyvm", check=True, shell=True)
    local_pyvm = tmp / "pyvm"
    assert local_pyvm.exists()
    assert "3.12" in subprocess.check_output("./pyvm run 3.12 --version", shell=True, cwd=tmp).decode()
    assert (PYVM_HOME / "3.12").exists()

@pytest.mark.end_to_end
def test_pyvm_pipx_as_shebang(fakefs, caplog, mocker):
    "test using pyvm as a shebang with pipx"
    PYVM_HOME, PYVM_BIN, tmp = fakefs
    pyvm_bin = tmp / "pyvm"
    shutil.copy("pyvm.py", pyvm_bin)
    pyvm_bin.chmod(0o755)
    mocker.patch.dict("os.environ", {"PATH": f"{tmp}:{os.environ['PATH']}"})
    shutil.copy("tests/examples/shebang_basic.py", tmp)
    example_script = tmp / "shebang_basic.py"
    example_script.chmod(0o755)
    res = subprocess.run(f"{example_script}", shell=True, check=True, cwd=tmp, capture_output=True)
    out = res.stdout.decode()
    assert "httpbin.org" in out

@pytest.mark.end_to_end
def test_pyvm_pipx_as_shebang_with_bootstrapping(fakefs, caplog, mocker):
    "test using pyvm as a shebang with pipx"
    PYVM_HOME, PYVM_BIN, tmp = fakefs

    shutil.copy("tests/examples/shebang_bootstrapping.py", tmp)
    example_script = tmp / "shebang_bootstrapping.py"
    example_script.chmod(0o755)
    res = subprocess.run(f"{example_script}", shell=True, check=True, cwd=tmp, capture_output=True)
    out = res.stdout.decode()
    assert "httpbin.org" in out