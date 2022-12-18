import dirscan as ds
from dirscan.__main__ import scan_shadb
from dirscan.formatfields import COMPARE_TYPES_ALL


def scan(dirs, compare=ds.dir_compare2):
    ''' Generator for directory differences '''

    # Build the scan database
    shadb = scan_shadb(dirs)

    for (p, o) in ds.walkdirs(
            dirs,
            traverse_oneside=True,
        ):
        c, t = compare(
            o,
            comparetypes=COMPARE_TYPES_ALL,
            shadb=shadb,
        )
        #print(p, o, c, t)
        yield (str(p), c)


def test_shascan_dup(wd):
    ''' Test that it detects duplicates
    '''

    wd.makedirs('a')
    wd.wrdata('a/foo', 'foobar')
    wd.wrdata('a/bar', 'foobar')

    a = ds.create_from_fs('a')

    out = list(scan((a, ), compare=ds.dir_compare1))
    assert out == [
        ('.', 'scan'),
        ('bar', 'duplicated'),
        ('foo', 'duplicated'),
    ]


def test_shadiff_renamed(wd):
    ''' Test that a file has been renamed but with same contents
    '''

    wd.makedirs('a')
    wd.makedirs('b')
    wd.wrdata('a/foo', 'foobar')
    wd.wrdata('b/bar', 'foobar')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    assert list(scan((a, b))) == [
        ('.', 'equal'),
        ('bar', 'right_renamed'),
        ('foo', 'left_renamed'),
    ]


def test_shadiff_left_only(wd):
    ''' Tests that the same equal file on left side isn't indicated as
        a duplicate
    '''

    wd.makedirs('a')
    wd.makedirs('b')
    wd.wrdata('a/foo', 'foobar')
    wd.wrdata('a/bar', 'foobar')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    assert list(scan((a, b))) == [
        ('.', 'equal'),
        ('bar', 'left_only'),
        ('foo', 'left_only'),
    ]


def test_shadiff_cross(wd):
    ''' Test that two equal files swaps name
    '''

    wd.makedirs('a')
    wd.makedirs('b')
    wd.wrdata('a/foo', 'foo')
    wd.wrdata('a/bar', 'bar')
    wd.wrdata('b/foo', 'bar')  # a/bar -> b/foo
    wd.wrdata('b/bar', 'foo')  # a/foo -> b/bar

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    assert list(scan((a, b))) == [
        ('.', 'equal'),
        ('bar', 'changed'),  # FIXME
        ('foo', 'changed'),  # FIXME
    ]


def test_shadiff_dup2right(wd):
    ''' Test that a left side files exists in two files on right
    '''

    wd.makedirs('a')
    wd.makedirs('b')
    wd.wrdata('a/foo', 'foobar')
    wd.wrdata('b/foo', 'foobar')
    wd.wrdata('b/bar', 'foobar')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    assert list(scan((a, b))) == [
        ('.', 'equal'),
        ('bar', 'right_renamed'),
        ('foo', 'equal'),
    ]


def test_shadiff_renameandnew(wd):
    ''' Test that a left side file is renamed and right is something else
    '''

    wd.makedirs('a')
    wd.makedirs('b')
    wd.wrdata('a/foo', 'foobar')
    wd.wrdata('b/foo', 'something')
    wd.wrdata('b/bar', 'foobar')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    assert list(scan((a, b))) == [
        ('.', 'equal'),
        ('bar', 'right_renamed'),
        ('foo', 'changed'),  # FIXME: Should it be something else?
    ]
