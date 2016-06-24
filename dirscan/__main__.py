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

import sys
import dirscan
import argparse
import os
import re
import stat
import time
import fnmatch
import string
import pwd
import grp



# General options
opts = None
prog = None


def log(text):
    print >>sys.stderr, text



# Simple text quoter
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
            # Unknown escape char is silently ignored
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
        return obj.hashsum()
    elif obj.objtype=='l':
        return obj.link()
    return None



def format_user(uid):
    return pwd.getpwuid(uid).pw_name



def format_group(gid):
    return grp.getgrgid(gid).gr_name



#
# LIST OF FORMAT FIELDS
#
re_relative = re.compile(r'([^/]+)(/?.*)')
info_fields = {

    # (bare) filename
    'name': lambda o: o.name,

    # The full file path
    'path': lambda o: o.fullpath,

    # The relative fullpath (from the top scan directory)
    'relpath': lambda o: re_relative.sub(r'.\2', o.fullpath),

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
    'size': lambda o: o.size if not opts.human else format_bytes(o.size),

    # Modification time
    'mtime': lambda o: o.mtime.strftime("%Y-%m-%d %H:%M:%S"),
    'mtime_num': lambda o: '%.6f' %(time.mktime(o.mtime.timetuple())+float(o.mtime.strftime("%f"))/1000000.0,),

    # Special data-payload of the file. For files: the hashsum, links: the link destination
    'data': lambda o: format_data(o),
}

alias_fields = {
    'f': 'name',
    'F': 'path',
    'R': 'relpath',
    'u': 'user',
    'U': 'uid',
    'g': 'group',
    'G': 'gid',
    'o': 'type',
    's': 'size',
    'm': 'mode',
    'M': 'mode_t',
    't': 'mtime',
    'T': 'mtime_num',
}

# Put the aliases into the info_fields dict as well
for alias in alias_fields:
    info_fields[alias] = info_fields[alias_fields[alias]]



re_format = re.compile(r'({[\w]*)([!:][^}]*)?}')
def dump_fileinfo(obj, format, doquote=True):

    q = lambda a: a
    if doquote:
        global quote
        q = quote

    fields = { }
    formatter = string.Formatter()

    try:

        # Iterate over the formatter fields and get the required fields
        for (text,field,fmt,conv) in formatter.parse(format):

            if field in info_fields:

                # Get the dynamic data from the fields dict
                data = info_fields[field](obj)
                if data is None:
                    data = ''

                # Store the field (as string)
                fields[field] = q(str(data))

        # Generate the line
        return formatter.format(format, **fields) + '\n'

    except (KeyError, IndexError, ValueError) as e:
        raise SyntaxError("Format '%s' error: %s" %(format,e))




def scandir(dir,outfile,exclude=None):
    ''' Scan dir and write output to outfile '''

    #
    # Determine print format to use
    #

    # Default format
    format = printformat = '{path}'

    if outfile:
        # This HAVE to be matched up against the sequence in readfilelist() for it
        # to be useful
        format = "{type},{size},{mode},{uid},{gid},{mtime_num},{data},{relpath}"

    elif opts.all:
        if opts.human:
            format = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {path}'
        else:
            format = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {path}'

    elif opts.long:
        if opts.human:
            format = '{mode_t}  {user:8} {group:8}  {size:>5}  {mtime}  {path}'
        else:
            format = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {path}'

    # User provided format overrides any defaults
    format = opts.format or format


    # Setup exclusion dirs
    if exclude is None:
        exclude = []
    exclude = [ os.path.join(dir,e) for e in exclude ]


    histogram = {}
    size = 0
    has_errors = False
    f = None
    try:
        if not outfile:
            f = sys.stdout
            doprint = False
            dowrite = True
            doquote = False

        else:
            f = open(outfile, 'w')
            doprint = opts.verbose
            dowrite = True
            doquote = True


        # Traverse the directory
        for (path,objs) in dirscan.walkdirs([dir,]):
            obj = objs[0]

            # Ignored file?
            fullpath = obj.fullpath
            if [ fnmatch.fnmatch(fullpath, e) for e in exclude ].count(True) > 0:
                continue

            # Failed file?
            if obj.parserr:
                sys.stderr.write('%s: %s\n' %(prog, obj.parserr))
                has_errors = True
                continue

            # Save histogram info
            histogram.setdefault(type(obj),0)
            histogram[type(obj)] += 1
            size += (obj.size or 0)

            # Print to stderr?
            if doprint:
                sys.stdout.write(dump_fileinfo(obj, format=printformat, doquote=False))

            # Print to stdout or file?
            if dowrite:
                f.write(dump_fileinfo(obj, format=format, doquote=doquote))


        if opts.summary:
            log('')
            log("Statistics of '%s':" %(dir))
            log("     %s  files, in total %s" %(histogram.get(dirscan.FileObj,0),
                                                format_bytes(size,print_full=True) ))
            log("     %s  directories" %(histogram.get(dirscan.DirObj,0)))
            log("     %s  symbolic links" %(histogram.get(dirscan.LinkObj,0)))
            log("     %s  special files" %(histogram.get(dirscan.SpecialObj,0)))
            log("In total %s file objects" %(sum(histogram.values())))


    finally:
        if f != sys.stdout:
            f.close()

    if has_errors:
        log('%s: *** Some files/dirs were not scanned due to errors' %(prog))
        return 1

    return 0



def main(args=None):

    if args is None:
        args = sys.argv[1:]

    # -- Generic options
    description = '''
Tool for scanning and comparing directories.

A single DIR argument will traverse the given directory and print the contents,
similar to ls or find, and can provide a summary of the found files. It can
save the file list with file metadata, including sha256 hashsum of the file,
using the -o option.

A DIR1 DIR2 argument is used to compare directories, showing differences
between DIR1 and DIR2. DIR1 or DIR2 can be either a directory or a previous
generated scan file.

(C) 2010-2016 Svein Seldal. This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.

'''
    epilog = ''

    ap = argparse.ArgumentParser(description=description, epilog=epilog, add_help=False)
    ap.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    ap.add_argument('--help', action='help')
    ap.add_argument('-a', '--all', dest='all', action='store_true', default=False, help='Print all file info. Might consume considerable time, as the hashsum is read from the files.')
    ap.add_argument('-f', '--format', dest='format', metavar='TYPE', default=None, help='File printing format')
    #ap.add_argument('-G', '--ignore-gid', action='store_true', dest='igngid', default=False, help='Ignore GID ownership')
    ap.add_argument('-h', '--human', dest='human', action='store_true', default=False,
                                     help='Display human readable sizes')
    ap.add_argument('-l', '--long', dest='long', action='store_true', default=False, help='Dump file in extended format')
    #ap.add_argument('-D', '--debug', dest='debug', action='store_true', default=False, help='Debug output')
    ap.add_argument('-o', '--output', dest='outfile', metavar='FILE', help='Store scan output in FILE. FILE can be used later as input to dirscan for comparsion.')
    #ap.add_argument('-P', '--ignore-perm', action='store_true', dest='ignperm', default=False, help='Ignore permissions')
    #ap.add_argument('-q', '--quiet', action='store_true', dest='quiet', default=False, help='Quiet operation')
    ap.add_argument('-s', '--summary', action='store_true', dest='summary', default=False, help='Print summary')
    #ap.add_argument('-t', '--traverse', dest='traverse', action='store_true', default=False,
    #                           help='Print the children of dirs when traversing directory that exists on only one side.')
    #ap.add_argument('-T', '--ignore-time', action='store_true', dest='igntime', default=False, help='Ignore time')
    #ap.add_argument('-U', '--ignore-uid', action='store_true', dest='ignuid', default=False, help='Ignore UID ownership')
    ap.add_argument('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose printing.')
    ap.add_argument('-X', '--exclude-dir', dest='exclude', metavar='FILE', action='append', default=[],
                                           help='Exclude FILE from scan')
    ap.add_argument('dir1', metavar='DIR1', help='Directory to scan/traverse')
    ap.add_argument('dir2', metavar='DIR2', help='If present, compare DIR1 with DIR2', default=False, nargs='?')

    global opts
    opts = ap.parse_args()
    global prog
    prog = ap.prog


    # -- Make sure all exclude rules have 'name/*' in the list as well to make sure we also ignore sub-dirs
    for e in opts.exclude:
        if not e.endswith('*'):
            opts.exclude.append(os.path.join(e,'*'))


    # -- COMMAND HANDLING
    #if not opts.dir2:
    return scandir(opts.dir1,opts.outfile,exclude=opts.exclude)
    #else:
    #    diffdirs(opts.dir1,opts.dir2,exclude=opts.exclude)

    ap.exit(0)
    

if __name__ == '__main__':
    main()
