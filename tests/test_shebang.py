import pytest

@pytest.mark.docker
def test_no_downloader(compose):
    "pyvm should fail if no downloader is found"
    c = compose('ubuntu_no_downloader')
    res = c.exec_run("./pyvm -h")
    assert "Neither curl nor wget found." in str(res.output)
    assert res.exit_code == 1


@pytest.mark.docker
def test_with_curl(compose):
    "pyvm should work when run on a machine with curl installed"
    c = compose('ubuntu_curl')
    res = c.exec_run("./pyvm -h")
    out = str(res.output)
    assert "extracting python 3.12..." in out
    assert "usage: pyvm [-h]" in out


def test_with_wget(compose):
    "pyvm should work when run on a machine with wget installed"
    c = compose('ubuntu_wget')
    res = c.exec_run("./pyvm -h")
    out = str(res.output)
    assert "extracting python 3.12..." in out
    assert "usage: pyvm [-h]" in out


def test_idempotency(compose):
    "pyvm should only bootstrap its own interpreter once, and then use it from cache"
    c = compose('ubuntu_wget')
    c.exec_run('rm -rf /home/testuser/.pyvm')

    res = c.exec_run("./pyvm -h")
    out = str(res.output)
    assert "extracting python 3.12..." in out
    assert "usage: pyvm [-h]" in out
    assert c.exec_run('test -d /home/testuser/.pyvm').exit_code == 0

    res = c.exec_run("./pyvm -h")
    out = str(res.output)
    assert "extracting python 3.12..." not in out
    assert "usage: pyvm [-h]" in out
