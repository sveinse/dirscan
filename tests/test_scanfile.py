import os
import sys
import pytest
from pathlib import Path
from pytest import raises
#from pprint import pprint

import dirscan as ds

# pylint: disable-all


def test_scanfile_empty_file(wd):
    ''' Test passing an empty scanfile to read_scanfile() and dirscan '''

    wd.wrdata('a', None)

    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert 'Invalid scanfile' in str(exc.value)

    with raises(NotADirectoryError) as exc:
        ds.main(["--debug", "a"])


def test_scanfile_no_access(wd):
    ''' Test passing a file with no access to read_scanfile() and dirscan '''

    if sys.platform == 'win32':
        pytest.skip("Not supported on windows")

    wd.wrdata('a', None)
    wd.chmod('a', 0x000)

    with raises(PermissionError) as exc:
        ds.read_scanfile('a')

    with raises(PermissionError) as exc:
        ds.main(["--debug", "a"])


def test_scanfile_is_scanfile(wd):
    ''' Test the is_scanfile() method with various file inputs '''

    # Test mundane input first
    assert ds.is_scanfile('') == False
    assert ds.is_scanfile(None) == False
    assert ds.is_scanfile('noexist') == False

    # Give dir
    wd.makedirs('d1')
    assert ds.is_scanfile('d1') == False

    # Give dir with no access
    if sys.platform != 'win32':
        wd.makedirs('d2')
        wd.chmod('d2', 0o000)
        assert ds.is_scanfile('d2') == False

    # Give empty file
    wd.wrdata('a', None)
    assert ds.is_scanfile('a') == False

    # Give file without permission
    if sys.platform != 'win32':
        wd.wrdata('p', None)
        wd.chmod('p', 0o000)
        with raises(PermissionError):
            ds.is_scanfile('p')

    # File which is not scanfile
    wd.wrdata('a', ('''foobar'''))
    assert ds.is_scanfile('a') == False

    # Too new scanfile version
    wd.wrdata('a', ('''#!ds:v100'''))
    assert ds.is_scanfile('a') == False

    # Proper file header
    wd.wrdata('a', ('''#!ds:v1'''))
    assert ds.is_scanfile('a') == True


def test_scanfile_read_scanfile_file_handling(wd):
    ''' Test the read_scanfile() '''

    # Test mundane input first
    with raises(FileNotFoundError):
        ds.read_scanfile('')
    with raises(TypeError):
        ds.read_scanfile(None)
    with raises(FileNotFoundError):
        ds.read_scanfile('noexist')

    # Give dir
    wd.makedirs('d1')
    exctype = IsADirectoryError
    if sys.platform == 'win32':
        exctype = PermissionError
    with raises(exctype):
        ds.read_scanfile('d1')

    # Give dir with no access
    wd.makedirs('d2')
    wd.chmod('d2', 0o000)
    with raises(PermissionError):
        ds.read_scanfile('d2')

    # Give empty file
    wd.wrdata('a', None)
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Invalid scanfile 'a', missing header" in str(exc.value)

    # Give file without permission
    if sys.platform != 'win32':
        wd.wrdata('p', None)
        wd.chmod('p', 0o000)
        with raises(PermissionError):
            ds.read_scanfile('p')

    # File which is not scanfile
    wd.wrdata('a', ('''foobar'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Invalid scanfile 'a', malformed header" in str(exc.value)

    # Too new scanfile version
    wd.wrdata('a', ('''#!ds:v100'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Invalid scanfile 'a', unsupported version 'v100'" in str(exc.value)

    # Proper file header, but no data
    wd.wrdata('a', ('''#!ds:v1'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Scanfile 'a' contains no data or no top-level directory" in str(exc.value)


def test_scanfile_read_scanfile_data_fields(wd):
    ''' Test the basic line fields'''

    # Test correct minimal file
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
'''))
    d = ds.read_scanfile('a')
    assert isinstance(d, ds.DirObj)
    assert d.name == 'a'
    assert d.path == ''
    assert d.size == None
    assert d.mode == 0
    assert d.uid == 0
    assert d.gid == 0
    assert d._mtime == 0

    # Test empty lines
    wd.wrdata('a', (
'''#!ds:v1

d,,,,,,,.

'''))
    d = ds.read_scanfile('a')
    assert isinstance(d, ds.DirObj)

    # Test comments
    wd.wrdata('a', (
'''#!ds:v1
# foobar
d,,,,,,,.
# after
'''))
    d = ds.read_scanfile('a')
    assert isinstance(d, ds.DirObj)

    # Test empty filename
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, 'path' field (#7) cannot be omitted" in str(exc.value)

    # Test filenames ending with /
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,./
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, empty filename './'" in str(exc.value)

    # Test empty type
    wd.wrdata('a', (
'''#!ds:v1
,,,,,,,.
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, 'type' field (#1) cannot be omitted" in str(exc.value)

    # Test file type top
    wd.wrdata('a', (
'''#!ds:v1
f,,,,,,,.
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Scanfile 'a' contains no data or no top-level directory" in str(exc.value)

    # Test too few fields
    wd.wrdata('a', (
'''#!ds:v1
d
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, Missing or excess file fields (got 1, want 8)" in str(exc.value)

    # Test incorrect filetype
    wd.wrdata('a', (
'''#!ds:v1
q,,,,,,,.
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, Unknown object type 'q'" in str(exc.value)

    # Test for invalid data in the fields
    tests = (
        "d,text,,,,,,.",  # size text
        "d,1.44,,,,,,.",  # size float
        "d,,text,,,,,.",  # mode text
        "d,,1.44,,,,,.",  # mode float
        "d,,9999,,,,,.",  # mode number
        "d,,,text,,,,.",  # uid text
        "d,,,1.44,,,,.",  # uid float
        "d,,,,text,,,.",  # gid text
        "d,,,,1.44,,,.",  # gid float
        "d,,,,,text,,.",  # mtime text
        "d,,,,,1.44,,.",  # mtime float
    )
    for test in tests:
        wd.wrdata('a', (
f'''#!ds:v1
{test}
'''))
        with raises(ds.DirscanException) as exc:
            ds.read_scanfile('a')
        assert "Data error, Scanfile field error: invalid literal for int()" in str(exc.value)

    # Test for negative number in the numeric fields
    tests = (
        "d,-1,,,,,,.",  # size
        "d,,-1,,,,,.",  # mode
        "d,,,-1,,,,.",  # uid
        "d,,,,-1,,,.",  # gid
        "d,,,,,-1,,.",  # mtime
    )
    for test in tests:
        wd.wrdata('a', (
f'''#!ds:v1
{test}
'''))
        with raises(ds.DirscanException) as exc:
            ds.read_scanfile('a')
        assert "Data error, Scanfile field error: Number must be positive" in str(exc.value)

    # FIXME: Add test of quoting of the data and path fields


def test_scanfile_read_scanfile_data_structures_success(wd):
    ''' Test the higher level data structure, expected successes '''

    # Test subdir without ./ prefix
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,b
'''))
    a = ds.read_scanfile('a')
    b = a.children()
    assert a.path == ''
    assert a.name == 'a'
    assert len(b) == 1
    assert b[0].path == 'a'
    assert b[0].name == 'b'

    # Test subdir of subdir without ./ prefix
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,b
d,,,,,,,b/c
'''))
    a = ds.read_scanfile('a')
    b = a.children()
    c = b[0].children()
    assert a.path == ''
    assert a.name == 'a'
    assert len(b) == 1
    assert b[0].path == 'a'
    assert b[0].name == 'b'
    assert len(c) == 1
    assert c[0].path == 'a/b'
    assert c[0].name == 'c'

    # Test subdir with ./ prefix
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,./b
'''))
    a = ds.read_scanfile('a')
    b = a.children()
    assert a.path == ''
    assert a.name == 'a'
    assert len(b) == 1
    assert b[0].path == 'a'
    assert b[0].name == 'b'

    # Test subdir of subdir with ./ prefix
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,./b
d,,,,,,,./b/c
'''))
    a = ds.read_scanfile('a')
    b = a.children()
    c = b[0].children()
    assert a.path == ''
    assert a.name == 'a'
    assert len(b) == 1
    assert b[0].path == 'a'
    assert b[0].name == 'b'
    assert len(c) == 1
    assert c[0].path == 'a/b'
    assert c[0].name == 'c'

    # Test successful subroot
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,b
d,,,,,,,b/c
'''))
    b = ds.read_scanfile('a', 'b')
    c = b.children()
    assert b.path == 'a'
    assert b.name == 'b'
    assert len(c) == 1
    assert c[0].path == 'a/b'
    assert c[0].name == 'c'


def test_scanfile_read_scanfile_data_structures_fails(wd):
    ''' Test the higher level data structure, expected fails '''

    # Test repeated top
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,.
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, '.' already exists in file" in str(exc.value)

    # Test orphan
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,foo/orphan
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, 'foo/orphan' is an orphan" in str(exc.value)

    # Test orphan with ./ prefix
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,./b/c
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, './b/c' is an orphan" in str(exc.value)

    # Test duplicate dirs
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,b
d,,,,,,,b
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, 'b' already exists in file" in str(exc.value)

    # Test duplicate dirs with ./ prefix
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,./b
d,,,,,,,./b
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, './b' already exists in file" in str(exc.value)

    # Test duplicate files
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
f,,,,,,,b
f,,,,,,,b
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, 'b' already exists in file" in str(exc.value)

    # Test duplicate name with different filetype
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,b
f,,,,,,,b
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, 'b' already exists in file" in str(exc.value)

    # Test subroot which is not dir
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
f,,,,,,,b
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a', 'b')
    assert "No such directory 'b' found in scanfile 'a'" in str(exc.value)

    # Test subroot that does not exist
    wd.wrdata('a', (
'''#!ds:v1
d,,,,,,,.
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a', 'b')
    assert "No such directory 'b' found in scanfile 'a'" in str(exc.value)
