import os
from pytest import raises
#from pprint import pprint

import dirscan as ds

# pylint: disable-all

def test_no_access_to_topdir(wd):
    ''' Test scanning a dir with no access '''
    os.makedirs('a')
    os.chmod('a', 0o000)

    # Direct call
    with raises(PermissionError) as exc:
        for _ in ds.walkdirs(('a',)): pass

    # Cmd line
    with raises(PermissionError) as exc:
        ds.main(["--debug", "a"])


def test_top_is_not_a_dir(wd):
    ''' Test giving a file to scan instead of a dir '''
    with open('a', 'w') as f: pass

    # Direct call
    with raises(NotADirectoryError) as exc:
        for _ in ds.walkdirs(('a',)): pass

    # Cmd line
    with raises(NotADirectoryError) as exc:
        ds.main(["--debug", "a"])


def test_top_is_not_existing(wd):
    ''' Test scanning a path that doesn't exist '''

    # Direct call
    with raises(FileNotFoundError) as exc:
        for _ in ds.walkdirs(('a',)): pass

    # Cmd line
    with raises(FileNotFoundError) as exc:
        ds.main(["--debug", "a"])


def test_empty_dirlist(wd):
    ''' Test passing empty lists to walkdirs() '''

    ds.set_debug(1)

    expect = ((('.'),()),)

    # Empty list
    result = tuple(ds.walkdirs([]))
    assert result == expect

    # None list
    with raises(TypeError) as exc:
        for _ in ds.walkdirs(None): pass
