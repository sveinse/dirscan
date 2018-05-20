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
import os
import argparse
import datetime

from . import __version__
from . import dirscan
from . import fileinfo


#
# SCAN FILE READER
# ================
#
SCANFILE_FORMAT = "{type},{size},{mode},{uid},{gid},{mtime_n},{data},{path}"

def readscanfile(fname):
    ''' Read fname scan file and return a DirObj() with the file tree root '''

    dirtree = {}
    rootobj = None

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
                opath = fname
            elif opath.startswith('./'):
                opath = opath.replace('./', fname+'/', 1)

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
                dirtree[path][name] = obj

            # Make sure we make an entry into the dirtree to ensure
            # we have a list of the parents
            if otype == 'd':
                dirtree[opath] = obj

    if not rootobj:
        raise dirscan.DirscanException("Scanfile '%s' is empty" %(fname,))

    # Now the tree should be populated
    return rootobj



#
# OBJECT COMPARATOR
# =================
def dir_compare1(objs, ignores='', compare_dates=False):
    ''' Object comparator for 1 dir. Returns tuple with (change, text) '''

    # Comparison matrix for 1 dir
    # ---------------------------
    #    x    excluded  Excluded
    #    *    scan      Scan

    if objs[0].excluded:
        # File EXCLUDED
        # =============
        return ('excluded', 'excluded')

    return ('scan', 'scan')


def dir_compare2(objs, ignores='', compare_dates=False):
    ''' Object comparator for two dirs. Returns a tuple with (change, text) '''

    # Comparison matrix for 2 dirs
    # -----------------------------
    #    xx   excluded        Excluded
    #    x-   excluded        Left excluded, not present in right
    #    x*   excluded        Only in right, left is excluded
    #    a-   left_only       Only in left
    #    -a   right_only      Only in right
    #    ab   different_type  Different type: %a in left, %b in right
    #    ab   changed         %t changed: ...
    #         left_newer
    #         right_newer
    #    aa   Equal

    if all([o.excluded for o in objs]):
        # File EXCLUDED
        # =============
        if objs[0].objtype  == '-':
            return ('excluded', 'Right excluded, not present in left')
        if objs[1].objtype  == '-':
            return ('excluded', 'Left excluded, not present in right')
        return ('excluded', 'excluded')

    if objs[0].objtype == '-' or objs[0].excluded:
        # File present RIGHT only
        # =======================
        text = "%s only in right" %(objs[1].objname,)
        if objs[0].excluded:
            text += ", left is excluded"
        return ('right_only', text)

    if objs[1].objtype == '-' or objs[1].excluded:
        # File present LEFT only
        # ======================
        text = "%s only in left" %(objs[0].objname,)
        if objs[0].excluded:
            text += ", right is excluded"
        return ('left_only', text)

    s = set([o.objtype for o in objs])
    if len(s) > 1:
        # File type DIFFERENT
        # ===================
        text = "Different type, %s in left and %s in right" %(
            objs[0].objname, objs[1].objname)
        return ('different_type', text)

    # File type EQUAL
    # ===============

    # compare returns a list of differences. If None, they are equal
    # This might fail, so be prepared to catch any errors
    rl = objs[0].compare(objs[1])
    if rl:
        # Make a new list and filter out the ignored differences
        el = []
        change = 'changed'
        for r in rl:
            if 'newer' in r:
                if len(rl) == 1 and not compare_dates:
                    continue
                if 't' in ignores:
                    continue
                r = 'left is newer'
                change = 'left_newer'
            elif 'older' in r:
                if len(rl) == 1 and not compare_dates:
                    continue
                if 't' in ignores:
                    continue
                r = 'right is newer'
                change = 'right_newer'
            elif 'u' in ignores and 'UID differs' in r:
                continue
            elif 'g' in ignores and 'GID differs' in r:
                continue
            elif 'p' in ignores and 'permissions differs' in r:
                continue
            el.append(r)

        if el:  # else from this test indicates file changed, but all
                # changes have been masked with above ignore settings

            # File contents CHANGED
            # =====================
            text = "%s changed: %s" %(objs[0].objname, ", ".join(el))
            return (change, text)

        # Compares with changes may fall through here because of
        # ignore settings

    # File contents EQUAL
    # ===================
    return ('equal', 'equal')


#
# SCAN DIRS
# =========
#
def scandirs(left, right, opts):
    ''' Scan dirs '''

    #
    # Determine print format
    # ----------------------
    #

    # Default format
    fmt = printfmt = '{path}'

    # Determine default format from options
    if right is None:
        dir_comparator = dir_compare1
        fmt = '{fullpath}'
        comparetypes = 's'
        filetypes = 'fdlbcps'
        printfmt = fmt

        if opts.outfile:
            fmt = SCANFILE_FORMAT

        elif opts.all and opts.long:
            if opts.human:
                fmt = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {mtime}  {type}  {fullpath}'
            else:
                fmt = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {mtime}  {type}  {fullpath}'

        elif opts.all:
            if opts.human:
                fmt = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {type}  {fullpath}'
            else:
                fmt = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {type}  {fullpath}'

        elif opts.long:
            if opts.human:
                fmt = '{mode_t}  {user:8} {group:8}  {size:>5}  {mtime}  {type}  {fullpath}'
            else:
                fmt = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {type}  {fullpath}'

    else:
        dir_comparator = dir_compare2
        fmt = '{arrow}  {path}  :  {text}'
        comparetypes = 'rldcLR'
        filetypes = 'fdlbxps'

        # Does outfile make any sense in compare mode?

        if opts.all:
            comparetypes = ''.join([
                fileinfo.COMPARE_ARROWS[x][0] for x in fileinfo.COMPARE_ARROWS])

    # User provided format overrides any defaults
    fmt = opts.format or fmt
    comparetypes = opts.comparetypes or comparetypes
    filetypes = opts.filetypes or filetypes
    # -------------------------------------------------


    # Prepare the histograms to collect statistics
    comparehist = fileinfo.CompareHistogram(left, right)
    if right is None:
        filehist = [fileinfo.FileHistogram(left)]
        prefixlist = ['']
    else:
        filehist = [fileinfo.FileHistogram(left), fileinfo.FileHistogram(right)]
        prefixlist = ['l_', 'r_']



    f = None
    try:

        # Setup output destination/files
        if not opts.outfile:
            f = sys.stdout
            doprint = False
            dowrite = not opts.quiet
            quoter = lambda a: a   # No quoter on stdout
        else:
            f = open(opts.outfile, 'w')
            doprint = opts.verbose
            dowrite = True
            quoter = lambda a: fileinfo.quote(a)


        # Prepare the list of formats to use
        formatlist = []
        if doprint:
            formatlist.append(printfmt)
        if dowrite:
            if not (doprint and printfmt == fmt):
                formatlist.append(fmt)


        # If either left or write is file, they should be parsed as scan files
        if os.path.isfile(left):
            left = readscanfile(left)
        if right and os.path.isfile(right):
            right = readscanfile(right)


        # Create the list of directories to traverse
        dirs = [left]
        if right is not None:
            dirs.append(right)


        def error_handler(exception):
            comparehist.add('err')
            if not opts.realquiet:
                sys.stderr.write('%s: %s\n' %(opts.prog, exception))
            return True


        for (path, objs) in dirscan.walkdirs(
                dirs,
                reverse=opts.reverse,
                excludes=opts.exclude,
                onefs=opts.onefs,
                traverse_oneside=opts.traverse_oneside,
                exception_fn=error_handler):

            show = True
            fields = {}

            # Save file histogram info
            for (o, fh) in zip(objs, filehist):
                ot = 'x' if o.excluded else o.objtype
                fh.add(ot)
                if ot == 'f':
                    fh.add_size(o.size)

            # Compare the objects
            try:
                (change, text) = dir_comparator(
                    objs,
                    ignores=opts.ignore,
                    compare_dates=opts.compare_dates)
            except IOError as err:
                # Errors here are due to comparisons that fail. Add them
                # as errors
                error_handler(err)
                change = 'error'
                fields['change'] = change
                text = 'Compare failed: ' + str(err)

            # Show this file type?
            if not any([o.objtype in filetypes for o in objs]):
                show = False

            # Get dict of file info fields used by the formatlist
            if show:
                (err, fields) = fileinfo.get_fileinfo(path, objs, change, text,
                                                      prefixlist, formatlist)
                if err:
                    # Errors here is because the field could not be read, e.g.
                    # hashsum
                    error_handler(err)

            # Bail out if the change type is excluded from the show filter
            if fileinfo.COMPARE_ARROWS[change][0] not in comparetypes:
                show = False

            # Print to stdout (used if writing to file)
            if show and doprint:
                fileinfo.write_fileinfo(fields, printfmt, quoter=lambda a: a,
                                        out=sys.stdout)

            # Write to stdout or file
            if show and dowrite:
                fileinfo.write_fileinfo(fields, fmt, quoter=quoter, out=f)

            # Save histogram info for the change type
            comparehist.add(change)


    finally:
        # Close any open output file
        if f and f != sys.stdout:
            f.close()


    #has_errors = False
    if opts.summary is not None:

        summary_fields = {
            'prog':  opts.prog,
        }

        # Get the global comparison summary
        summary_fields.update(comparehist.get_summary_fields())

        # Assemble the per-directory summaries
        for (fh, pre) in zip(filehist, prefixlist):
            for field, data in fh.get_summary_fields().items():

                # Replace 'n_' with specified prefix
                if field.startswith('n_') and pre:
                    field = field[2:]
                summary_fields[pre + field] = data

        # Get the summary texts
        if any(opts.summary):
            summary_text = [(True, s) for s in opts.summary]
        else:
            if right is None:
                summary_text = list(fileinfo.SUMMARY_SCAN)
            else:
                summary_text = list(fileinfo.SUMMARY_COMPARE)

            if not opts.realquiet:
                summary_text.append(
                    ('n_err',
                     "\n{prog}: **** {n_err} files or directories could not be read")
                )

        # Print the summary text
        try:
            # Use the pre-defined summary_text
            for (doprint, line) in summary_text:
                # d.get(n,n) will return the d value for n if n exists, otherwise return n.
                # Thus if n is True, True will be returned
                if line is not None and summary_fields.get(doprint, doprint):
                    sys.stderr.write(line.format(**summary_fields)+'\n')

        # .format() might fail
        except (KeyError, IndexError, ValueError) as err:
            raise SyntaxError("Format error: %s" %(err))


    # Return error code if we have encountered any errors scanning
    if comparehist.get('err'):
        return 1

    return 0



#
# MAIN
# ====
#
def main(args=None):
    ''' Main dirscan command-line interface '''

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

(C) 2010-2018 Svein Seldal. This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.

'''
    epilog = ''

    ap = argparse.ArgumentParser(description=description, epilog=epilog, add_help=False)
    ap.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    ap.add_argument('--help', action='help')

    # Common options
    ap.add_argument('-a', '--all', action='store_true', dest='all', default=False, help='Print all file info')
    ap.add_argument('-c', '--compare', metavar='TYPES', action='store', dest='comparetypes', default='', help='Show only compare types e=equal, l=only left, r=only right, c=changed, L=left is newest, R=right is newest, t=different type, E=error, x=excluded')
    ap.add_argument('-d', '--compare-dates', action='store_true', dest='compare_dates', default=False, help='Compare dates on files which are otherwise equal')
    ap.add_argument('-f', '--file-types', metavar='TYPES', action='store', dest='filetypes', default='', help='Show only file types. f=files, d=dirs, l=links, b=blkdev, c=chrdev, p=pipes, s=sockets')
    ap.add_argument('-F', '--format', metavar='TEMPLATE', dest='format', default=None, help='Custom file info line template')
    ap.add_argument('-h', '--human', action='store_true', dest='human', default=False, help='Display human readable sizes')
    ap.add_argument('-i', '--ignore', metavar='IGNORES', action='store', dest='ignore', default='', help='Ignore compare differences in u=uid, g=gid, p=permissions, t=time')
    ap.add_argument('-l', '--long', action='store_true', dest='long', default=False, help='Dump file in extended format')
    ap.add_argument('-o', '--output', metavar='FILE', action='store', dest='outfile', help='Store scan output in FILE')
    ap.add_argument('-q', '--quiet', action='store_true', dest='quiet', default=False, help='Quiet operation')
    ap.add_argument('-Q', '--suppress-errors', action='store_true', dest='realquiet', default=False, help='Suppress error messages')
    ap.add_argument('-r', '--reverse', action='store_true', dest='reverse', default=False, help='Traverse directories in reverse order')
    ap.add_argument('-s', '--summary', metavar='SUMMARY_TEMPLATE', nargs='?', action='append', dest='summary', default=None, help='Print scan statistics summary. Optional argument specified custom summary template. The option can be used multiple times for multiple template lines')
    ap.add_argument('-t', '--traverse-oneside', action='store_true', dest='traverse_oneside', default=False, help='Traverse directories that exists on only one side of comparison')
    ap.add_argument('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose printing')
    ap.add_argument('-x', '--one-file-system', action='store_true', dest='onefs', default=False, help="Don't cross filesystem boundaries")
    ap.add_argument('-X', '--exclude', metavar='PATH', action='append', dest='exclude', default=[], help='Exclude PATH from scan. PATH is relative to DIR')

    # Main arguments
    ap.add_argument('dir1', metavar='LEFT_DIR', help='Directory to scan/traverse, or LEFT side of comparison')
    ap.add_argument('dir2', metavar='RIGHT_DIR', help='RIGHT side of comparison if preset', default=None, nargs='?')

    # FIXME:  Other possible options:
    #   --print0  to safely interact with xargs -0
    #   --filter  on scan to show only certain kind of file types


    # -- Parsing and washing
    opts = ap.parse_args()
    opts.prog = ap.prog

    # Not having onesided traversion in scan mode does not print anything
    if opts.dir2 is None:
        opts.traverse_oneside = True


    # -- COMMAND HANDLING
    try:
        return scandirs(opts.dir1, opts.dir2,
                        opts=opts)
    except dirscan.DirscanException as err:
        # Handle user-specific errors
        print(ap.prog + ': ' + str(err))
        return 1


if __name__ == '__main__':
    main()
