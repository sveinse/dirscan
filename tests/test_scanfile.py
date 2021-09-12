import os
from pytest import raises
#from pprint import pprint

import dirscan as ds

# pylint: disable-all


def prexc(exc):
    print(exc.type.__name__ + ': ' + str(exc.value))


def wrdata(f, d=None):
    with open(f, 'w') as fd:
        if d:
            fd.write(d)


def test_scanfile_empty_file(wd):
    ''' Test passing an empty scanfile to read_scanfile() and dirscan '''

    wrdata('a')

    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert 'Invalid scanfile' in str(exc.value)

    with raises(NotADirectoryError) as exc:
        ds.main(["--debug", "a"])


def test_scanfile_no_access(wd):
    ''' Test passing a file with no access to read_scanfile() and dirscan '''

    wrdata('a')
    os.chmod('a', 0x000)

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
    os.makedirs('d1')
    assert ds.is_scanfile('d1') == False

    # Give dir with no access
    os.makedirs('d2')
    os.chmod('d2', 0o000)
    assert ds.is_scanfile('d2') == False

    # Give empty file
    wrdata('a')
    assert ds.is_scanfile('a') == False

    # Give file without permission
    wrdata('p')
    os.chmod('p', 0o000)
    with raises(PermissionError):
        ds.is_scanfile('p')

    # File which is not scanfile
    wrdata('a', ('''foobar'''))
    assert ds.is_scanfile('a') == False

    # Too new scanfile version
    wrdata('a', ('''#!ds:v100'''))
    assert ds.is_scanfile('a') == False

    # Proper file header
    wrdata('a', ('''#!ds:v1'''))
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
    os.makedirs('d1')
    with raises(IsADirectoryError):
        ds.read_scanfile('d1')

    # Give dir with no access
    os.makedirs('d2')
    os.chmod('d2', 0o000)
    with raises(PermissionError):
        ds.read_scanfile('d2')

    # Give empty file
    wrdata('a')
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Invalid scanfile 'a', missing header" in str(exc.value)

    # Give file without permission
    wrdata('p')
    os.chmod('p', 0o000)
    with raises(PermissionError):
        ds.read_scanfile('p')

    # File which is not scanfile
    wrdata('a', ('''foobar'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Invalid scanfile 'a', malformed header" in str(exc.value)

    # Too new scanfile version
    wrdata('a', ('''#!ds:v100'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Invalid scanfile 'a', unsupported version 'v100'" in str(exc.value)

    # Proper file header, but no data
    wrdata('a', ('''#!ds:v1'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Scanfile 'a' contains no data or no top-level directory" in str(exc.value)


def test_scanfile_read_scanfile_data_fields(wd):
    ''' Test the basic line fields'''

    # Test correct minimal file
    wrdata('a', (
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
    wrdata('a', (
'''#!ds:v1

d,,,,,,,.

'''))
    d = ds.read_scanfile('a')
    assert isinstance(d, ds.DirObj)

    # Test comments
    wrdata('a', (
'''#!ds:v1
# foobar
d,,,,,,,.
# after
'''))
    d = ds.read_scanfile('a')
    assert isinstance(d, ds.DirObj)

    # Test empty filename
    wrdata('a', (
'''#!ds:v1
d,,,,,,,
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, 'path' field cannot be omitted" in str(exc.value)

    # Test filenames ending with /
    wrdata('a', (
'''#!ds:v1
d,,,,,,,./
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, empty filename './'" in str(exc.value)

    # Test empty type
    wrdata('a', (
'''#!ds:v1
,,,,,,,.
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, 'type' field cannot be omitted" in str(exc.value)

    # Test file type top
    wrdata('a', (
'''#!ds:v1
f,,,,,,,.
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Scanfile 'a' contains no data or no top-level directory" in str(exc.value)

    # Test too few fields
    wrdata('a', (
'''#!ds:v1
d
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, Missing or excess file fields (got 1, want 8)" in str(exc.value)

    # Test incorrect filetype
    wrdata('a', (
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
        wrdata('a', (
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
        wrdata('a', (
f'''#!ds:v1
{test}
'''))
        with raises(ds.DirscanException) as exc:
            ds.read_scanfile('a')
        assert "Data error, Scanfile field error: Number must be positive" in str(exc.value)

    # FIXME: Add test of quoting of the data and path fields


def test_scanfile_read_scanfile_data_structures_success(wd):
    ''' Test the higher level data structure, expected successes '''

    # Test subdir
    wrdata('a', (
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

    # Test subdir
    wrdata('a', (
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

    # Test dir relative path
    wrdata('a', (
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

    # Test subdir relative path
    wrdata('a', (
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


def test_scanfile_read_scanfile_data_structures_fails(wd):
    ''' Test the higher level data structure, expected fails '''

    # Test repeated data
    wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,.
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, '.' already exists in file" in str(exc.value)

    # Test orphan
    wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,foo/orphan
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, 'foo/orphan' is an orphan" in str(exc.value)

    # Test orphan2
    wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,./b/a
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, './b/a' is an orphan" in str(exc.value)

    # Test duplicate dirs
    wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,./a
d,,,,,,,./a
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, './a' already exists in file" in str(exc.value)

    # Test duplicate files
    wrdata('a', (
'''#!ds:v1
d,,,,,,,.
f,,,,,,,./a
f,,,,,,,./a
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a')
    assert "Data error, './a' already exists in file" in str(exc.value)

    # Test subroot which is not dir
    wrdata('a', (
'''#!ds:v1
d,,,,,,,.
f,,,,,,,./a
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a', 'a')
    assert "No such sub-directory 'a' found in scanfile 'a'" in str(exc.value)

    # Test subroot which does not exist
    wrdata('a', (
'''#!ds:v1
d,,,,,,,.
'''))
    with raises(ds.DirscanException) as exc:
        ds.read_scanfile('a', 'a')
    assert "No such sub-directory 'a' found in scanfile 'a'" in str(exc.value)

    # Test subroot which is not dir
    wrdata('a', (
'''#!ds:v1
d,,,,,,,.
d,,,,,,,./a
'''))
    d = ds.read_scanfile('a', 'a')
    assert d.name == 'a'

