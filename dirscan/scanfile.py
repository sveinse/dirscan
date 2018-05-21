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
from . import fileinfo


# File format for serialized data-file
SCANFILE_FORMAT = "{type},{size},{mode},{uid},{gid},{mtime_n},{data},{path}"


def readscanfile(fname):
    ''' Read fname scan file and return a DirObj() with the file tree root '''

    dirtree = {}
    rootobj = None
    base_fname = os.path.basename(fname)

    with open(fname, 'r') as f:
        lineno = 0
        for line in f:
            lineno += 1

            # Read/parse the parameters (must be aliged with SCANFILE_FORMAT)
            args = [fileinfo.unquote(e) for e in line.rstrip().split(',')]
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
                dirtree[path].set_child(obj)

            # Make sure we make an entry into the dirtree to ensure
            # we have a list of the parents
            if otype == 'd':
                dirtree[opath] = obj

    if not rootobj:
        raise dirscan.DirscanException("Scanfile '%s' is empty" %(fname,))

    # Now the tree should be populated
    return rootobj
