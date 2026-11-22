import re
import sys

import pytest
from pytest import raises

import dirscan as ds
from dirscan import scanfile
from tests.common import Tempdir


def test_scanfile_get_fileheader() -> None:
    """Test the fileheader"""

    # Somewhat idiomatic test
    a = "#!ds:v1\n"

    assert a == scanfile.get_fileheader()


def test_scanfile_empty_file(wd: Tempdir) -> None:
    """Test passing an empty scanfile to read_scanfile() and dirscan"""

    wd.wrdata("a", None)

    with raises(ds.DirscanException, match="Invalid scanfile"):
        ds.read_scanfile("a")

    with raises(NotADirectoryError):
        ds.main(["--debug", "a"])


def test_scanfile_no_access(wd: Tempdir) -> None:
    """Test passing a file with no access to read_scanfile() and dirscan"""

    if sys.platform == "win32":
        pytest.skip("Not supported on windows")

    wd.wrdata("a", None)
    wd.chmod("a", 0x000)

    with raises(PermissionError):
        ds.read_scanfile("a")

    with raises(PermissionError):
        ds.main(["--debug", "a"])


def test_scanfile_is_scanfile(wd: Tempdir) -> None:
    """Test the is_scanfile() method with various file inputs"""

    # Test mundane input first
    assert not ds.is_scanfile("")
    assert not ds.is_scanfile(None)  # type: ignore
    assert not ds.is_scanfile("noexist")

    # Give dir
    wd.makedirs("d1")
    assert not ds.is_scanfile("d1")

    # Give dir with no access
    if sys.platform != "win32":
        wd.makedirs("d2")
        wd.chmod("d2", 0o000)
        assert not ds.is_scanfile("d2")

    # Give empty file
    wd.wrdata("a", None)
    assert not ds.is_scanfile("a")

    # Give file without permission
    if sys.platform != "win32":
        wd.wrdata("p", None)
        wd.chmod("p", 0o000)
        with raises(PermissionError):
            ds.is_scanfile("p")

    # File which is not scanfile
    wd.wrdata("a", ("""foobar"""))
    assert not ds.is_scanfile("a")

    # Too new scanfile version
    wd.wrdata("a", ("""#!ds:v100"""))
    assert not ds.is_scanfile("a")

    # Proper file header
    wd.wrdata("a", ("""#!ds:v1"""))
    assert ds.is_scanfile("a")


def test_scanfile_read_scanfile_file_handling(wd: Tempdir) -> None:
    """Test the read_scanfile()"""

    # Test mundane input first
    with raises(FileNotFoundError):
        ds.read_scanfile("")
    with raises(TypeError):
        ds.read_scanfile(None)  # type: ignore
    with raises(FileNotFoundError):
        ds.read_scanfile("noexist")

    # Give dir
    wd.makedirs("d1")
    exctype = IsADirectoryError
    if sys.platform == "win32":
        exctype = PermissionError
    with raises(exctype):
        ds.read_scanfile("d1")

    # Give dir with no access
    wd.makedirs("d2")
    wd.chmod("d2", 0o000)
    with raises(PermissionError):
        ds.read_scanfile("d2")

    # Give empty file
    wd.wrdata("a", None)
    with raises(ds.DirscanException, match="Invalid scanfile 'a', missing header"):
        ds.read_scanfile("a")

    # Give file without permission
    if sys.platform != "win32":
        wd.wrdata("p", None)
        wd.chmod("p", 0o000)
        with raises(PermissionError):
            ds.read_scanfile("p")

    # File which is not scanfile
    wd.wrdata("a", ("""foobar"""))
    with raises(ds.DirscanException, match="Invalid scanfile 'a', malformed header"):
        ds.read_scanfile("a")

    # Too new scanfile version
    wd.wrdata("a", ("""#!ds:v100"""))
    with raises(ds.DirscanException, match="Invalid scanfile 'a', unsupported version 'v100'"):
        ds.read_scanfile("a")

    # Proper file header, but no data
    wd.wrdata("a", ("""#!ds:v1"""))
    with raises(
        ds.DirscanException, match="Scanfile 'a' contains no data or no top-level directory"
    ):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_fields_minimal(wd: Tempdir) -> None:
    """Test that a correct minimal scanfile is parsed"""

    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
""",
    )
    d = ds.read_scanfile("a")
    assert isinstance(d, ds.DirObj)
    assert d.path == "a"
    assert d.name == "."
    assert d.size == 0
    assert d.mode == 0
    assert d.uid == 0
    assert d.gid == 0
    assert d._mtime == 0


def test_scanfile_read_scanfile_data_fields_empty_lines(wd: Tempdir) -> None:
    """Test that empty lines in a scanfile are ignored"""

    wd.wrdata(
        "a",
        """#!ds:v1

d,,,,,,,.

""",
    )
    d = ds.read_scanfile("a")
    assert isinstance(d, ds.DirObj)


def test_scanfile_read_scanfile_data_fields_comments(wd: Tempdir) -> None:
    """Test that comment lines in a scanfile are ignored"""

    wd.wrdata(
        "a",
        """#!ds:v1
# foobar
d,,,,,,,.
# after
""",
    )
    d = ds.read_scanfile("a")
    assert isinstance(d, ds.DirObj)


def test_scanfile_read_scanfile_data_fields_empty_filename(wd: Tempdir) -> None:
    """Test that an empty path field is rejected"""

    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,
""",
    )
    with raises(
        ds.DirscanException, match=re.escape("Data error, 'path' field (#7) cannot be omitted")
    ):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_fields_trailing_slash(wd: Tempdir) -> None:
    """Test that filenames ending with a slash are rejected"""

    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,./
""",
    )
    with raises(ds.DirscanException, match=re.escape("Data error, empty filename './'")):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_fields_empty_type(wd: Tempdir) -> None:
    """Test that an empty type field is rejected"""

    wd.wrdata(
        "a",
        """#!ds:v1
,,,,,,,.
""",
    )
    with raises(
        ds.DirscanException, match=re.escape("Data error, 'type' field (#1) cannot be omitted")
    ):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_fields_file_type_top(wd: Tempdir) -> None:
    """Test that a file as the top-level object is rejected"""

    wd.wrdata(
        "a",
        """#!ds:v1
f,,,,,,,.
""",
    )
    with raises(
        ds.DirscanException, match="Scanfile 'a' contains no data or no top-level directory"
    ):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_fields_too_few_fields(wd: Tempdir) -> None:
    """Test that a line with too few fields is rejected"""

    wd.wrdata(
        "a",
        """#!ds:v1
d
""",
    )
    with raises(
        ds.DirscanException,
        match=re.escape("Data error, Missing or excess file fields (got 1, want 8)"),
    ):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_fields_incorrect_filetype(wd: Tempdir) -> None:
    """Test that an unknown object type is rejected"""

    wd.wrdata(
        "a",
        """#!ds:v1
q,,,,,,,.
""",
    )
    with raises(ds.DirscanException, match="Data error, Unknown object type 'q'"):
        ds.read_scanfile("a")


@pytest.mark.parametrize(
    "test",
    [
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
    ],
)
def test_scanfile_read_scanfile_data_fields_invalid_data(wd: Tempdir, test: str) -> None:
    """Test that invalid data in the numeric fields is rejected"""

    wd.wrdata(
        "a",
        f"""#!ds:v1
{test}
""",
    )
    with raises(ds.DirscanException, match=re.escape("Field error, invalid literal for int()")):
        ds.read_scanfile("a")


@pytest.mark.parametrize(
    "test",
    [
        "d,-1,,,,,,.",  # size
        "d,,-1,,,,,.",  # mode
        "d,,,-1,,,,.",  # uid
        "d,,,,-1,,,.",  # gid
    ],
)
def test_scanfile_read_scanfile_data_fields_negative_numbers(wd: Tempdir, test: str) -> None:
    """Test that negative numbers in the numeric fields are rejected"""

    wd.wrdata(
        "a",
        f"""#!ds:v1
{test}
""",
    )
    with raises(ds.DirscanException, match="Field error, number must be positive"):
        ds.read_scanfile("a")


# FIXME: Add test of quoting of the data and path fields


def test_scanfile_read_scanfile_data_structures_success_subdir(wd: Tempdir) -> None:
    """Test a subdir without ./ prefix"""

    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,b
""",
    )
    a = ds.read_scanfile("a")
    b = a.children()
    assert a.path == "a"
    assert a.name == "."
    assert len(b) == 1
    assert b[0].path == "."
    assert b[0].name == "b"


def test_scanfile_read_scanfile_data_structures_success_subdir_of_subdir(wd: Tempdir) -> None:
    """Test a subdir of a subdir without ./ prefix"""

    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,b
d,,,,,,,b/c
""",
    )
    a = ds.read_scanfile("a")
    b = a.children()
    c = b[0].children()
    assert a.path == "a"
    assert a.name == "."
    assert len(b) == 1
    assert b[0].path == "."
    assert b[0].name == "b"
    assert len(c) == 1
    assert c[0].path == "./b"
    assert c[0].name == "c"


def test_scanfile_read_scanfile_data_structures_success_subdir_prefix(wd: Tempdir) -> None:
    """Test a subdir with ./ prefix"""

    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,./b
""",
    )
    a = ds.read_scanfile("a")
    b = a.children()
    assert a.path == "a"
    assert a.name == "."
    assert len(b) == 1
    assert b[0].path == "."
    assert b[0].name == "b"


def test_scanfile_read_scanfile_data_structures_success_subdir_of_subdir_prefix(
    wd: Tempdir,
) -> None:
    """Test a subdir of a subdir with ./ prefix"""

    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,./b
d,,,,,,,./b/c
""",
    )
    a = ds.read_scanfile("a")
    b = a.children()
    c = b[0].children()
    assert a.path == "a"
    assert a.name == "."
    assert len(b) == 1
    assert b[0].path == "."
    assert b[0].name == "b"
    assert len(c) == 1
    assert c[0].path == "./b"
    assert c[0].name == "c"


def test_scanfile_read_scanfile_data_structures_success_subroot(wd: Tempdir) -> None:
    """Test reading a scanfile with a successful subroot"""

    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,b
d,,,,,,,b/c
""",
    )
    b = ds.read_scanfile("a", "b")
    c = b.children()
    assert b.path == "."
    assert b.name == "b"
    assert len(c) == 1
    assert c[0].path == "./b"
    assert c[0].name == "c"


def test_scanfile_read_scanfile_data_structures_fails_repeated_top(wd: Tempdir) -> None:
    """Test that a repeated top-level directory is rejected"""

    # Test repeated top
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,.
""",
    )
    with raises(ds.DirscanException, match=re.escape("Data error, '.' already exists in file")):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_structures_fails_allowed_orphan(wd: Tempdir) -> None:
    """Test that an orphan at the top level is allowed"""

    # Test allowed orphan (should not raise an exception)
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,foo
""",
    )
    ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_structures_fails_orphan(wd: Tempdir) -> None:
    """Test that an orphan is rejected"""

    # Test orphan
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,foo/orphan
""",
    )
    with raises(ds.DirscanException, match="Data error, 'foo/orphan' is an orphan"):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_structures_fails_orphan_prefix(wd: Tempdir) -> None:
    """Test that an orphan with ./ prefix is rejected"""

    # Test orphan with ./ prefix
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,./b/c
""",
    )
    with raises(ds.DirscanException, match=re.escape("Data error, './b/c' is an orphan")):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_structures_fails_duplicate_dirs(wd: Tempdir) -> None:
    """Test that duplicate directories are rejected"""

    # Test duplicate dirs
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,b
d,,,,,,,b
""",
    )
    with raises(ds.DirscanException, match="Data error, 'b' already exists in file"):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_structures_fails_duplicate_dirs_prefix(wd: Tempdir) -> None:
    """Test that duplicate directories with ./ prefix are rejected"""

    # Test duplicate dirs with ./ prefix
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,./b
d,,,,,,,./b
""",
    )
    with raises(ds.DirscanException, match=re.escape("Data error, './b' already exists in file")):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_structures_fails_duplicate_files(wd: Tempdir) -> None:
    """Test that duplicate files are rejected"""

    # Test duplicate files
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
f,,,,,,,b
f,,,,,,,b
""",
    )
    with raises(ds.DirscanException, match="Data error, 'b' already exists in file"):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_structures_fails_duplicate_name_different_type(
    wd: Tempdir,
) -> None:
    """Test that a duplicate name with a different filetype is rejected"""

    # Test duplicate name with different filetype
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
d,,,,,,,b
f,,,,,,,b
""",
    )
    with raises(ds.DirscanException, match="Data error, 'b' already exists in file"):
        ds.read_scanfile("a")


def test_scanfile_read_scanfile_data_structures_fails_subroot_not_dir(wd: Tempdir) -> None:
    """Test that a subroot which is not a directory is rejected"""

    # Test subroot which is not dir
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
f,,,,,,,b
""",
    )
    with raises(ds.DirscanException, match="No such directory 'b' found in scanfile 'a'"):
        ds.read_scanfile("a", "b")


def test_scanfile_read_scanfile_data_structures_fails_subroot_missing(wd: Tempdir) -> None:
    """Test that a subroot which does not exist is rejected"""

    # Test subroot that does not exist
    wd.wrdata(
        "a",
        """#!ds:v1
d,,,,,,,.
""",
    )
    with raises(ds.DirscanException, match="No such directory 'b' found in scanfile 'a'"):
        ds.read_scanfile("a", "b")


def test_scanfile_read_scanfile_object_types(wd: Tempdir) -> None:
    """Test the object types returned"""
    wd.wrdata(
        "a",
        (
            """#!ds:v1
d,,,,,,,.
f,,,,,,,f
l,,,,,,,l
b,,,,,,,b
c,,,,,,,c
p,,,,,,,p
s,,,,,,,s
"""
        ),
    )
    d = ds.read_scanfile("a")
    assert isinstance(d, ds.DirObj)
    c = d.children()
    assert isinstance(c[0], ds.FileObj)
    assert isinstance(c[1], ds.LinkObj)
    assert isinstance(c[2], ds.BlockDevObj)
    assert isinstance(c[3], ds.CharDevObj)
    assert isinstance(c[4], ds.FifoObj)
    assert isinstance(c[5], ds.SocketObj)


ENCODES = [
    # (which, encode/decode, unencoded_text, encoded_text)
    ("all", "ed", "ABCDEF", "ABCDEF"),
    ("all", "ed", "/\\", "/\\\\"),  # /\ -> /\\ Backslash-quoting
    ("all", "ed", "\x00\x01\x7f", "\\x00\\x01\\x7f"),  # Low values quoting
    ("all", "ed", "\U0001f44d", "👍"),  # Unicode emoji, as utf-8 \xf0\x9f\x99\x8f
    ("all", "ed", "👍", "👍"),
    ("all", "ed", "Δ", "Δ"),
    ("all", "ed", "æ", "æ"),  # As utf-8 \xc3\xa6
    ("all", "ed", "\udcfa", "\\xfa"),  # Surrogate escape for 0x80-0xff on some file systems
    ("all", "ed", "\udc6d", "\\udc6d"),  # Surrogate outside the python range
    ("all", "ed", "@Δ😇ab", "@Δ😇ab"),
    ("all", "d", "\x40\u0394\U0001f607ab", "\\x40\\u0394\\U0001f607ab"),
    ("all", "d", "\n", "\\n"),
    ("text", "ed", ",", ","),
    ("text", "ed", " ", " "),
    ("text", "ed", "-", "-"),
    ("text", "ed", "\\-", "\\\\-"),
    ("text", "ed", "\\,", "\\\\,"),
    ("text", "ed", "\\ ", "\\\\ "),
    ("file", "ed", "-", "-"),
    ("file", "e", " ", "\\ "),  # Encode only, when ' ' encodes to '\\ '
    ("file", "d", " ", " "),  # Decode only
    ("file", "d", " ", "\\ "),  # Decode only
    ("file", "ed", ",", "\\-"),
    ("file", "ed", "\\-", "\\\\-"),
    ("file", "ed", "\\,", "\\\\\\-"),
    ("file", "ed", "\\\\-", "\\\\\\\\-"),
    ("file", "e", "\\ ", "\\\\\\ "),  # Encode only, when ' ' encodes to '\\ '
    ("file", "d", "\\ ", "\\\\ "),  # Decode only
    ("file", "d", "\\ ", "\\\\\\ "),  # Decode only
]


@pytest.mark.parametrize(
    "d, a, b",
    [(d, a, b) for i, d, a, b in ENCODES if i in ("all", "text")],
)
def test_scanfile_quote_text(d: str, a: str, b: str) -> None:  # text_quoter():
    """Test quoting and unquoting of text fields"""

    if "e" in d:
        q = scanfile.text_quote(a)
        assert b == q

    if "d" in d:
        u = scanfile.text_unquote(b)
        assert a == u


@pytest.mark.parametrize(
    "d, a, b",
    [(d, a, b) for i, d, a, b in ENCODES if i in ("all", "file")],
)
def test_scanfile_quote_file(d: str, a: str, b: str) -> None:  # _quoter():
    """Test quoting and unquoting of file path fields"""

    q = u = ""

    if "e" in d:
        q = scanfile.file_quote(a)
        assert b == q

    if "d" in d:
        u = scanfile.file_unquote(b)
        assert a == u


def test_scanfile_quote_invalid() -> None:
    """Test that invalid quoted input is handled or rejected"""

    # Test do-nothing result
    a = "SIMPLE"
    assert a == scanfile.file_unquote(a)

    # Test invalid quote symbol
    a = "\\q"
    with raises(ds.DirscanException, match="Unknown escape char"):
        scanfile.file_unquote(a)

    # Test unfinished string
    a = "End\\"
    with raises(ds.DirscanException, match="Incomplete escape string"):
        scanfile.file_unquote(a)
