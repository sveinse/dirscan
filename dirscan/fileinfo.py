# -*- coding: utf-8 -*-
#
# This file is a part of dirscan, a handy tool for recursively
# scanning and comparing directories and files
#
# Copyright (C) 2010-2016 Svein Seldal, sveinse@seldal.com
# URL: https://github.com/sveinse/dirscan
#
# This application is licensed under GNU GPL version 3
# <http://gnu.org/licenses/gpl.html>. This is free software: you are
# free to change and redistribute it. There is NO WARRANTY, to the
# extent permitted by law.
#
from __future__ import absolute_import

import stat
import time
import string
import pwd
import grp



#
# LIST OF FORMAT FIELDS
# =====================
#
file_fields = {

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
    'size_h': lambda o: format_bytes(o.szie),

    # Modification time
    'mtime': lambda o: o.mtime.strftime("%Y-%m-%d %H:%M:%S"),
    'mtime_n': lambda o: '%.6f' %(time.mktime(o.mtime.timetuple())+float(o.mtime.strftime("%f"))/1000000.0,),

    # Special data-payload of the file. For files: the hashsum, links: the link destination
    'data': lambda o: format_data(o),
}


compare_arrows = {
    # Change type    : ( filter, arrow )
    'excluded'       : ( 'x', '    x' ),
    'right_only'     : ( 'r', '   >>' ),
    'left_only'      : ( 'l', '<<   ' ),
    'different_type' : ( 'd', '~~~~~' ),
    'changed'        : ( 'c', '<--->' ),
    'left_newer'     : ( 'L', '<<-->' ),
    'right_newer'    : ( 'R', '<-->>' ),
    'equal'          : ( 'e', '     ' ),
    'error'          : ( 'E', 'ERROR' ),
    'scan'           : ( 's', '     ' ),
}


summary_scan = [
    # Condition,    Text.  Condition is a lookup into summary_dict
    ( True,               "\nSummary of '{dir}':" ),
    ( 'n_files',          "    {n_files}  files, total {sum_bytes_t}" ),
    ( 'n_dirs',           "    {n_dirs}  directories" ),
    ( 'n_symlinks',       "    {n_symlinks}  symbolic links" ),
    ( 'n_special',        "    {n_special}  special files  ({n_blkdev} block devices, {n_chrdev} char devices, {n_fifos} fifos, {n_sockets} sockets)" ),
    ( 'n_exclude',        "    {n_exclude}  excluded files" ),
    ( True,               "In total {n_objects} file objects" ),
]


summary_compare = [
    # Condition,    Text.  Condition is a lookup into summary_dict
    ( True,               "\nSummary of compare between '{left}' and '{right}':" ),
    ( 'n_equal',          "    {n_equal}  equal files" ),
    ( 'n_changed',        "    {n_changed}  changed files" ),
    ( 'n_different_type', "    {n_different_type}  files of same name but different type" ),
    ( 'n_left_only',      "    {n_left_only}  files only in '{left}'" ),
    ( 'n_right_only',     "    {n_right_only}  files only in '{right}'" ),
    ( 'n_left_newer',     "    {n_left_newer}  newer files in '{left}'" ),
    ( 'n_right_newer',    "    {n_right_newer}  newer files in '{right}'" ),
    ( 'n_scan',           "    {n_scan}  scanned objects in '{left}'" ),
    ( 'n_excludes',       "    {n_excludes}  excluded files" ),
    ( 'n_errors',         "    {n_errors}  errors" ),
    ( True,               "In total {sum_objects} file objects" ),
]



# SIMPLE TEXT QUOTER
# ==================
#
#     \ -> \\
#     space -> \_
#     , -> \-
#     28 -> \<
#     31 -> \?
#     <32 to \@ to \^ (with the exception for 28 and 31)
def quote(st):
    needquote=False
    for s in st:
        if ord(s) <= 32 or ord(s) == 44 or ord(s) == 92:
            needquote=True
            break
    if not needquote:
        return st
    ns = ''
    for s in st:
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


def unquote(st):
    if '\\' not in st:
        return st
    ns = ''
    escape = False
    for s in st:
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



def split_number(number):
    ''' Split a number into groups of 3 chars. E.g "1234776" will be
        returned as "1 234 776".
    '''
    s = str(number)
    n = [ ]
    for i in range(-1,-len(s)-1,-1):
        n.append(s[i])
        if i % 3 == 0:
            n.append(' ')
    n.reverse()
    return ''.join(n).lstrip()



def format_bytes(bytes,print_full=False):
    ''' Return a string with a human printable representation of a
        (file) size.  The print_full option will append "(26 552 946
        485 bytes)" to the string.  E.g. format_bytes(26552946485)
        will return "24.74 GiB"
    '''

    # Make exceptions for low values
    if bytes is None:
        return None

    elif bytes < 10000:
        size = '%s' %(bytes)

    else:
        units = [ 'B', 'K', 'M', 'G' ]

        # Kbi = integer part, kbm = modulus part
        # n = reconstructed float
        kbi = bytes
        kbm = 0
        n = kbi
        # Iterate through each "decade" unit
        for unit in units:
            n = float(kbi) + float(kbm)/1024

            # Various print options. If a matching value range is found then exit loop
            if kbi < 10:
                size = '%.2f%s' %(n,unit)
                break
            elif kbi < 100:
                size = '%.1f%s' %(n,unit)
                break
            elif kbi < 1000:
                size = '%.0f%s' %(n,unit)
                break
            elif kbi < 2048:
                size = '%.0f%s' %(n,unit)
                break

            # If kbi (remaining value) is >=2048 then we will go to
            # next unit. Hence we need to divide by 1024 for the next
            # round.
            kbm = kbi % 1024
            kbi = kbi >> 10

    if print_full:
        extra = ' bytes'
        if bytes >= 10000:
            extra = ' (%s bytes)' %(split_number(bytes))
        size += extra
    return size



def format_mode(objtype,mode):
    ''' Return a human readable string of the mode permission bits '''
    text = list('-') * 9
    ev = [
        (stat.S_IRUSR, 0, 'r'),  (stat.S_IWUSR, 1, 'w'),  (stat.S_IXUSR, 2, 'x'),
        (stat.S_ISUID, 2, 'S'),  (stat.S_IXUSR|stat.S_ISUID, 2, 's'),
        (stat.S_IRGRP, 3, 'r'),  (stat.S_IWGRP, 4, 'w'),  (stat.S_IXGRP, 5, 'x'),
        (stat.S_ISGID, 5, 'S'),  (stat.S_IXGRP|stat.S_ISGID, 5, 's'),
        (stat.S_IROTH, 6, 'r'),  (stat.S_IWOTH, 7, 'w'),  (stat.S_IXOTH, 8, 'x'),
        (stat.S_ISVTX, 8, 'T'),  (stat.S_IXOTH|stat.S_ISVTX, 8, 't'),
        ]
    for (m,p,c) in ev:
        if mode & m == m:
            text[p] = c
    ot = objtype
    if objtype=='f':
        ot = '-'
    return ot + ''.join(text)



def format_data(obj):
    ''' Return the information for the special field 'data', which return various
        information, depending on type. Files return their sha256 hashsum, links
        their symlink target.
    '''
    if obj.objtype=='f' and obj.size:
        # FIXME: This might fail if we can't read the file. The error needs to bubble up
        #        to the mainloop.
        return obj.hashsum()
    elif obj.objtype=='l':
        return obj.link
    return None



def format_user(uid):
    return pwd.getpwuid(uid).pw_name



def format_group(gid):
    return grp.getgrgid(gid).gr_name




#
# INFO PRINT FUNCTIONS
# ====================
#
def get_fileinfo(path, ob, change, text, prefixlist, formatlist):

    # The base fields
    fields = {
        'path'  : str(path),
        'change': str(change),
        'arrow' : compare_arrows[change][1],
        'text'  : str(text).capitalize(),
    }


    formatter = string.Formatter()
    err = None

    for format in formatlist:

        # Iterate over the formatter fields and get the used fields
        for (text,field,fmt,conv) in formatter.parse(format):

            # Empty and already existing fields are ignored
            if field is None or field in fields:
                continue

            for (obj,prefix) in zip(ob,prefixlist):

                # Consider only fieldnames with the specific prefix
                if not field.startswith(prefix):
                    continue

                # Get the basename of the field and find it in the file_fields dict
                fi = field[len(prefix):]
                if fi not in file_fields:
                    continue

                # Get the data for that field
                try:
                    data = file_fields[fi](obj)
                    if data is None:
                        data = ''
                except (IOError,OSError) as e:
                    data = '**-VOID-**'
                    err = e

                # Store the field (as string)
                fields[field] = str(data)

    return (err, fields)



def write_fileinfo(fields, format, quoter, f):

    fields = fields.copy()
    for fi in fields:
        fields[fi] = quoter(fields[fi])
    f.write(format.format(**fields) + '\n')




#
# HISTOGRAM CLASS
# ===============
#
class Histogram(object):
    def __init__(self):
        self.d = {}

    def add(self,objtype):
        self.d.setdefault(objtype,0)
        self.d[objtype] += 1

    def get(self,objtype):
        return self.d.get(objtype,0)


class FileHistogram(Histogram):

    def __init__(self,dir):
        self.dir = dir
        self.size = 0
        Histogram.__init__(self)

    def add_size(self,size):
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
            'sum_bytes_t': format_bytes(self.size,print_full=True),
        }


class CompareHistogram(Histogram):

    def __init__(self,left,right):
        self.left = left
        self.right = right
        Histogram.__init__(self)

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
            'sum_objects': sum(self.d.values()),
        }
