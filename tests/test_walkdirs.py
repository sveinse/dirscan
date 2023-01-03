from dataclasses import dataclass
import os
import sys
from typing import Any
import pytest
from pytest import raises
from pathlib import Path
from pprint import pprint

import dirscan as ds

# pylint: disable-all


def test_walkdirs_no_access_to_topdir(wd):
    ''' Test scanning a dir with no access '''

    if sys.platform == 'win32':
        pytest.skip("Not supported on windows")

    wd.makedirs('a')
    wd.chmod('a', 0o000)

    # Direct call
    with raises(PermissionError) as exc:
        for _ in ds.walkdirs(('a',)): pass

    # Cmd line
    with raises(PermissionError) as exc:
        ds.main(["--debug", "a"])


def test_walkdirs_top_is_not_a_dir(wd):
    ''' Test giving a file to scan instead of a dir '''

    wd.wrdata('a', None)

    # Direct call
    with raises(NotADirectoryError) as exc:
        for _ in ds.walkdirs(('a',)): pass

    # Cmd line
    with raises(NotADirectoryError) as exc:
        ds.main(["--debug", "a"])


def test_walkdirs_top_is_not_existing(wd):
    ''' Test scanning a path that doesn't exist '''

    # Direct call
    with raises(FileNotFoundError) as exc:
        for _ in ds.walkdirs(('noexist',)): pass

    # Cmd line
    with raises(FileNotFoundError) as exc:
        ds.main(["--debug", "noexist"])


def test_walkdirs_empty_dirlist(wd):
    ''' Test passing empty lists to walkdirs() '''

    ds.set_debug(1)

    expect = (((Path('.')),()),)

    # Empty list
    result = tuple(ds.walkdirs([]))
    assert result == expect

    # None list
    with raises(TypeError) as exc:
        for _ in ds.walkdirs(None): pass


# st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size, st_atime, st_mtime, st_ctime
FAKESTAT = os.stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0))

def prep(expected, start):

    def mk_obj(obj, path, s):
        if path == '.':
            return obj('', path=s, stat=FAKESTAT)
        pp = os.path.split(path)
        kw = {}
        if obj is not ds.NonExistingObj:
            kw['stat'] = FAKESTAT
        return obj(pp[-1], path=Path(s, pp[0]), **kw)

    for path, *obj in expected:
        yield Path(path), tuple(mk_obj(o, path, s) for o, s in zip(obj, start))


def maketree(wd, base, withb=True):
    wd.makedirs(base)
    wd.wrdata(Path(base, 'x'), None)
    if withb:
        wd.makedirs(Path(base, 'b'))
        wd.wrdata(Path(base, 'b/y'), None)
    wd.makedirs(Path(base, 'c'))


def compare(dirs, expected, **kwargs):
    walks = tuple(ds.walkdirs(dirs, **kwargs))
    for (ap, aobj), (bp, bobj) in zip(
                walks, prep(expected, dirs), strict=True):

        #print((ap, aobj), (bp, bobj))

        # Path is equal
        assert ap == bp

        # For each of the objects...
        for ao, bo in zip(aobj, bobj, strict=True):
            # Assert that type, name and path is equal
            assert type(ao) is type(bo)
            assert ao.name == bo.name
            assert ao.path == bo.path

    return walks


#
# Plain scan without additional options
#

def test_walkdirs_scan(wd):

    maketree(wd, 'a')
    dirs = ('a', )

    expected = (
        ('.', ds.DirObj),
        ('b', ds.DirObj),
        ('b/y', ds.FileObj),
        ('c', ds.DirObj),
        ('x', ds.FileObj),
    )

    compare(dirs, expected)


def test_walkdirs_scan2(wd):

    maketree(wd, 'a')
    maketree(wd, 'b')
    dirs = ('a', 'b')

    expected = (
        ('.', ds.DirObj, ds.DirObj),
        ('b', ds.DirObj, ds.DirObj),
        ('b/y', ds.FileObj, ds.FileObj),
        ('c', ds.DirObj, ds.DirObj),
        ('x', ds.FileObj, ds.FileObj),
    )

    compare(dirs, expected)


def test_walkdirs_scan3(wd):

    maketree(wd, 'a')
    maketree(wd, 'b')
    maketree(wd, 'c')
    dirs = ('a', 'b', 'c')

    expected = (
        ('.'  , ds.DirObj , ds.DirObj , ds.DirObj ),
        ('b'  , ds.DirObj , ds.DirObj , ds.DirObj ),
        ('b/y', ds.FileObj, ds.FileObj, ds.FileObj),
        ('c'  , ds.DirObj , ds.DirObj , ds.DirObj ),
        ('x'  , ds.FileObj, ds.FileObj, ds.FileObj),
    )

    compare(dirs, expected)


#
# Reversed
#

def test_walkdirs_scan_reverse(wd):

    maketree(wd, 'a')
    dirs = ('a', )

    expected = (
        ('.', ds.DirObj),
        ('x', ds.FileObj),
        ('c', ds.DirObj),
        ('b', ds.DirObj),
        ('b/y', ds.FileObj),
    )

    compare(dirs, expected, reverse=True)


#
# Test traverse_oneside setting
#

def test_walkdirs_traverse_oneside_scan(wd):

    maketree(wd, 'a')
    dirs = ('a', )

    expected = (
        ('.', ds.DirObj),
        ('b', ds.DirObj),
        ('b/y', ds.FileObj),
        ('c', ds.DirObj),
        ('x', ds.FileObj),
    )

    compare(dirs, expected, traverse_oneside=False)
    compare(dirs, expected, traverse_oneside=True)


def test_walkdirs_traverse_oneside_scan2(wd):

    maketree(wd, 'a')
    maketree(wd, 'b', withb=False)
    dirs = ('a', 'b')

    expected_false = (
        ('.', ds.DirObj, ds.DirObj),
        ('b', ds.DirObj, ds.NonExistingObj),
        #('b/y', ds.FileObj, ds.FileObj),
        ('c', ds.DirObj, ds.DirObj),
        ('x', ds.FileObj, ds.FileObj),
    )
    expected_true = (
        ('.', ds.DirObj, ds.DirObj),
        ('b', ds.DirObj, ds.NonExistingObj),
        ('b/y', ds.FileObj, ds.NonExistingObj),
        ('c', ds.DirObj, ds.DirObj),
        ('x', ds.FileObj, ds.FileObj),
    )

    compare(dirs, expected_false, traverse_oneside=False)
    compare(dirs, expected_true, traverse_oneside=True)


def test_walkdirs_traverse_oneside_scan3(wd):

    maketree(wd, 'a')
    maketree(wd, 'b')
    maketree(wd, 'c', withb=False)
    dirs1 = ('a', 'b', 'c')

    maketree(wd, 'd')
    maketree(wd, 'e', withb=False)
    maketree(wd, 'f', withb=False)
    dirs2 = ('d', 'e', 'f')

    expected_false1 = (
        ('.'  , ds.DirObj , ds.DirObj , ds.DirObj ),
        ('b'  , ds.DirObj , ds.DirObj , ds.NonExistingObj),
        ('b/y', ds.FileObj, ds.FileObj, ds.NonExistingObj),
        ('c'  , ds.DirObj , ds.DirObj , ds.DirObj ),
        ('x'  , ds.FileObj, ds.FileObj, ds.FileObj),
    )
    expected_false2 = (
        ('.'  , ds.DirObj , ds.DirObj , ds.DirObj ),
        ('b'  , ds.DirObj , ds.NonExistingObj, ds.NonExistingObj),
        #('b/y', ds.FileObj, ds.NonExistingObj, ds.NonExistingObj),
        ('c'  , ds.DirObj , ds.DirObj , ds.DirObj ),
        ('x'  , ds.FileObj, ds.FileObj, ds.FileObj),
    )

    compare(dirs1, expected_false1, traverse_oneside=False)
    compare(dirs2, expected_false2, traverse_oneside=False)

    expected_true1 = expected_false1
    expected_true2 = (
        ('.'  , ds.DirObj , ds.DirObj , ds.DirObj ),
        ('b'  , ds.DirObj , ds.NonExistingObj, ds.NonExistingObj),
        ('b/y', ds.FileObj, ds.NonExistingObj, ds.NonExistingObj),
        ('c'  , ds.DirObj , ds.DirObj , ds.DirObj ),
        ('x'  , ds.FileObj, ds.FileObj, ds.FileObj),
    )

    compare(dirs1, expected_true1, traverse_oneside=True)
    compare(dirs2, expected_true2, traverse_oneside=True)


#
# Exclusion testing
#

def test_walkdirs_exclude(wd):

    maketree(wd, 'a')
    dirs = ('a', )

    expected = (
        ('.', ds.DirObj),
        ('b', ds.DirObj),
        #('b/y', ds.FileObj),
        ('c', ds.DirObj),
        ('x', ds.FileObj),
    )

    walk = compare(dirs, expected, excludes=['b'])

    # FIXME: Is it unexpected that 'b' is returned? However excluded is
    #        set
    for p, (obj,) in walk:
        if p == Path('b'):
            assert obj.excluded == True


def test_walkdirs_dirofdir(wd):

    pytest.skip("Not complete yet")

    # FIXME: Test the top-level Dirobject name and path, both from fs and
    # from scanfile

    wd.makedirs('a')
    wd.makedirs('a/a')
    wd.wrdata('a/a/b', None)

    print()
    for a in ds.walkdirs(('a/a',)):
        print(a, tuple(str(o.fullpath) for o in a[1]))

    ds.main(["a/a", '-o', 'scan.out'])
    with open('scan.out', 'r') as f:
        d = f.read()
    print(d)

    wd.wrdata('a.scan', (
'''#!ds:v1
d,0,777,0,0,0,,.
f,0,666,0,0,0,,b
'''))

    top = ds.read_scanfile('a.scan')
    for a in ds.walkdirs((top,)):
        print(a, tuple(str(o.fullpath) for o in a[1]))

    # FIXME: This
    assert False