import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from .common import Tempdir


@pytest.fixture
def wd(tmp_path: Path) -> Iterator[Tempdir]:
    dir = os.getcwd()
    os.chdir(tmp_path)
    yield Tempdir(tmp_path)
    os.chdir(dir)
    subprocess.call(["chmod", "-R", "700", tmp_path])
