# -*- coding: utf-8 -*-
'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2018 Svein Seldal, sveinse@seldal.com
URL: https://github.com/sveinse/dirscan

This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.
'''
from __future__ import absolute_import, division, print_function

import os
import datetime

from . import dirscan


# File format for serialized data-file
SCANFILE_FORMAT = "{type},{size},{mode},{uid},{gid},{mtime_n},{data},{path}"


def readscanfile(fname):
    ''' Read fname scan file and return a DirObj() with the file tree root '''

    dirtree = {}
    rootobj = None
    base_fname = os.path.basename(fname)

    with open(fname, 'r') as infile:
        lineno = 0
        for line in infile:
            lineno += 1

            # Read/parse the parameters (must be aliged with SCANFILE_FORMAT)
            args = [unquote(e) for e in line.rstrip().split(',')]
            otype = args[0]
            osize = int(args[1] or '0')
            omode = int(args[2])
            ouid = int(args[3])
            ogid = int(args[4])
            otime = datetime.datetime.fromtimestamp(float(args[5]))
            odata = args[6] or None
            opath = args[7]

            if opath == '.':
                opath = base_fname
            elif opath.startswith('./'):
                opath = opath.replace('./', base_fname+'/', 1)

            # Split path into path and name
            (path, name) = os.path.split(opath)
            if path.endswith('/'):
                path = path[:-1]

            # Create new object.
            obj = dirscan.create_from_data(path, name, otype, osize, omode,
                                           ouid, ogid, otime, odata)

            # The first object is special
            if path == '':
                rootobj = obj
                dirtree[opath] = obj
            else:
                # Add the object into the parent's children
                dirtree[path].add_child(obj)

            # Make sure we make an entry into the dirtree to ensure
            # we have a list of the parents
            if otype == 'd':
                dirtree[opath] = obj

    if not rootobj:
        raise dirscan.DirscanException("Scanfile '%s' is empty" %(fname,))

    # Now the tree should be populated
    return rootobj


# SIMPLE TEXT QUOTER
# ==================
#
#     \ -> \\
#     space -> \_
#     , -> \-
#     28 -> \<
#     31 -> \?
#     <32 to \@ to \^ (with the exception for 28 and 31)
def quote(text):
    ''' Simple text quoter for the scan files '''

    needquote = False
    for s in text:
        if ord(s) <= 32 or ord(s) == 44 or ord(s) == 92:
            needquote = True
            break
    if not needquote:
        return text
    ns = ''
    for s in text:
        if ',' in s:
            ns += '\\-'
        elif '\\' in s:
            ns += '\\\\'
        elif ' ' in s:
            ns += '\\_'
        elif ord(s) == 28 or ord(s) == 31:
            ns += '\\%s' %(chr(ord(s)+32))
        elif ord(s) < 32:
            ns += '\\%s' %(chr(ord(s)+64))
        else:
            ns += s
    return ns


def unquote(text):
    ''' Simple text un-quoter for the scan files '''

    if '\\' not in text:
        return text
    ns = ''
    escape = False
    for s in text:
        if escape:
            if '\\' in s:
                ns += '\\'
            elif '-' in s:
                ns += ','
            elif '_' in s:
                ns += ' '
            elif '<' in s:
                ns += chr(28)
            elif '?' in s:
                ns += chr(31)
            elif ord(s) >= 64 and ord(s) <= 95:
                ns += chr(ord(s)-64)
            # Unknown/incorrectly formatted escape char is silently ignored
            escape = False
        elif '\\' in s:
            escape = True
        else:
            ns += s
    return ns
