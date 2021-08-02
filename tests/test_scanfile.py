import os
import pytest
import subprocess

import dirscan


def prexc(exc):
    print(exc.type.__name__ + ': ' + str(exc.value))


def test_scanfile_empty_file(wd):
    ''' Test passing an empty scanfile to read_scanfile() and dirscan '''
    with open('a', 'w') as f:
        pass

    with pytest.raises(dirscan.DirscanException) as exc:
        dirscan.read_scanfile('a')
    prexc(exc)
    assert 'Invalid scanfile' in str(exc.value)

    with pytest.raises(subprocess.CalledProcessError) as exc:
        subprocess.check_call(["dirscan", "--debug", "a"])
    assert exc.value.returncode == 1


def test_scanfile_no_access(wd):
    ''' Test passing a file with no access to read_scanfile() and dirscan '''
    with open('a', 'w') as f:
        pass
    os.chmod('a', 0x000)

    with pytest.raises(PermissionError) as exc:
        dirscan.read_scanfile('a')
    prexc(exc)

    with pytest.raises(subprocess.CalledProcessError) as exc:
        subprocess.check_call(["dirscan", "--debug", "a"])
    assert exc.value.returncode == 1


def test_scanfile_is_scanfile(wd):
    ''' Test the is_scanfile() method with various file inputs '''

    # Test mundane errors first
    assert dirscan.is_scanfile('') == False
    assert dirscan.is_scanfile(None) == False
    assert dirscan.is_scanfile('foobar') == False

    # Give dir
    os.makedirs('d1')
    assert dirscan.is_scanfile('d1') == False

    # Give dir with no access
    os.makedirs('d2')
    os.chmod('d2', 0o000)
    assert dirscan.is_scanfile('d2') == False

    # Give empty file
    with open('a', 'w') as f:
        pass
    assert dirscan.is_scanfile('a') == False

    # Give file without permission
    os.chmod('a', 0o000)
    with pytest.raises(PermissionError) as exc:
        dirscan.is_scanfile('a')
    prexc(exc)
