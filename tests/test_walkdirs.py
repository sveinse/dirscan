import sys
from pathlib import Path

import pytest
from pytest import raises

import dirscan as ds
from dirscan.dirscan import *
from tests.common import ExpectedT, Tempdir


def test_walkdirs_no_access_to_topdir(wd: Tempdir) -> None:
    """Test scanning a dir with no access"""

    if sys.platform == "win32":
        pytest.skip("Not supported on windows")

    wd.makedirs("a")
    wd.chmod("a", 0o000)

    # Direct call
    with raises(PermissionError):
        for _ in ds.walkdirs(("a",)):
            pass

    # Cmd line
    with raises(PermissionError):
        ds.main(["--debug", "a"])


def test_walkdirs_top_is_not_a_dir(wd: Tempdir) -> None:
    """Test giving a file to scan instead of a dir"""

    wd.wrdata("a", None)

    # Direct call
    with raises(NotADirectoryError):
        for _ in ds.walkdirs(("a",)):
            pass

    # Cmd line
    with raises(NotADirectoryError):
        ds.main(["--debug", "a"])


def test_walkdirs_top_is_not_existing(wd: Tempdir) -> None:
    """Test scanning a path that doesn't exist"""

    # Direct call
    with raises(FileNotFoundError):
        for _ in ds.walkdirs(("noexist",)):
            pass

    # Cmd line
    with raises(FileNotFoundError):
        ds.main(["--debug", "noexist"])


def test_walkdirs_empty_dirlist(wd: Tempdir) -> None:
    """Test passing empty lists to walkdirs()"""

    ds.set_debug(1)

    expect = (((Path(".")), ()),)

    # Empty list
    result = tuple(ds.walkdirs([]))
    assert result == expect

    # None list
    with raises(TypeError):
        for _ in ds.walkdirs(None):  # type: ignore
            pass


TEST_TREE = [
    ("x", "f", ""),
    ("b", "d", None),
    ("b/y", "f", "abc"),
    ("c", "d", None),
]


def test_walkdirs_scan1(wd: Tempdir) -> None:
    """Test basic walkdirs scan with a single directory"""

    wd.maketree("a", TEST_TREE)

    expected = [
        (".", DirObj),
        ("b", DirObj),
        ("b/y", FileObj),
        ("c", DirObj),
        ("x", FileObj),
    ]

    tree = ds.walkdirs(["a"])
    wd.compare(tree, expected)


def test_walkdirs_scan2(wd: Tempdir) -> None:
    """Test walkdirs scan with multiple directories"""

    wd.maketree("a", TEST_TREE)
    wd.maketree("b", TEST_TREE)

    expected = [
        (".", DirObj, DirObj),
        ("b", DirObj, DirObj),
        ("b/y", FileObj, FileObj),
        ("c", DirObj, DirObj),
        ("x", FileObj, FileObj),
    ]

    tree = ds.walkdirs(["a", "b"])
    wd.compare(tree, expected)


def test_walkdirs_scan3(wd: Tempdir) -> None:
    """Test walkdirs scan with three directories"""

    wd.maketree("a", TEST_TREE)
    wd.maketree("b", TEST_TREE)
    wd.maketree("c", TEST_TREE)

    expected = [
        (".", DirObj, DirObj, DirObj),
        ("b", DirObj, DirObj, DirObj),
        ("b/y", FileObj, FileObj, FileObj),
        ("c", DirObj, DirObj, DirObj),
        ("x", FileObj, FileObj, FileObj),
    ]

    tree = ds.walkdirs(["a", "b", "c"])
    wd.compare(tree, expected)


def test_walkdirs_scan_reverse(wd: Tempdir) -> None:
    """Test walkdirs scan in reverse order"""

    wd.maketree("a", TEST_TREE)

    expected = [
        (".", DirObj),
        ("x", FileObj),
        ("c", DirObj),
        ("b", DirObj),
        ("b/y", FileObj),
    ]

    tree = ds.walkdirs(["a"], reverse=True)
    wd.compare(tree, expected)


def test_walkdirs_traverse_into_onesided_scan(wd: Tempdir) -> None:
    """Test walkdirs scan with traverse_into_oneside setting"""

    wd.maketree("a", TEST_TREE)

    expected = [
        (".", DirObj),
        ("b", DirObj),
        ("b/y", FileObj),
        ("c", DirObj),
        ("x", FileObj),
    ]

    tree = ds.walkdirs(["a"], traverse_into_oneside=False)
    wd.compare(tree, expected)
    tree = ds.walkdirs(["a"], traverse_into_oneside=True)
    wd.compare(tree, expected)


TEST_TREE_NO_B = [
    ("x", "f", ""),
    ("c", "d", None),
]


def test_walkdirs_traverse_into_onesided_scan2(wd: Tempdir) -> None:
    """Test walkdirs scan with traverse_into_oneside setting for two directories"""

    wd.maketree("a", TEST_TREE)
    wd.maketree("b", TEST_TREE_NO_B)

    expected = [
        (".", DirObj, DirObj),
        ("b", DirObj, NonExistingObj),
        # ('b/y', FileObj, FileObj),
        ("c", DirObj, DirObj),
        ("x", FileObj, FileObj),
    ]
    tree = ds.walkdirs(["a", "b"], traverse_into_oneside=False)
    wd.compare(tree, expected)

    expected2 = [
        (".", DirObj, DirObj),
        ("b", DirObj, NonExistingObj),
        ("b/y", FileObj, NonExistingObj),
        ("c", DirObj, DirObj),
        ("x", FileObj, FileObj),
    ]
    tree = ds.walkdirs(["a", "b"], traverse_into_oneside=True)
    wd.compare(tree, expected2)


def test_walkdirs_traverse_into_onesided_scan3(wd: Tempdir) -> None:
    """Test walkdirs scan with traverse_into_oneside setting for three directories"""

    wd.maketree("a", TEST_TREE)
    wd.maketree("b", TEST_TREE)
    wd.maketree("c", TEST_TREE_NO_B)

    wd.maketree("d", TEST_TREE)
    wd.maketree("e", TEST_TREE_NO_B)
    wd.maketree("f", TEST_TREE_NO_B)

    expected_false1 = [
        (".", DirObj, DirObj, DirObj),
        ("b", DirObj, DirObj, NonExistingObj),
        ("b/y", FileObj, FileObj, NonExistingObj),
        ("c", DirObj, DirObj, DirObj),
        ("x", FileObj, FileObj, FileObj),
    ]
    expected_false2 = [
        (".", DirObj, DirObj, DirObj),
        ("b", DirObj, NonExistingObj, NonExistingObj),
        # ('b/y', FileObj, NonExistingObj, NonExistingObj),
        ("c", DirObj, DirObj, DirObj),
        ("x", FileObj, FileObj, FileObj),
    ]

    tree = ds.walkdirs(["a", "b", "c"], traverse_into_oneside=False)
    wd.compare(tree, expected_false1)
    tree = ds.walkdirs(["d", "e", "f"], traverse_into_oneside=False)
    wd.compare(tree, expected_false2)

    expected_true1 = expected_false1
    expected_true2 = [
        (".", DirObj, DirObj, DirObj),
        ("b", DirObj, NonExistingObj, NonExistingObj),
        ("b/y", FileObj, NonExistingObj, NonExistingObj),
        ("c", DirObj, DirObj, DirObj),
        ("x", FileObj, FileObj, FileObj),
    ]

    tree = ds.walkdirs(["a", "b", "c"], traverse_into_oneside=True)
    wd.compare(tree, expected_true1)
    tree = ds.walkdirs(["d", "e", "f"], traverse_into_oneside=True)
    wd.compare(tree, expected_true2)


def test_walkdirs_exclude(wd: Tempdir) -> None:
    """Test walkdirs with exclusion of certain directories"""

    wd.maketree("a", TEST_TREE)

    expected: list[ExpectedT] = [
        (".", DirObj),
        ("b", {"obj": DirObj, "excluded": True}),
        # ('b/y', FileObj),  # Excluded
        ("c", DirObj),
        ("x", FileObj),
    ]

    tree = ds.walkdirs(["a"], excludes=["b"])
    wd.compare(tree, expected)


def _test_walkdirs_dirofdir(wd: Tempdir) -> None:
    """Test walkdirs with directories containing other directories"""

    pytest.skip("Not complete yet")

    # FIXME: Test the top-level Dirobject name and path, both from fs and
    # from scanfile

    wd.maketree("a", [("a", "d", None), ("a/b", "f", None)])

    print()
    for a in ds.walkdirs(("a/a",)):
        print(a, tuple(str(o.fullpath) for o in a[1]))

    ds.main(["a/a", "-o", "scan.out"])
    with open("scan.out", "r") as f:
        d = f.read()
    print(d)

    wd.wrdata(
        "a.scan",
        (
            """#!ds:v1
d,0,777,0,0,0,,.
f,0,666,0,0,0,,b
"""
        ),
    )

    top = ds.read_scanfile("a.scan")
    for a in ds.walkdirs((top,)):
        print(a, tuple(str(o.fullpath) for o in a[1]))

    # FIXME: This
    assert False
