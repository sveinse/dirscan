import dirscan as ds
from pytest import raises


def test_compare1_two_dirs(wd):
    """ Test that dir_compare1 doesn't accept multiple dirs """

    wd.makedirs('a')

    a = ds.create_from_fs('a')

    with raises(AssertionError):
        cmp = ds.dir_compare1(tuple())
    with raises(AssertionError):
        cmp = ds.dir_compare1((a,a))
    with raises(AssertionError):
        cmp = ds.dir_compare1((a,a,a))


def test_compare1_scan(wd):
    """ Test """

    wd.makedirs('a')

    a = ds.create_from_fs('a')

    cmp = ds.dir_compare1((a,))
    assert cmp == ('scan', 'scan')


def test_compare1_exclude(wd):
    """ Test """

    wd.makedirs('a')

    a = ds.create_from_fs('a')
    a.excluded = True

    cmp = ds.dir_compare1((a,))
    assert cmp == ('excluded', 'excluded')


def test_compare2_two_dirs(wd):
    """ Test that dir_compare2 doesn't accept multiple dirs """

    wd.makedirs('a')

    a = ds.create_from_fs('a')

    with raises(AssertionError):
        cmp = ds.dir_compare2(tuple())
    with raises(AssertionError):
        cmp = ds.dir_compare2((a,))
    with raises(AssertionError):
        cmp = ds.dir_compare2((a,a,a))


def test_compare2_exclude(wd):
    """ Test compares involving exclusions """

    wd.makedirs('a')
    wd.makedirs('b')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')
    c = ds.NonExistingObj('c')

    a.excluded = True
    b.excluded = True
    c.excluded = True

    cmp = ds.dir_compare2((a,b))
    assert cmp == ('excluded', 'excluded')

    cmp = ds.dir_compare2((a,c))
    assert cmp == ('excluded', 'Left excluded')

    cmp = ds.dir_compare2((c,b))
    assert cmp == ('excluded', 'Right excluded')

    a.excluded = False
    b.excluded = True
    c.excluded = True

    cmp = ds.dir_compare2((a,b))
    assert cmp == ('left_only', 'directory only in left, right is excluded')

    cmp = ds.dir_compare2((a,c))
    assert cmp == ('left_only', 'directory only in left, right is excluded')

    a.excluded = True
    b.excluded = False
    c.excluded = True

    cmp = ds.dir_compare2((a,b))
    assert cmp == ('right_only', 'directory only in right, left is excluded')

    cmp = ds.dir_compare2((c,b))
    assert cmp == ('right_only', 'directory only in right, left is excluded')

    a.excluded = True
    b.excluded = True
    c.excluded = False

    cmp = ds.dir_compare2((a,c))
    assert cmp == ('excluded', 'excluded, only in left')

    cmp = ds.dir_compare2((c,b))
    assert cmp == ('excluded', 'excluded, only in right')


def test_compare2_types(wd):
    """ Test mismatching types """

    wd.makedirs('a')
    wd.wrdata('b', '')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    cmp = ds.dir_compare2((a,b))
    assert cmp == ('different_type', 'Different type, directory in left and file in right')


def test_compare2_comparetype(wd):
    """ Test when compare is ignored """

    wd.makedirs('a')
    wd.makedirs('b')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    cmp = ds.dir_compare2((a,b), comparetypes='')
    assert cmp == ('skipped', 'compare skipped')


def test_compare2_equal(wd):
    """ Test for equality """

    wd.wrdata('a', 'foobar')
    wd.wrdata('b', 'foobar')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    cmp = ds.dir_compare2((a,b))
    assert cmp == ('equal', 'equal')


def test_compare2_change(wd):
    """ Test for changed file contents """

    wd.wrdata('a', 'foobar')
    wd.wrdata('b', 'foobas')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    cmp = ds.dir_compare2((a,b))
    assert cmp == ('changed', 'file changed: contents differs')


def test_compare2_change_size(wd):
    """ Test for changed file contents """

    wd.wrdata('a', 'foobar')
    wd.wrdata('b', 'foobar!')

    a = ds.create_from_fs('a')
    b = ds.create_from_fs('b')

    cmp = ds.dir_compare2((a,b))
    assert cmp == ('changed', 'file changed: size differs')
