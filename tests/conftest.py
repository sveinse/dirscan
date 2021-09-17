import os
import subprocess
from dataclasses import dataclass
import pytest


@dataclass
class Tempdir:
    path: str

    @staticmethod
    def wrdata(f, d):
        with open(f, 'w') as fd:
            if d:
                fd.write(d)

    @staticmethod
    def chmod(*args, **kwargs):
        return os.chmod(*args, **kwargs)

    @staticmethod
    def makedirs(*args, **kwargs):
        return os.makedirs(*args, **kwargs)


@pytest.fixture
def wd(tmpdir):
    dir = os.getcwd()
    os.chdir(tmpdir)
    print()
    yield Tempdir(tmpdir)
    os.chdir(dir)
    subprocess.call(["chmod", "-R", "700", tmpdir])
