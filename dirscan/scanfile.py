# -*- coding: utf-8 -*-
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

from . import dirscan
from .dirscan import DirscanException


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
        raise DirscanException("Invalid scanfile '%s', missing header" % (filename,))
    line = line.rstrip()

    if not line.startswith('#!ds:v'):
        raise DirscanException("Invalid scanfile '%s', incorrect header" % (filename,))

    ver = line[5:]
    if ver not in SCANFILE_VERSIONS:
        raise DirscanException("Invalid scanfile '%s', unsupported version '%s'" % (filename, ver))


class ScanfileRecord:
    ''' Scan file record '''

    # File format for serialized data-file
    FORMAT = "{type},{size},{mode},{uid},{gid},{mtime_n},{data},{path}"

    def __init__(self, parse):
        args = [unquote(e) for e in parse.rstrip().split(',')]
        length = len(args)
        if length != 8:
            raise DirscanException("Missing file fields (got %s of 8)" % (length,))
        try:
            # Must be kept in sync with self.FORMAT
            self.type = args[0]
            self.size = int(args[1] or '0')
            self.mode = int(args[2])
            self.uid = int(args[3])
            self.gid = int(args[4])
            self.mtime = float(args[5])
            self.data = args[6] or None
            self.path = args[7]
        except ValueError as err:
            raise DirscanException("Scanfile field error: " + str(err)) from None
        if not self.type:
            raise DirscanException("'type' field cannot be omitted")
        if not self.path:
            raise DirscanException("'path' field cannot be omitted")


def read_scanfile(filename, treeid=None, root=None):
    ''' Read filename scan file and return a DirObj() with the file tree root '''

    # Set a default value
    if not root:
        root = ''
        droot = '.'
    else:
        droot = os.path.join('.', root)

    dirtree = {}
    base_fname = os.path.basename(filename)

    with open(filename, 'r', errors='surrogateescape') as infile:

        # Check the scanfile header
        check_header(infile.readline(), filename)

        lineno = 1
        for line in infile:
            lineno += 1

            try:
                # Read/parse the record
                data = ScanfileRecord(line)

                # Split path into path and name
                opath = data.path
                (path, name) = os.path.split(opath)

                # Set file object path and name
                if path == '':
                    if name != '.':
                        raise DirscanException("unexpected top-level entity '%s'" % (name,))
                    fpath = path
                    fname = base_fname
                else:
                    fpath = os.path.join(base_fname, path[2:])
                    fname = name

                # Create new file object
                fileobj = dirscan.create_from_data(fname, fpath,
                                                   objtype=data.type,
                                                   size=data.size,
                                                   mode=data.mode,
                                                   uid=data.uid,
                                                   gid=data.gid,
                                                   mtime=data.mtime,
                                                   data=data.data,
                                                   treeid=treeid)

                # The first object is special
                if opath == '.':
                    dirtree[opath] = fileobj
                else:
                    if path not in dirtree:
                        raise DirscanException("'%s' is an orphan" % (opath))

                    # Add the object into the parent's children
                    dirtree[path].add_child(fileobj)

                # Make sure we make an entry into the dirtree to ensure
                # we have a list of the parents
                if data.type == 'd':
                    dirtree[opath] = fileobj

            except DirscanException as err:
                raise DirscanException("%s:%s: Data error, " % (
                    filename, lineno) + str(err)) from None

    if not dirtree:
        raise DirscanException("Scanfile '%s' contains no data" % (filename,))

    if droot not in dirtree:
        raise DirscanException("No such directory '%s' in scanfile '%s" % (root, filename))

    # Now the tree should be populated
    return dirtree[droot]


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
            out += '\\x%02x' % (value)
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
                raise DirscanException("Unknown escape char '%s'" % (char,))
            escape = False

        elif '\\' in char:
            escape = True

        else:
            out += char

    if escape or getchars:
        raise DirscanException("Incomplete escape string '%s'" % (text))
    return out
