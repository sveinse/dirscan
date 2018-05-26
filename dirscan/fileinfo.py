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

import sys
import stat
import time
import string
import pwd
import grp



#
# LIST OF FORMAT FIELDS
# =====================
#
FILE_FIELDS = {

    # (bare) filename
    'name': lambda o: o.name,

    # The full file path
    'fullpath': lambda o: o.fullpath,

    # User
    'user': lambda o: format_user(o.uid),
    'uid': lambda o: o.uid,

    # Group
    'group': lambda o: format_group(o.gid),
    'gid': lambda o: o.gid,

    # Mode
    'mode': lambda o: o.mode,
    'mode_t': lambda o: format_mode(o.objtype, o.mode),

    # The object type, f=file, d=dir, l=symlink
    'type': lambda o: o.objtype,

    # The object size
    'size': lambda o: o.size,
    'size_h': lambda o: format_bytes(o.size),

    # Modification time
    'mtime': lambda o: o.mtime.strftime("%Y-%m-%d %H:%M:%S"),
    'mtime_n': lambda o: '%.6f' %(time.mktime(o.mtime.timetuple())+
                                  float(o.mtime.strftime("%f"))/1000000.0,),

    # Special data-payload of the file. For files: the hashsum, links: the link destination
    'data': lambda o: format_data(o),

    # The device node which the file resides
    'dev': lambda o: o.dev,
}


COMPARE_ARROWS = {
    # Change type    : ( filter, arrow )
    'error'          : ('E', 'ERROR'),
    'excluded'       : ('x', '    x'),
    'right_only'     : ('r', '   >>'),
    'left_only'      : ('l', '<<   '),
    'different_type' : ('t', '<~~~>'),
    'changed'        : ('c', '<--->'),
    'left_newer'     : ('L', '<<-->'),
    'right_newer'    : ('R', '<-->>'),
    'equal'          : ('e', '     '),
    'scan'           : ('s', '     '),
    'skipped'        : ('i', '    -'),
}


SCAN_SUMMARY = (
    # Condition,    Text.  Condition is a lookup into summary_dict
    (True,               "\nSummary of '{dir}':"),
    ('n_files',          "    {n_files}  files, total {sum_bytes_t}"),
    ('n_dirs',           "    {n_dirs}  directories"),
    ('n_symlinks',       "    {n_symlinks}  symbolic links"),
    ('n_special',        "    {n_special}  special files  ({n_blkdev} block devices, {n_chrdev} char devices, {n_fifos} fifos, {n_sockets} sockets)"),
    ('n_exclude',        "    {n_exclude}  excluded files or directories"),
    (True,               "In total {n_objects} file objects"),
)


COMPARE_SUMMARY = (
    # Condition,    Text.  Condition is a lookup into summary_dict
    (True,               "\nSummary of compare between left '{left}' and right '{right}':"),
    ('n_equal',          "    {n_equal}  equal files or directories"),
    ('n_changed',        "    {n_changed}  changed files or directories"),
    ('n_different_type', "    {n_different_type}  files of same name but different type"),
    ('n_left_only',      "    {n_left_only}  files or directories only in left '{left}'"),
    ('n_right_only',     "    {n_right_only}  files or directories only in right '{right}'"),
    ('n_left_newer',     "    {n_left_newer}  newer files in left '{left}'"),
    ('n_right_newer',    "    {n_right_newer}  newer files in right '{right}'"),
    ('n_scan',           "    {n_scan}  scanned objects in '{left}'"),
    ('n_excludes',       "    {n_excludes}  excluded files or directories"),
    ('n_errors',         "    {n_errors}  compare errors"),
    ('n_skipped',        "    {n_skipped}  skipped comparisons"),
    (True,               "In total {sum_objects} file objects"),
)


FINAL_SUMMARY = (
    ('n_err', "\n{prog}: **** {n_err} files or directories could not be read"),
)



def split_number(number):
    ''' Split a number into groups of 3 chars. E.g "1234776" will be
        returned as "1 234 776".
    '''
    s = str(number)
    n = []
    for i in range(-1, -len(s)-1, -1):
        n.append(s[i])
        if i % 3 == 0:
            n.append(' ')
    n.reverse()
    return ''.join(n).lstrip()



def format_bytes(size, print_full=False):
    ''' Return a string with a human printable representation of a
        (file) size.  The print_full option will append "(26 552 946
        485 bytes)" to the string.  E.g. format_bytes(26552946485)
        will return "24.74 GiB"
    '''

    # Make exceptions for low values
    if size is None:
        return None

    elif size < 10000:
        sizestr = '%s' %(size)

    else:
        # Kbi = integer part, kbm = modulus part
        # n = reconstructed float
        kbi = size
        kbm = 0
        n = kbi
        # Iterate through each "decade" unit
        for unit in ('B', 'K', 'M', 'G'):
            n = float(kbi) + float(kbm)/1024

            # Various print options. If a matching value range is found then exit loop
            if kbi < 10:
                sizestr = '%.2f%s' %(n, unit)
                break
            elif kbi < 100:
                sizestr = '%.1f%s' %(n, unit)
                break
            elif kbi < 1000:
                sizestr = '%.0f%s' %(n, unit)
                break
            elif kbi < 2048:
                sizestr = '%.0f%s' %(n, unit)
                break

            # If kbi (remaining value) is >=2048 then we will go to
            # next unit. Hence we need to divide by 1024 for the next
            # round.
            kbm = kbi % 1024
            kbi = kbi >> 10

    if print_full:
        extra = ' bytes'
        if size >= 10000:
            extra = ' (%s bytes)' %(split_number(size))
        sizestr += extra
    return sizestr



def format_mode(objtype, mode):
    ''' Return a human readable string of the mode permission bits '''
    text = list('-') * 9
    ev = [
        (stat.S_IRUSR, 0, 'r'), (stat.S_IWUSR, 1, 'w'), (stat.S_IXUSR, 2, 'x'),
        (stat.S_ISUID, 2, 'S'), (stat.S_IXUSR|stat.S_ISUID, 2, 's'),
        (stat.S_IRGRP, 3, 'r'), (stat.S_IWGRP, 4, 'w'), (stat.S_IXGRP, 5, 'x'),
        (stat.S_ISGID, 5, 'S'), (stat.S_IXGRP|stat.S_ISGID, 5, 's'),
        (stat.S_IROTH, 6, 'r'), (stat.S_IWOTH, 7, 'w'), (stat.S_IXOTH, 8, 'x'),
        (stat.S_ISVTX, 8, 'T'), (stat.S_IXOTH|stat.S_ISVTX, 8, 't'),
        ]
    for (m, p, c) in ev:
        if mode & m == m:
            text[p] = c
    ot = objtype
    if objtype == 'f':
        ot = '-'
    return ot + ''.join(text)



def format_data(obj):
    ''' Return the information for the special field 'data', which return various
        information, depending on type. Files return their sha256 hashsum, links
        their symlink target.
    '''
    if obj.objtype == 'f' and obj.size:
        return obj.hashsum()
    elif obj.objtype == 'l':
        return obj.link
    return None



def format_user(uid):
    ''' Return the username for the given uid '''
    return pwd.getpwuid(uid).pw_name



def format_group(gid):
    ''' Return the group name for the given gid '''
    return grp.getgrgid(gid).gr_name



def get_fields(objs, prefixes, fieldnames):
    ''' Get a dict of field values from the objects using the given
        fieldnames.
    '''

    fields = {}
    errs = []

    for field in fieldnames:

        for (obj, prefix) in zip(objs, prefixes):

            # Consider only fieldnames with the specific prefix
            if not field.startswith(prefix):
                continue

            # Get the basename of the field and find it in the FILE_FIELDS dict
            fld = field[len(prefix):]
            if fld not in FILE_FIELDS:
                continue

            # Get the data for that field
            try:
                data = FILE_FIELDS[fld](obj)
                if data is None:
                    data = ''
            except (IOError, OSError) as err:
                data = '**-ERROR-**'
                errs.append(err)

            # Store the field (as string)
            fields[field] = str(data)

    return (errs, fields)



def get_fieldnames(formatstr):
    ''' Get a set of {fields} used in formatstr '''

    fieldnames = set()
    for (text, field, fmt, conv) in string.Formatter().parse(formatstr):
        if field:
            fieldnames.add(field)
    return fieldnames



def write_fileinfo(fmt, fields, quoter=None, file=sys.stdout):
    ''' Write fileinfo fields '''

    if quoter:
        fields = {k: quoter(v) for k, v in fields.items()}
    file.write(fmt.format(**fields) + '\n')



def write_summary(summary, fields, file=sys.stdout):
    ''' Write the summary '''

    # Use the pre-defined summary_text
    for (var, line) in summary:
        # d.get(n,n) will return d[n] if n exists, otherwise return n.
        # Thus if n is True, True will be returned
        if line and fields.get(var, var):
            file.write(line.format(**fields) + '\n')




#
# HISTOGRAM CLASS
# ===============
#

class FileHistogram(object):

    def __init__(self, dir):
        self.dir = dir
        self.size = 0
        self.d = {}

    def add(self, v):
        self.d[v] = self.d.get(v, 0) + 1

    def get(self, v):
        return self.d.get(v, 0)

    def add_size(self, size):
        self.size += size

    def get_summary_fields(self):
        return {
            'dir': self.dir,
            'n_files': self.get('f'),
            'n_dirs': self.get('d'),
            'n_symlinks': self.get('l'),
            'n_special': self.get('b')+self.get('c')+self.get('p')+self.get('s'),
            'n_blkdev': self.get('b'),
            'n_chrdev': self.get('c'),
            'n_fifos': self.get('p'),
            'n_sockets': self.get('s'),
            'n_missing': self.get('-'),
            'n_exclude': self.get('x'),
            'n_objects': sum(self.d.values()),
            'sum_bytes': self.size,
            'sum_bytes_t': format_bytes(self.size, print_full=True),
        }


class CompareHistogram(object):

    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.d = {}

    def add(self, v):
        self.d[v] = self.d.get(v, 0) + 1

    def get(self, v):
        return self.d.get(v, 0)

    def get_summary_fields(self):
        return {
            'left': self.left,
            'right': self.right,
            'n_equal': self.get('equal'),
            'n_changed': self.get('changed'),
            'n_different_type': self.get('different_type'),
            'n_left_only': self.get('left_only'),
            'n_right_only': self.get('right_only'),
            'n_left_newer': self.get('left_newer'),
            'n_right_newer': self.get('right_newer'),
            'n_scan': self.get('scan'),
            'n_excludes': self.get('excluded'),
            'n_errors': self.get('error'),
            'n_skipped': self.get('skipped'),
            'n_err': self.get('err'),
            'sum_objects': sum(self.d.values())-self.get('err'),
        }


class Statistics(object):

    def __init__(self, left, right):
        self.compare = CompareHistogram(left, right)
        if right is None:
            self.filehist = [FileHistogram(left)]
        else:
            self.filehist = [FileHistogram(left), FileHistogram(right)]

    def add(self, change):
        self.compare.add(change)

    def add_filehist(self, objs):
        for (o, fh) in zip(objs, self.filehist):
            ot = 'x' if o.excluded else o.objtype
            fh.add(ot)
            if ot == 'f':
                fh.add_size(o.size)

    def get_fields(self, prefixes):

        # Get the main comparison fields
        fields = self.compare.get_summary_fields()

        # Assemble the per-directory summaries
        for (fh, pre) in zip(self.filehist, prefixes):
            for field, data in fh.get_summary_fields().items():

                # Replace 'n_' with specified prefix
                if field.startswith('n_') and pre:
                    field = field[2:]
                fields[pre + field] = data

        return fields
