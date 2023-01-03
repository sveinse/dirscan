import sys
import pytest
from pytest import raises

import dirscan as ds

# pylint: disable-all

def toslash(text):
    if sys.platform == 'win32':
        return '\n' + text.replace('\\', '/')
    return '\n' + text


def test_main_no_arguments():
    ''' Test scanning a dir with no access '''

    with raises(SystemExit) as exc:
        ds.main([])
    assert int(exc.value.code) == 2


def test_main_too_many_arguments():

    with raises(SystemExit) as exc:
        ds.main(["a", "b", "c"])
    assert int(exc.value.code) == 2


def test_main_args_help():

    with raises(SystemExit) as exc:
        ds.main(["--help"])
    assert int(exc.value.code) == 0


def test_main_args_format_help():

    with raises(SystemExit) as exc:
        ds.main(["--format-help"])
    assert int(exc.value.code) == 1


def test_main_args_version(capsys):

    with raises(SystemExit) as exc:
        ds.main(["--version"])
    assert int(exc.value.code) == 0
    captured = capsys.readouterr()
    assert captured.out == "dirscan " + ds.__version__ + "\n"


@pytest.fixture()
def main_files(wd):
    wd.makedirs('a')
    wd.wrdata('a/a', '')
    wd.makedirs('a/b')
    wd.wrdata('a/b/c', '')


def test_main_scan(main_files, capsys):

    ds.main(["a"])
    captured = capsys.readouterr()

    assert toslash(captured.out) == '''
a
a/a
a/b
a/b/c
'''
    return

    ds.main(["-a", "a"])
    captured = capsys.readouterr()

    #print("\n" + toslash(captured.out))
    assert toslash(captured.out) == '''
drwxrwxrwx      0     0           0                                                                    d  a
-rw-rw-rw-      0     0           0                                                                    f  a/a
drwxrwxrwx      0     0           0                                                                    d  a/b
-rw-rw-rw-      0     0           0                                                                    f  a/b/c
'''

    ds.main(["-l", "a"])
    captured = capsys.readouterr()

    #print("\n" + toslash(captured.out))
    assert toslash(captured.out) == '''
drwxrwxrwx      0     0           0  2022-12-30 14:21:25  a
-rw-rw-rw-      0     0           0  2022-12-30 14:21:25  a/a
drwxrwxrwx      0     0           0  2022-12-30 14:21:25  a/b
-rw-rw-rw-      0     0           0  2022-12-30 14:21:25  a/b/c
'''
