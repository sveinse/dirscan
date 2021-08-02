import os
import pytest
from pprint import pprint
import subprocess

import dirscan

def test_no_access_to_topdir(wd):
    ''' Test scanning a dir with no access '''
    os.makedirs('a')
    os.chmod('a', 0o000)

    with pytest.raises(PermissionError) as exc:
        for (path, objs) in dirscan.walkdirs(('a',)):
            pass

    with pytest.raises(subprocess.CalledProcessError) as exc:
        subprocess.check_call(["dirscan", "--debug", "a"])
    assert exc.value.returncode == 1


def test_top_is_not_a_dir(wd):
    ''' Test giving a file to scan instead of a dir '''
    with open('a', 'w') as f:
        pass

    with pytest.raises(NotADirectoryError) as exc:
        for (path, objs) in dirscan.walkdirs(('a',)):
            pass

    with pytest.raises(subprocess.CalledProcessError) as exc:
        subprocess.check_call(["dirscan", "--debug", "a"])
    assert exc.value.returncode == 1


def test_top_is_not_existing(wd):
    ''' Test scanning a path that doesn't exist '''
    with pytest.raises(FileNotFoundError) as exc:
        for (path, objs) in dirscan.walkdirs(('a',)):
            pass

    with pytest.raises(subprocess.CalledProcessError) as exc:
        subprocess.check_call(["dirscan", "--debug", "a"])
    assert exc.value.returncode == 1


def test_empty_dirlist(wd):
    ''' Test passing empty lists to walkdirs() '''
    with pytest.raises(IndexError) as exc:
        for (path, objs) in dirscan.walkdirs([]):
            pass

    with pytest.raises(TypeError) as exc:
        for (path, objs) in dirscan.walkdirs(None):
            pass
