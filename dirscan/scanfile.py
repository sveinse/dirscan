'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2021 Svein Seldal, sveinse@seldal.com
URL: https://github.com/sveinse/dirscan

This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.
'''
import os

from dirscan.dirscan import DirscanException, create_from_data


class ScanFIleException(DirscanException):
    ''' Scan-file exceptions '''


# Known scan file versions
SCANFILE_VERSIONS = ('v1',)


def is_scanfile(filename):
    ''' Check if the given file is a scanfile. It will return a boolean with
        the results, unless it is unable to read the file
    '''

    if not filename or not os.path.isfile(filename):
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


class ScanfileRecord:
    ''' Scan file record '''

    __slots__ = ('type', 'size', 'mode', 'uid', 'gid', 'mtime', 'data', 'path', 'name', 'filepath')

    # File format for serialized data-file
    FORMAT = "{type},{size},{mode:o},{uid},{gid},{mtime_x},{data:qs},{relpath:qs}"

    def __init__(self, parse, base_fname=None):
        args = [unquote(e) for e in parse.rstrip().split(',')]
        length = len(args)
        if length != 8:
            raise DirscanException(f"Missing or excess file fields (got {length}, want 8)")
        try:
            # Must be kept in sync with self.FORMAT
            self.type = args[0]
            self.size = int_positive(args[1])
            self.mode = int_positive(args[2], 8)  # Octal input
            self.uid = int_positive(args[3])
            self.gid = int_positive(args[4])
            self.mtime = float(int_positive(args[5], 16))  # Hex input
            self.data = args[6] or None
            filepath = args[7]
        except ValueError as err:
            raise DirscanException("Scanfile field error: " + str(err)) from None
        if not self.type:
            raise DirscanException("'type' field cannot be omitted")
        if not filepath:
            raise DirscanException("'path' field cannot be omitted")

        (path, name) = os.path.split(filepath)

        if not name:
            raise DirscanException(f"empty filename '{filepath}'")

        # Set file object path and name
        if path == '':
            # First top-level entry has path='', name='.'.
            # Rewrite into path='', name=filename
            if name == '.':
                name = base_fname
            else:
                path = base_fname
                #raise DirscanException(f"unexpected top-level entity '{filepath}'")
        elif path == '.':
            # First level entries has path='.'
            # Rewrite into path=filename
            path = base_fname
        elif path.startswith('./'):
            # Rewrite into path='filename/something...'
            path = os.path.join(base_fname, path[2:])
        else:
            # All other has path='something...'
            # Rewrite into path='filename/something...'
            path = os.path.join(base_fname, path)
        #else:
            # path does not start with './'
            #raise DirscanException(f"malformed path '{filepath}'")

        # If path do not have './' as prefix, it will fall though here unchanged

        # Filepath contains the unparsed fileparse as represented in file, while
        # path and name are processed
        self.filepath = filepath
        self.path = path
        self.name = name


def read_scanfile(filename, root=None):
    ''' Read filename scan file and return a DirObj() with the file tree root '''

    base_fname = os.path.basename(filename)

    # Set a default value
    if not root:
        root = '.'
        droot = base_fname
    else:
        droot = os.path.join(base_fname, root)

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
                # Read/parse the record
                data = ScanfileRecord(line, base_fname=base_fname)

                # Split path into path and name
                path = data.path
                fullpath = os.path.join(path, data.name)

                # Get the parent dict
                parent = dirtree.get(path)
                if not parent and path:
                    raise DirscanException(f"'{data.filepath}' is an orphan")

                # # Create new file object
                fileobj = create_from_data(
                    name=data.name,
                    path=parent[2] if parent else data.path,
                    objtype=data.type,
                    size=data.size,
                    mode=data.mode,
                    uid=data.uid,
                    gid=data.gid,
                    mtime=data.mtime,
                    data=data.data
                )

                if data.type == 'd':
                    # Add this new dir object to the dict of directories
                    if fullpath in dirtree:
                        raise DirscanException(f"'{data.filepath}' already exists in file")
                    dirtree[fullpath] = (fileobj, {}, fullpath)  # (parent, children, path)

                if parent:
                    # Add the object into the parent's children list
                    if data.name in parent[1]:
                        raise DirscanException(f"'{data.filepath}' already exists in file")
                    parent[1][data.name] = fileobj

            except DirscanException as err:
                raise DirscanException(f"{filename}:{lineno}: Data error, {err}") from None

    # Second pass, inserting all the children into the list of parents,
    # building up the final tree structure
    for parent, children, _ in dirtree.values():

        # Insert the children into the parent object
        parent.set_children(tuple(children.values()))

    if not dirtree:
        raise DirscanException(f"Scanfile '{filename}' contains no data or no top-level directory")

    if droot not in dirtree:
        raise DirscanException(f"No such sub-directory '{root}' found in scanfile '{filename}'")

    # Now the tree should be populated
    return dirtree[droot][0]


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
