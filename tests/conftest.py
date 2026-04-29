import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
import pytest


@dataclass
class Tempdir:
    path: Path

    @staticmethod
    def wrdata(f, d):
        with open(f, 'w', encoding='utf-8') as fd:
            if d:
                fd.write(d)
            fd.flush()

    @staticmethod
    def chmod(*args, **kwargs):
        return os.chmod(*args, **kwargs)

    @staticmethod
    def makedirs(*args, **kwargs):
        return os.makedirs(*args, **kwargs)


@pytest.fixture
def wd(tmp_path: Path):
    dir = os.getcwd()
    os.chdir(tmp_path)
    yield Tempdir(tmp_path)
    os.chdir(dir)
    subprocess.call(["chmod", "-R", "700", tmp_path])
