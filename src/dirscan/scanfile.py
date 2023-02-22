''' Dirscan - functions for reading and writing scanfiles '''
#
# Copyright (C) 2010-2023 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

from typing import Any, Dict, Generator, Optional, Tuple
import os
from pathlib import Path

from dirscan.dirscan import DirscanException, create_from_dict, TPath
from dirscan.dirscan import DirscanObj, DirObj, DirscanDict
from dirscan.log import debug_level


# Known scan file versions
SCANFILE_VERSIONS = ('v1',)

# Line fields of the scanfile
SCANFILE_FORMAT = "{type},{size},{mode:o},{uid},{gid},{mtime_x},{data:qs},{relpath_p:qs}"

# Typing
TDirtree = Dict[str, Tuple[DirObj, Dict[str, DirscanObj], str]]


def is_scanfile(filename: TPath) -> bool:
    '''
    Check if the given file is a scanfile

    Args:
        filename: Filename to check
    Returns:
        ``True`` if the given file is a scan file.
    '''

    if not filename:
        return False
    fname = Path(filename)
    if not fname.is_file():
        return False
    try:
        with open(fname, 'r', encoding='utf-8', errors='surrogateescape') as infile:
            check_header(infile.readline(), fname)
    except DirscanException:
        return False

    return True


def get_fileheader() -> str:
    ''' Return the file header of the scan-file '''
    return '#!ds:v1\n'


def check_header(line: str, filename: TPath) -> None:
    ''' Check if line from filename is a correct dirscan scanfile header '''

    if not line:
        raise DirscanException(f"Invalid scanfile '{filename}', missing header")
    line = line.rstrip()

    if not line.startswith('#!ds:v'):
        raise DirscanException(f"Invalid scanfile '{filename}', malformed header")

    ver = line[5:]
    if ver not in SCANFILE_VERSIONS:
        raise DirscanException(f"Invalid scanfile '{filename}', unsupported version '{ver}'")


def int_positive(value: str, radix: int=10) -> int:
    ''' Call int() and raise an ValueError if number is negative '''

    num = int(value or '0', radix)
    if num < 0:
        raise ValueError("number must be positive")
    return num


def read_scanfile(filename: TPath, root: Optional[str]=None) -> DirObj:
    '''
    Read filename scan file and return a :py:class:`DirObj` instance containing
    the file tree root

    Args:
        filename: Filename to read
        root: The path to use as root from the scanfile. The value is ``.`` if
            unset which will use the top object in the file as root. Setting
            another value will use the sub-entry as root. This can be
            used to load a subset of the scanfile.

    Returns:
        Top-level :py:class:`DirObj` object in the hierarchy loaded from the
        file.
    '''

    base_fname = Path(filename).name

    # Set a default value
    if not root:
        root = '.'

    dirtree: TDirtree = {}

    # First pass reading entire file into memory
    with open(filename, 'r', encoding='utf-8', errors='surrogateescape') as infile:

        # Check the scanfile header
        check_header(infile.readline(), filename)

        lineno = 1
        for line in infile:
            lineno += 1

            # Ignore empty line and lines with comments
            if not line.rstrip() or line[0] == '#':
                continue

            try:
                # Parse each line and insert into dirtree
                parse_line(line, base_fname, dirtree)

            except ValueError as err:
                exc1 = err if debug_level() else None
                raise DirscanException(f"{filename}:{lineno}: Field error, "
                                       f"{err}") from exc1

            except DirscanException as err:
                exc2 = err if debug_level() else None
                raise DirscanException(f"{filename}:{lineno}: Data error, "
                                       f"{err}") from exc2

    # Second pass, inserting all the children into the list of parents,
    # building the entire tree structure
    for dparent, children, _ in dirtree.values():

        # Insert the children into the parent object
        dparent.set_children(children.values())

    if not dirtree:
        raise DirscanException(f"Scanfile '{filename}' contains no data "
                               "or no top-level directory")

    # Now the tree should be populated
    try:
        return dirtree['./' + root if root[0] != '.' else root][0]

    except KeyError:
        raise DirscanException(f"No such directory '{root}' "
                               f"found in scanfile '{filename}'") from None


def parse_line(line: str, base_fname: str, dirtree: TDirtree) -> None:
    ''' Parse line and inject into dirtree dict '''

    # Parse the line record
    args = [file_unquote(e) for e in line.rstrip().split(',')]
    length = len(args)
    if length != 8:
        raise DirscanException("Missing or excess file fields "
                               f"(got {length}, want 8)")

    # Must be kept in sync with self.FORMAT
    data: DirscanDict = {
        'objtype':  args[0],
        'name': '',  # Will be updated below
        'path': '',  # Will be updated below
        'size': int_positive(args[1]),
        'mode': int_positive(args[2], 8),  # Octal input
        'uid': int_positive(args[3]),
        'gid': int_positive(args[4]),
        'mtime': float(int_positive(args[5], 16)),  # Hex input,
        'dev': 0,
    }
    objpath = args[7]

    # Parse the 'data' field - args[6]
    objtype = data['objtype']
    if objtype == 'f':  # Files
        data['hashsum'] = args[6] or ''
    elif objtype == 'l':  # Link
        data['link'] = args[6] or ''
    elif objtype == 'd':  # Directory
        data['children'] = ()

    if not objtype:
        raise DirscanException("'type' field (#1) cannot be omitted")
    if not objpath:
        raise DirscanException("'path' field (#7) cannot be omitted")

    relpath = objpath
    if relpath[0] != '.':
        # Don't use Path for this, as the './' is important
        relpath = './' + relpath

    # Set file object path and name
    path, name = os.path.split(relpath)
    fpath, fname = path, name

    # First top-level entry has path='', name='.'.
    if path == '' and name == '.':
        # In the top-level entry the scan filename as path, while keeping
        # the name empty
        fpath = base_fname
        fname = ''

    # First level entries has path='.', name=*
    elif path == '.':
        fpath = base_fname

    else:
        # Prefix path with the base filename
        fpath = base_fname + '/' + path[2:]

    if not name:
        raise DirscanException(f"empty filename '{objpath}'")

    # Get the parent dict
    parent = dirtree.get(str(path))
    if not parent and path:
        raise DirscanException(f"'{objpath}' is an orphan")

    data['name'] = fname
    data['path'] = parent[2] if parent else fpath

    # Create new file object
    fileobj = create_from_dict(data)

    if isinstance(fileobj, DirObj):
        # Add this new dir object to the dict of directories
        if relpath in dirtree:
            raise DirscanException(f"'{objpath}' already exists in file")
        # (parent, children, path)
        dirtree[str(relpath)] = (
            fileobj, {}, fpath + '/' + fname if fname else fpath)

    if parent:
        # Add the object into the parent's children list
        if name in parent[1]:
            raise DirscanException(f"'{objpath}' already exists in file")
        parent[1][name] = fileobj


# SIMPLE QUOTER USED IN SCAN FILES
# ================================

def quote(text: str, extended: bool=False) -> str:
    ''' Quote the text '''

    def _quote(text: str) -> Generator[str, None, None]:
        ext = extended
        for c in text:
            v = ord(c)
            if v < 32 or v == 127:   # n -> \xnn
                yield f"\\x{v:02x}"
            elif c == '\\':          # \ -> \\
                yield '\\\\'
            elif ext and c == ',':   # , -> \\-
                yield '\\-'          # To not interfere when reading file
            elif ext and c == ' ':   # ' ' -> '\\ '
                yield '\\ '          # To remain quotable with shell pasting
            else:
                yield c

    text = "".join(_quote(text))
    try:
        # Need this to encode surrogates \udcfa -> \\xfa
        btext = text.encode(errors='surrogateescape')
    except UnicodeEncodeError:
        # But fails on other surrogates, so \udc6d -> \\udc6d
        btext = text.encode(errors='backslashreplace')
    text = btext.decode(errors='backslashreplace')
    return text


def unquote(text: str, extended: bool=False) -> str:
    ''' Unquote the text '''

    def _unqoute(text: str) -> Generator[str, None, None]:

        # Escape code translations
        escapes = {
            '\\': '\\',
            'n': '\n',
            'r': '\r',
            't': '\t',
            "'": "'",
            '"': '"',
        }
        if extended:
            escapes.update({
                '-': ',',
                ' ': ' ',
            })

        it = iter(text)
        while True:
            try:
                c = next(it)
                if c != '\\':
                    yield c
                    continue
            except StopIteration:
                return

            try:
                c = next(it)
                out = escapes.get(c)
                if out is not None:
                    yield out
                    continue
                if c not in 'xuU':
                    raise DirscanException(f"Unknown escape char '{c}'")
                capture = {'x': 2, 'u': 4, 'U': 8}[c]
                cap = "".join(next(it) for i in range(capture))
                val = int(cap, 16)
                if val > 127 and val < 256:
                    val |= 0xdc00  # Handle surrogates
                yield chr(val)
            except StopIteration:
                raise DirscanException(f"Incomplete escape string '{text}'") from None

    return "".join(_unqoute(text))


def text_quote(text: str) -> str:
    ''' Quote the text for printing '''
    return quote(text, False)


def file_quote(text: str) -> str:
    ''' Simple text quoter for the scan files '''
    return quote(text, True)


def text_unquote(text: str) -> str:
    ''' Simple text un-quoter for the scan files '''
    return unquote(text, False)


def file_unquote(text: str) -> str:
    ''' Simple text un-quoter for the scan files '''
    return unquote(text, True)
