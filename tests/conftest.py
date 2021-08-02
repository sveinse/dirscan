import os
import subprocess
import pytest


@pytest.fixture
def wd(tmpdir):
    dir = os.getcwd()
    os.chdir(tmpdir)
    print()
    yield tmpdir
    os.chdir(dir)
    subprocess.call(["chmod", "-R", "700", tmpdir])
