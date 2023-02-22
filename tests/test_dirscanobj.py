import os
import sys
import pytest
import datetime
import stat as osstat
from pathlib import Path
from pytest import raises
from pprint import pprint

import dirscan as ds

# pylint: disable-all

# st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size, st_atime, st_mtime, st_ctime
FAKESTAT = os.stat_result((0o123456, 0, 0, 0, 'uid', 'gid', 'size', 11, 42, 0))


def test_dirscanobj():

    a = ds.DirscanObj('a', path='b', stat=FAKESTAT)

    assert type(a) is ds.DirscanObj

    # Attributes
    assert a.name == 'a'
    assert a.path == 'b'
    assert a.mode == osstat.S_IMODE(FAKESTAT.st_mode)
    assert a.uid == FAKESTAT.st_uid
    assert a.gid == FAKESTAT.st_gid
    assert a.size == FAKESTAT.st_size
    assert a.dev == FAKESTAT.st_dev

    # Properties
    assert a.mtime == datetime.datetime.fromtimestamp(FAKESTAT.st_mtime)
    assert a.fullpath == Path('b/a')

    # Methods
    assert a.children() == ()
    assert tuple(a.compare(a)) == ()
    assert f"{a}" == "DirscanObj(b,a)"

    # Serializer won't work in base class
    with raises(AttributeError):
        a.to_dict()


def test_fileobj():

    a = ds.FileObj('a', path='b', stat=FAKESTAT, hashsum=b'1234')

    assert type(a) is ds.FileObj

    # Attributes
    assert a.objtype == 'f'
    assert a.name == 'a'
    assert a.path == 'b'
    assert a.mode == osstat.S_IMODE(FAKESTAT.st_mode)
    assert a.uid == FAKESTAT.st_uid
    assert a.gid == FAKESTAT.st_gid
    assert a.size == FAKESTAT.st_size
    assert a.dev == FAKESTAT.st_dev

    # Properties
    assert a.mtime == datetime.datetime.fromtimestamp(FAKESTAT.st_mtime)
    assert a.fullpath == Path('b/a')
    assert a.hashsum == b'1234'

    # Methods
    assert a.children() == ()
    assert tuple(a.compare(a)) == ()
    assert f"{a}" == "FileObj(b,a)"

    # Serializer won't work in base class
    assert a.to_dict() == {
        'objtype': 'f',
        'name': 'a',
        'path': 'b',
        'mode': osstat.S_IMODE(FAKESTAT.st_mode),
        'uid': FAKESTAT.st_uid,
        'gid': FAKESTAT.st_gid,
        'dev': FAKESTAT.st_dev,
        'size': FAKESTAT.st_size,
        'mtime': FAKESTAT.st_mtime,
        'hashsum': '31323334',
    }


def test_linkobj():

    # TODO: Add test for linkobj
    pass


def test_dirobj():

    a = ds.DirObj('a', path='b', stat=FAKESTAT, children=())

    # TODO: Test children input None

    assert type(a) is ds.DirObj

    # Attributes
    assert a.objtype == 'd'
    assert a.name == 'a'
    assert a.path == 'b'
    assert a.mode == osstat.S_IMODE(FAKESTAT.st_mode)
    assert a.uid == FAKESTAT.st_uid
    assert a.gid == FAKESTAT.st_gid
    assert a.size == 0  # Dir has no size
    assert a.dev == FAKESTAT.st_dev

    # Properties
    assert a.mtime == datetime.datetime.fromtimestamp(FAKESTAT.st_mtime)
    assert a.fullpath == Path('b/a')

    # Methods
    assert a.children() == ()
    assert tuple(a.compare(a)) == ()
    assert f"{a}" == "DirObj(b,a)"

    # Serializer won't work in base class
    assert a.to_dict() == {
        'objtype': 'd',
        'name': 'a',
        'path': 'b',
        'mode': osstat.S_IMODE(FAKESTAT.st_mode),
        'uid': FAKESTAT.st_uid,
        'gid': FAKESTAT.st_gid,
        'dev': FAKESTAT.st_dev,
        'size': 0,
        'mtime': FAKESTAT.st_mtime,
        'children': (),
    }


def test_objects():

    # TODO: Test BlockDevObj
    # TODO: Test CharDevObj
    # TODO: Test FifoObj
    # TODO: Test SocketObj
    pass


def test_nonexistingobj():

    # TODO: Test NonExistingObj
    pass


def test_fileobj_hashsum():

    # TODO: Test hashsum input

    a = ds.FileObj('a', path='b', stat=FAKESTAT, hashsum=None)
    a = ds.FileObj('a', path='b', stat=FAKESTAT, hashsum=b'')
    a = ds.FileObj('a', path='b', stat=FAKESTAT, hashsum=b'something')


def test_dirobj_children():

    # TODO: Test children input

    a = ds.DirObj('a', path='b', stat=FAKESTAT, children=None)
    a = ds.DirObj('a', path='b', stat=FAKESTAT, children=())


def test_obj_compare():

    # TODO: Test compare operations.
    # TODO: Test hashsum compare operations
    pass


def test_create_from_fs(wd):

    # TODO: Check setting full path in name vs setting path

    wd.makedirs('a')

    stat = os.lstat('a')

    a = ds.create_from_fs('a')

    assert type(a) is ds.DirObj
    assert a.objtype == 'd'
    assert a.name == 'a'
    assert a.path == ''
    assert a.mode == osstat.S_IMODE(stat.st_mode)
    assert a.size == 0  # Dir has no size
    assert a.uid == stat.st_uid
    assert a.gid == stat.st_gid
    assert a.mtime == datetime.datetime.fromtimestamp(stat.st_mtime)
    assert a.dev == stat.st_dev


def test_create_from_dict(wd):

    wd.makedirs('a')

    a = ds.DirObj('a', path='b', stat=FAKESTAT, children=())
    d = a.to_dict()

    b = ds.create_from_dict(d)

    assert type(b) is ds.DirObj
    assert b.objtype == 'd'
    assert b.name == 'a'
    assert b.path == 'b'
    assert b.mode == osstat.S_IMODE(FAKESTAT.st_mode)
    assert b.uid == FAKESTAT.st_uid
    assert b.gid == FAKESTAT.st_gid
    assert b.size == 0  # Dir has no size
    assert b.dev == FAKESTAT.st_dev
    assert b.mtime == datetime.datetime.fromtimestamp(FAKESTAT.st_mtime)

    # TODO: Do we need a == operator in DirscanObj?
    assert tuple(a.compare(b)) == ()


#-----------------

def xtest_dirscan_create(wd):

    # TODO: Read a real directory

    #wrdata('a')
    wd.makedirs('a')
    wd.makedirs('a/b')
    wd.makedirs('a/b/c')
    wd.wrdata('a/d', 'Hello')
    wd.wrdata('a/b/e', 'World')

    a = ds.create_from_fs('.')
    for _ in ds.walkdirs((a,), close_during=False):
        pass
    #tuple(ds.walkdirs((a,), close_during=False))
    pprint(a.to_dict())