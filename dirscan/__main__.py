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
import datetime



# General options
opts = None
prog = None


def log(text):
    sys.stderr.write(text + '\n')



# Simple text quoter
# ==================
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
# LIST OF FORMAT FIELDS
# =====================
#
info_fields = {

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
    'size': lambda o: o.size if not opts.human else format_bytes(o.size),

    # Modification time
    'mtime': lambda o: o.mtime.strftime("%Y-%m-%d %H:%M:%S"),
    'mtime_n': lambda o: '%.6f' %(time.mktime(o.mtime.timetuple())+float(o.mtime.strftime("%f"))/1000000.0,),

    # Special data-payload of the file. For files: the hashsum, links: the link destination
    'data': lambda o: format_data(o),
}

diff_arrows = {
    # Change type    : ( filter, arrow )
    'ignored'        : ( 'i', '    x' ),
    'only_right'     : ( 'r', '   >>' ),
    'only_left'      : ( 'l', '<<   ' ),
    'different_type' : ( 'd', '~~~~~' ),
    'changed'        : ( 'c', '<--->' ),
    'left_newer'     : ( 'L', '<<-->' ),
    'right_newer'    : ( 'R', '<-->>' ),
    'equal'          : ( 'e', '     ' ),
    'error'          : ( 'E', 'ERROR' ),
}



#
# INFO PRINT FUNCTIONS
# ====================
#
def dump_fileinfo(path, obj, format, quoter, f):

    # The base fields
    fields = {
        'path': quoter(str(path)),
    }

    try:

        # Iterate over the formatter fields and get the used fields
        formatter = string.Formatter()
        for (text,field,fmt,conv) in formatter.parse(format):

            if field in info_fields:

                # Get the dynamic data from the fields dict
                data = info_fields[field](obj)
                if data is None:
                    data = ''

                # Store the field (as string)
                fields[field] = quoter(str(data))

        # Generate the line
        f.write(formatter.format(format, **fields) + '\n')

    except (KeyError, IndexError, ValueError) as e:
        raise SyntaxError("Format '%s' error: %s" %(format,e))



def dump_diffinfo(path, change, left, right, text, format, quoter, f):

    # The common fields
    fields = {
        'arrow': diff_arrows[change][1],
        'path': quoter(str(path)),
        'change': change,
        'text': str(text).capitalize(),
    }

    try:

        # Iterate over the formatter fields and get the used fields
        formatter = string.Formatter()
        for (text,field,fmt,conv) in formatter.parse(format):

            use = None
            if field is None:
                continue
            elif field.startswith('l_'):
                use = left
            elif field.startswith('r_'):
                use = right
            else:
                continue

            # Remove the l_ or r_ prefix to get the field name
            fi = field[2:]
            if fi not in info_fields:
                continue

            # Get the dynamic data from the fields dict
            data = info_fields[fi](use)
            if data is None:
                data = ''

            # Store the field (as string)
            fields[field] = quoter(str(data))

        # Generate the line
        f.write(formatter.format(format, **fields) + '\n')

    except (KeyError, IndexError, ValueError) as e:
        raise SyntaxError("Format '%s' error: %s" %(format,e))



#
# SCAN FILE READER
# ================
#
scanfile_format = "{type},{size},{mode},{uid},{gid},{mtime_n},{data},{path}"
def readscanfile(fname):
    ''' Read fname scan file and return a DirObj() with the file tree root '''

    dirtree = { }
    rootobj = None

    with open(fname, 'r') as f:
        n=0
        for line in f:
            n+=1

            # Read/parse the parameters
            args = [ unquote(e) for e in line.rstrip().split(',') ]
            otype = args[0]
            osize = int(args[1] or '0')
            omode = int(args[2])
            ouid  = int(args[3])
            ogid  = int(args[4])
            otime = datetime.datetime.fromtimestamp(float(args[5]))
            odata = args[6] or None
            opath = args[7]

            if opath == '.':
                opath = fname
            elif opath.startswith('./'):
                opath = opath.replace('./',fname+'/',1)

            # Split path into path and name
            (path, name) = os.path.split(opath)
            if path.endswith('/'):
                path=path[:-1]

            # Create new object.
            obj = dirscan.newFromData(path, name, otype, osize, omode, ouid, ogid, otime, odata)

            # The first object is special
            if path == '':
                rootobj = obj
                dirtree[opath] = obj
            else:
                # Add the object into the parent's children
                dirtree[path][name] = obj

            # Make sure we make an entry into the dirtree to ensure we have a list of the parents
            if otype == 'd':
                dirtree[opath] = obj

    # Now the tree should be populated
    return rootobj



#
# DIFF TOOL
# =========
#
def diffworker(left,right,exclude):

    left_path = left
    if isinstance(left,dirscan.BaseObj):
        left_path = left.fullpath
    right_path = right
    if isinstance(right,dirscan.BaseObj):
        right_path = right.fullpath

    # Traverse the directories
    for (path,ob) in dirscan.walkdirs([left,right]):

        # Ignored file?
        fullpath = ob[0].fullpath
        if [ fnmatch.fnmatch(fullpath, e) for e in exclude ].count(True) > 0:
            # File IGNORED
            # ============
            yield (path, 'ignored', ob, 'ignored')

        elif ob[0].parserr:
            # Left file ERROR
            # ===============
            yield (path, 'error', ob, ob[0].parserr)

        elif ob[1].parserr:
            # Right file ERROR
            # ================
            yield (path, 'error', ob, ob[1].parserr)

        elif ob[0].objtype == '-':
            # File present RIGHT only
            # =======================
            if opts.traverse or ob[0].hasparent:
                text="%s only in %s" %(ob[1].objname,right_path)
                yield (path,'only_right', ob, text)

        elif ob[1].objtype == '-':
            # File present LEFT only
            # ======================
            if opts.traverse or ob[1].hasparent:
                text="%s only in %s" %(ob[0].objname,left_path)
                yield (path, 'only_left', ob, text)

        elif ob[0].objtype != ob[1].objtype:
            # File type DIFFERENT
            # ===================
            text="Different type, %s in %s and %s in %s" %(ob[0].objname,left_path,ob[1].objname,right_path)
            yield (path, 'different_type', ob, text)

        else:
            # File type EQUAL
            # ===============

            # compare returns a list of differences. If None, they are equal
            try:
                rl=ob[0].compare(ob[1])
            except IOError as e:
                # Compares might fail
                yield (path, 'error', ob, str(e))
                continue

            if rl:
                # Make a new list and filter out the ignored differences
                el=[]
                change='changed'
                for r in rl:
                    if 'newer' in r:
                        if 't' in opts.ignore:
                            continue
                        r = '%s is newer' %(left_path)
                        change='left_newer'
                    elif 'older' in r:
                        if 't' in opts.ignore:
                            continue
                        r = '%s is newer' %(right_path)
                        change='right_newer'
                    elif 'u' in opts.ignore and 'UID differs' in r:
                        continue
                    elif 'g' in opts.ignore and 'GID differs' in r:
                        continue
                    elif 'p' in opts.ignore and 'Permissions differs' in r:
                        continue
                    el.append(r)

                if el:  # else from this test indicates file changed, but all changes have been masked with
                        # the above ignore settings

                    # File contents CHANGED
                    # =====================
                    text="%s changed: %s" %(ob[0].objname,", ".join(el))
                    yield (path, change, ob, text)
                    continue

                # Compares with changes may fall through here because of ignore settings

            # File contents EQUAL
            # ===================
            yield (path, 'equal', ob, 'equal')



def diffdirs(left,right,exclude):

    #
    # Determine print format to use
    #

    # Default format
    format = '{arrow}  {path}  :  {text}'
    filter = 'rldcLRE'

    if opts.all:
        # Get all filter types
        filter = ''.join([ diff_arrows[x][0] for x in diff_arrows ])

    # User provided format overrides any defaults
    format = opts.format or format
    filter = opts.filter or filter


    # If either left or write is file, they should be parsed as scan files
    if os.path.isfile(left):
        left = readscanfile(left)
    if os.path.isfile(right):
        right = readscanfile(right)


    # Prepare histogram
    histogram = {}
    def hist_add(objtype):
        histogram.setdefault(objtype,0)
        histogram[objtype] += 1
    def hist_get(objtype):
        return histogram.get(objtype,0)


    f = None
    try:
        # FIXME: Add support for outfile
        f = sys.stdout
        quoter = lambda a: a

        # Traverse the directories
        for (path, change, ob, text) in diffworker(left,right,exclude):

            # Print the difference if type is listed in filter
            letter = diff_arrows[change][0]
            if letter in filter:
                dump_diffinfo(path, change, ob[0], ob[1], text, format, quoter, f)

            # Add to the histogram
            hist_add(change)


        if opts.summary:
            log('')
            log("Statistics of compare between '%s' and '%s':" %(left,right))
            log("     %s  equal files" %(hist_get('equal')))
            log("     %s  changed files" %(hist_get('changed')))
            log("     %s  files of different type but same name" %(hist_get('different_type')))
            log("     %s  files only in '%s'" %(hist_get('only_left'),left))
            log("     %s  files only in '%s'" %(hist_get('only_right'),right))
            if 't' not in opts.ignore:
                log("     %s  files in '%s' is newer" %(hist_get('left_newer'),left))
                log("     %s  files in '%s' is newer" %(hist_get('right_newer'),right))
            if hist_get('ignored') > 0:
                log("     %s  ignored files" %(hist_get('ignored')))
            if hist_get('error') > 0:
                log("     %s  files with error" %(hist_get('error')))
            log("In total %s file objects" %(sum(histogram.values())))


    finally:
        if f != sys.stdout:
            f.close()

    if hist_get('error') > 0:
        log('\n%s: *** Some files/dirs were not compared due to errors' %(prog))
        return 1

    return 0



#
# SCANNER
# =======
#
def scandir(dir,outfile,exclude):
    ''' Scan dir and write output to outfile '''

    #
    # Determine print format to use
    #

    # Default format
    format = printformat = '{fullpath}'

    if outfile:
        format = scanfile_format

    elif opts.all:
        if opts.human:
            format = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {type}  {fullpath}'
        else:
            format = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {type}  {fullpath}'

    elif opts.long:
        if opts.human:
            format = '{mode_t}  {user:8} {group:8}  {size:>5}  {mtime}  {type}  {fullpath}'
        else:
            format = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {type}  {fullpath}'

    # User provided format overrides any defaults
    format = opts.format or format


    # If dir is a file, read it as a scan-file
    if os.path.isfile(dir):
        dir = readscanfile(dir)


    # Prepare histogram
    histogram = {}
    def hist_add(objtype):
        histogram.setdefault(objtype,0)
        histogram[objtype] += 1
    def hist_get(objtype):
        return histogram.get(objtype,0)


    f = None
    try:
        size = 0

        # Setup output destination/files
        if not outfile:
            f = sys.stdout
            doprint = False
            dowrite = not opts.quiet
            quoter = lambda a: a   # No quoter on stdout
        else:
            f = open(outfile, 'w')
            doprint = opts.verbose
            dowrite = True
            quoter = lambda a: quote(a)


        # Traverse the directory
        for (path,objs) in dirscan.walkdirs([dir,]):
            obj = objs[0]

            try:

                # Ignored file?
                fullpath = obj.fullpath
                if [ fnmatch.fnmatch(fullpath, e) for e in exclude ].count(True) > 0:
                    hist_type = 'x'
                    continue

                # Failed file?
                if obj.parserr:
                    raise obj.parserr

                # Save histogram info
                hist_type = obj.objtype

                # Print to stdout?
                if doprint:
                    dump_fileinfo(path, obj, format=printformat, quoter=lambda a:a, f=sys.stdout)

                # Print to stdout or file?
                if dowrite:
                    dump_fileinfo(path, obj, format=format, quoter=quoter, f=f)

            except (IOError,OSError) as e:
                # Handle errors -- it may either come from obj.parseerr, or from
                # the dump_fileinfo() calls
                sys.stderr.write('%s: %s\n' %(prog, e))
                hist_type = 'e'

            finally:
                hist_add(hist_type)
                if hist_type == 'f':
                    size += obj.size


        if opts.summary:
            log('')
            log("Statistics of '%s':" %(dir))
            log("     %s  files, total %s" %(hist_get('f'),format_bytes(size,print_full=True) ))
            log("     %s  directories" %(hist_get('d')))
            log("     %s  symbolic links" %(hist_get('l')))
            log("     %s  special files" %(hist_get('b')+hist_get('c')+hist_get('p')+hist_get('s')))
            if hist_get('x') > 0:
                log("     %s  ignored files" %(hist_get('x')))
            if hist_get('e') > 0:
                log("     %s  files with error" %(hist_get('e')))
            log("In total %s file objects" %(sum(histogram.values())))


    finally:
        if f != sys.stdout:
            f.close()

    if hist_get('e') > 0:
        log('\n%s: *** Some files/dirs were not scanned due to errors' %(prog))
        return 1

    return 0



#
# MAIN
# ====
#
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

    # Common options
    ap.add_argument('-a', '--all', dest='all', action='store_true', default=False, help='Print all file info')
    ap.add_argument('-f', '--format', dest='format', metavar='FORMAT', default=None, help='File printing format')
    ap.add_argument('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose printing.')
    ap.add_argument('-X', '--exclude-dir', dest='exclude', metavar='PATH', action='append', default=[], help='Exclude PATH from scan. PATH is relative to DIR.')

    # Scan options
    ap.add_argument('-h', '--human', dest='human', action='store_true', default=False, help='Display human readable sizes')
    ap.add_argument('-l', '--long', dest='long', action='store_true', default=False, help='Dump file in extended format')
    ap.add_argument('-o', '--output', dest='outfile', metavar='FILE', help='Store scan output in FILE.')
    ap.add_argument('-q', '--quiet', action='store_true', dest='quiet', default=False, help='Quiet operation')
    ap.add_argument('-s', '--summary', action='store_true', dest='summary', default=False, help='Print summary')

    # Diff options
    ap.add_argument('-F', '--filter', dest='filter', action='store', default='', help='Show only difference type e=equal, l=only left, r=only right, c=changed, L=left is newest, R=right is newest, d=different type, E=error, i=ignored')
    ap.add_argument('-i', '--ignore', dest='ignore', action='store', default='', help='Ignore differences in u=uid, g=gid, p=permissions, t=time')
    ap.add_argument('-t', '--traverse', dest='traverse', action='store_true', default=False,
                    help='Traverse the children of directories that exists on only one side.')

    ap.add_argument('dir1', metavar='DIR1', help='Directory to scan/traverse')
    ap.add_argument('dir2', metavar='DIR2', help='If present, compare DIR1 with DIR2', default=False, nargs='?')

    # FIXME:  Other possible options:
    #   --print0  to safely interact with xargs -0
    #   --filter  on scan to show only certain kind of file types


    # -- Global options not passed via function arguments
    global opts
    opts = ap.parse_args()
    global prog
    prog = ap.prog


    # -- Make sure all exclude rules have additional 'name/*' in the list as well to make sure we also ignore sub-dirs
    exclude = []
    for e in opts.exclude:
        exclude.append( os.path.join(opts.dir1,e) )
        if not e.endswith('*'):
            exclude.append( os.path.join(opts.dir1,e,'*') )


    # -- COMMAND HANDLING
    if not opts.dir2:
        return scandir(opts.dir1,opts.outfile,exclude)
    else:
        return diffdirs(opts.dir1,opts.dir2,exclude)



if __name__ == '__main__':
    main()
