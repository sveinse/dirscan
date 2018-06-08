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
import sys
import datetime

from . import dirscan


# File format for serialized data-file
SCANFILE_FORMAT = "{type},{size},{mode},{uid},{gid},{mtime_n},{data},{path}"

# Known scan file versions
SCANFILE_VERSIONS = ( 'v1', )



def fileheader():
    ''' Return the file header of the scan-file '''
    return '#!ds:v1\n'



def checkheader(line, fname):

    if not line:
        raise dirscan.DirscanException("Scanfile '%s' is empty" %(fname,))
    line = line.rstrip()

    if not line.startswith('#!ds:v'):
        raise dirscan.DirscanException("Scanfile '%s' does not seem to be a scan-file" %(fname,))

    ver = line[5:]
    if ver not in SCANFILE_VERSIONS:
        raise dirscan.DirscanException("Scanfile '%s' use unknown version '%s'" %(fname, ver))



def readscanfile(fname, treeid=None):
    ''' Read fname scan file and return a DirObj() with the file tree root '''

    dirtree = {}
    rootobj = None
    base_fname = os.path.basename(fname)

    kw = {}
    if sys.version_info[0] >= 3:
        kw['errors']='surrogateescape'

    with open(fname, 'r', **kw) as infile:

        # Check the scanfile header
        checkheader(infile.readline(), fname)

        lineno = 1
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
            obj = dirscan.create_from_data(name, path, otype, osize, omode,
                                           ouid, ogid, otime,
                                           data=odata,
                                           treeid=treeid)

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
    for s in text:
        v = ord(s)
        if v < 32 or v == 127:
            out += '\\x%02x' %(v)
        #elif v == 32:  # ' '
        #    out += '\\ '
        #elif v == 44:  # ','
        #    out += '\\-'
        elif v == 92:  # '\'
            out += '\\\\'
        else:
            out += s

    if sys.version_info[0] < 3:
        try:
            _tmp = text.decode('utf-8')
        except UnicodeDecodeError:
            # This takes care of escaping strings containing encoding errors.
            # Specifically this takes care of esacaping >=128 chars into \xNN,
            # but not correct unicode code points.
            # [1:-1] removes the ' prefix and ' postfix
            out = repr(out)[1:-1]
    else:
        try:
            _tmp = text.encode('utf-8')
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
    for s in text:

        if getchars:
            # Getting char value for \xNN escape codes
            hexstr += s
            getchars -= 1
            if getchars == 0:
                v = int(hexstr, 16)
                # Code-points above 128 must be made into a surrogate on py3
                # for the quoter to work with this values
                if v >= 128 and sys.version_info[0] >= 3:
                    v |= 0xdc00
                out += chr(v)

        elif escape:
            # Getting escape code following '\'
            if '\\' in s:
                out += '\\'
            elif '-' in s:
                out += ','
            elif ' ' in s:
                out += ' '
            elif 'x' in s:
                getchars = 2
                hexstr = ''
            else:
                raise dirscan.DirscanException("Unknown escape char '%s'" %(s,))
            escape = False

        elif '\\' in s:
            escape = True

        else:
            out += s

    if escape or getchars:
        raise dirscan.DirscanException("Incomplete escape string '%s'" %(text))
    return out
