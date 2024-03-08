import pytest

@pytest.mark.docker
@pytest.mark.parametrize("version", ["20", "18", "16", "14"])
def test_ubuntu(version, compose):
    "pyvm should work on all recentish versions of ubuntu (14.04 and up)"
    c = compose(f'ubuntu_{version}')
    res = c.exec_run("./pyvm -h")
    out = str(res.output)
    assert "extracting python 3.12..." in out
    assert "usage: pyvm [-h]" in out

@pytest.mark.docker
@pytest.mark.parametrize("version", ["40", "38", "36", "34", "32"])
def test_fedora(version, compose):
    "pyvm should work on all recentish versions of fedora (32 and up)"
    c = compose(f'fedora_{version}')
    res = c.exec_run("./pyvm -h")
    out = str(res.output)
    assert "extracting python 3.12..." in out
    assert "usage: pyvm [-h]" in out
