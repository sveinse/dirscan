'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2022 Svein Seldal
This code is licensed under MIT license (see LICENSE for details)
URL: https://github.com/sveinse/dirscan
'''
import os
from pathlib import Path

from dirscan.dirscan import DirscanException, create_from_dict
from dirscan.log import debug_level


# Known scan file versions
SCANFILE_VERSIONS = ('v1',)

# Line fields of the scanfile
SCANFILE_FORMAT = "{type},{size},{mode:o},{uid},{gid},{mtime_x},{data:qs},{relpath_p:qs}"


def is_scanfile(filename):
    ''' Check if the given file is a scanfile. It will return a boolean with
        the results, unless it is unable to read the file
    '''

    if not filename:
        return False
    filename = Path(filename)
    if not filename.is_file():
        return False
    try:
        with open(filename, 'r', errors='surrogateescape') as infile:
            check_header(infile.readline(), filename)
    except DirscanException:
        return False

    return True


def get_fileheader():
    ''' Return the file header of the scan-file '''
    return '#!ds:v1\n'


def check_header(line, filename):
    ''' Check if line from filename is a correct dirscan scanfile header '''

    if not line:
        raise DirscanException(f"Invalid scanfile '{filename}', missing header")
    line = line.rstrip()

    if not line.startswith('#!ds:v'):
        raise DirscanException(f"Invalid scanfile '{filename}', malformed header")

    ver = line[5:]
    if ver not in SCANFILE_VERSIONS:
        raise DirscanException(f"Invalid scanfile '{filename}', unsupported version '{ver}'")


def int_positive(value, radix=10):
    ''' Call int() and raise an ValueError if number is negative '''

    num = int(value or '0', radix)
    if num < 0:
        raise ValueError("Number must be positive")
    return num


def read_scanfile(filename, root=None):
    ''' Read filename scan file and return a DirObj() with the file tree root '''

    base_fname = Path(filename).name

    # Set a default value
    if not root:
        root = '.'

    dirtree = {}

    # First pass reading entire file into memory
    with open(filename, 'r', errors='surrogateescape') as infile:

        # Check the scanfile header
        check_header(infile.readline(), filename)

        lineno = 1
        for line in infile:
            lineno += 1

            # Ignore empty line and lines with comments
            if not line.rstrip() or line[0] == '#':
                continue

            try:
                # Parse the line record
                args = [unquote(e) for e in line.rstrip().split(',')]
                length = len(args)
                if length != 8:
                    raise DirscanException(f"Missing or excess file fields (got {length}, want 8)")
                try:
                    # Must be kept in sync with self.FORMAT
                    data = {
                        'objtype':  args[0],
                        'size': int_positive(args[1]),
                        'mode': int_positive(args[2], 8),  # Octal input
                        'uid': int_positive(args[3]),
                        'gid': int_positive(args[4]),
                        'mtime': float(int_positive(args[5], 16)),  # Hex input,
                    }
                    objpath = args[7]

                    # Parse the 'data' field - args[6]
                    objtype = data['objtype']
                    if objtype == 'f':  # Files
                        data['hashsum'] = args[6] or False
                    elif objtype == 'l':  # Link
                        data['link'] = args[6] or None
                    elif objtype == 'd':  # Directory
                        data['children'] = ()

                except ValueError as err:
                    raise DirscanException("Scanfile field error: " + str(err)) from None
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
                    fpath = ''
                    fname = base_fname

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

                if objtype == 'd':
                    # Add this new dir object to the dict of directories
                    if relpath in dirtree:
                        raise DirscanException(f"'{objpath}' already exists in file")
                    # (parent, children, path)
                    dirtree[str(relpath)] = (fileobj, {}, fpath + '/' + fname if fpath else fname)

                if parent:
                    # Add the object into the parent's children list
                    if name in parent[1]:
                        raise DirscanException(f"'{objpath}' already exists in file")
                    parent[1][name] = fileobj

            except DirscanException as err:
                exc = err if debug_level() else None
                raise DirscanException(f"{filename}:{lineno}: Data error, {err}") from exc

    # Second pass, inserting all the children into the list of parents,
    # building up the final tree structure
    for parent, children, _ in dirtree.values():

        # Insert the children into the parent object
        parent.set_children(tuple(children.values()))

    if not dirtree:
        raise DirscanException(f"Scanfile '{filename}' contains no data or no top-level directory")

    # Now the tree should be populated
    try:
        return dirtree['./' + root if root[0] != '.' else root][0]

    except KeyError:
        raise DirscanException(f"No such directory '{root}' found in scanfile '{filename}'") from None



# SIMPLE QUOTER USED IN SCAN FILES
# ================================
#
#     '\' -> '\\'
#     ' ' -> '\ '
#     ',' -> '\-'
#     <32 and 127-255 -> '\xNN'
#

def text_quoter(text):
    ''' Quote the text for printing '''

    out = ''
    for char in text:
        value = ord(char)
        if value < 32 or value == 127:
            out += f"\\x{value:02x}"
        # elif v == 32:  # ' '
        #     out += '\\ '
        # elif v == 44:  # ','
        #    out += '\\-'
        elif value == 92:  # '\'
            out += '\\\\'
        else:
            out += char

    try:
        text.encode('utf-8')
    except UnicodeEncodeError:
        # Strings with encoding errors will come up as surrogates, which
        # will fail the encode. This code will make the str into a bytes
        # object and back to a string, where surrogates will be escaped
        # as \xNN. [2:-1] removes the b' prefix and ' postfix
        out = str(os.fsencode(out))[2:-1]

    return out


def file_quoter(text):
    ''' Simple text quoter for the scan files '''

    text = text_quoter(text)

    # Special scan file escapings
    if ',' in text:
        text = text.replace(',', '\\-')
    if ' ' in text:
        text = text.replace(' ', '\\ ')
    return text


def unquote(text):
    ''' Simple text un-quoter for the scan files '''

    if '\\' not in text:
        return text
    out = ''
    getchars = 0
    escape = False
    hexstr = ''
    for char in text:

        if getchars:
            # Getting char value for \xNN escape codes
            hexstr += char
            getchars -= 1
            if getchars == 0:
                value = int(hexstr, 16)
                # Code-points above 128 must be made into a surrogate
                # for the quoter to work with this values
                if value >= 128:
                    value |= 0xdc00
                out += chr(value)

        elif escape:
            # Getting escape code following '\'
            if '\\' in char:
                out += '\\'
            elif '-' in char:
                out += ','
            elif ' ' in char:
                out += ' '
            elif 'x' in char:
                getchars = 2
                hexstr = ''
            else:
                raise DirscanException(f"Unknown escape char '{char}'")
            escape = False

        elif '\\' in char:
            escape = True

        else:
            out += char

    if escape or getchars:
        raise DirscanException(f"Incomplete escape string '{text}'")
    return out
