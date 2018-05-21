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

from . import __version__
from . import dirscan
from . import fileinfo
from .scanfile import SCANFILE_FORMAT, readscanfile


#
# OBJECT COMPARATORS
# ==================

def dir_compare1(objs, ignores='', comparetypes='', compare_dates=False):
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



def dir_compare2(objs, ignores='', comparetypes='', compare_dates=False):
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
        if objs[1].excluded:
            return ('excluded', 'excluded, only in right')
        if objs[0].excluded:
            text += ", left is excluded"
        return ('right_only', text)

    if objs[1].objtype == '-' or objs[1].excluded:
        # File present LEFT only
        # ======================
        text = "%s only in left" %(objs[0].objname,)
        if objs[0].excluded:
            return ('excluded', 'excluded, only in left')
        if objs[1].excluded:
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

    # Unless we're not intersted in these comparetypes, then we don't have
    # to spend time on making the compare (which can be time consuming)
    needcompare=set('cLRe')
    if not needcompare.intersection(comparetypes):
        return ('skipped', 'compare skipped')

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


    # Create the list of directories to traverse
    dirs = [left]
    if right is not None:
        dirs.append(right)


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
        comparetypes = 'rltcLR'
        filetypes = 'fdlbcps'

        # Does outfile make any sense in compare mode?

    # The all option will show all compare types
    if opts.all:
        comparetypes = ''.join([
            fileinfo.COMPARE_ARROWS[x][0] for x in fileinfo.COMPARE_ARROWS])

    # User provided format overrides any defaults
    fmt = opts.format or fmt
    comparetypes = opts.comparetypes or comparetypes
    filetypes = opts.filetypes or filetypes
    # -------------------------------------------------


    # Prepare the histograms to collect statistics
    s_left = left.fullpath if isinstance(left, dirscan.BaseObj) else left
    s_right = right.fullpath if isinstance(right, dirscan.BaseObj) else right
    comparehist = fileinfo.CompareHistogram(s_left, s_right)
    if right is None:
        filehist = [fileinfo.FileHistogram(s_left)]
        prefixlist = ['']
    else:
        filehist = [fileinfo.FileHistogram(s_left), fileinfo.FileHistogram(s_right)]
        prefixlist = ['l_', 'r_']


    #
    # Directory scanning
    # -------------------
    #

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


        def error_handler(exception):
            ''' Callback for handling scanning errors during parsing '''
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

            # Compare the objects
            try:
                (change, text) = dir_comparator(
                    objs,
                    ignores=opts.ignore,
                    comparetypes=comparetypes,
                    compare_dates=opts.compare_dates)
            except IOError as err:
                # Errors here are due to comparisons that fail.
                error_handler(err)
                change = 'error'
                #fields['change'] = change
                text = 'Compare failed: ' + str(err)

            show = True

            # Show this file type?
            if not any([o.objtype in filetypes for o in objs]):
                show = False

            # Show this compare type?
            if fileinfo.COMPARE_ARROWS[change][0] not in comparetypes:
                show = False

            # Save file histogram info only if the object is about to be
            # Printed
            if show:
                for (o, fh) in zip(objs, filehist):
                    ot = 'x' if o.excluded else o.objtype
                    fh.add(ot)
                    if ot == 'f':
                        fh.add_size(o.size)

            # Get dict of file info fields used by the formatlist
            if show:
                (err, fields) = fileinfo.get_fileinfo(path, objs, change, text,
                                                      prefixlist, formatlist)
                if err:
                    # Errors here is because the field could not be read,
                    # e.g. from hashsum
                    error_handler(err)

                # Print to default stdout (used if writing to file)
                if doprint:
                    fileinfo.write_fileinfo(printfmt, fields)

                # Write to stdout or file
                if dowrite:
                    fileinfo.write_fileinfo(fmt, fields, quoter=quoter, file=f)

            # Save histogram info for the change type
            comparehist.add(change)


    finally:
        # Close any open output file
        if f and f != sys.stdout:
            f.close()


    #
    # Summary printing
    # ----------------
    #

    summary_text = []
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
    if opts.enable_summary:
        if opts.summary:
            summary_text = [(True, s) for s in opts.summary]
        else:
            if right is None:
                summary_text = list(fileinfo.SUMMARY_SCAN)
            else:
                summary_text = list(fileinfo.SUMMARY_COMPARE)

    # Append final warning for errors
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
save the file list into a scanfile with the -o option. The scanfile stores
all files metadata, including sha256 hashsum of the file.

A DIR1 DIR2 argument is used to compare directories, showing differences
between DIR1 and DIR2. DIR1 or DIR2 can be either a directory or a previous
generated scan file.

(C) 2010-2018 Svein Seldal. This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.

'''
    format_help = '''
format template:
  The --format, -F, option enables printing custom lines for each of the
  scanned files. The argument is a string using Python str.format() syntax.

  The scan/compare fields:
    {path}              Common, relative path
    {change}            Compare relationship, e.g. 'equal'
    {arrow}             ASCII graphics for ease of indication
    {text}              Human readable text for the change

  Supported file fields:
    {name}              Name of the file or directory
    {fullpath}          Full path of the file or directory
    {user}              Username
    {uid}               User ID
    {group}             The group name
    {gid}               Group ID
    {mode}              The mode fields as a number
    {mode_t}            Text representation of the mode field
    {type}              File type, f=file, d=dir, l=link, b=block device,
                        c=char device, p=pipe, s=socket
    {size}              File size
    {size_h}            File size in human readable size
    {mtime}             Modify time
    {mtime_n}           Modify time in integer
    {data}              Data field. The hashsum for files and the link target
                        for symlinks
    {dev}               The device number for the filesystem
  In compare mode, the fields for the left and right file objects can be
  accessed by prefixing with 'l_' or 'r_'. e.g. {l_name}.

summary template:
  The --summary option enables custom output fields when printing the
  statistics at the end of execution.

  Supported summary fields when scanning:
    {dir}               The base directory
    {n_files}           Count of ordinary files
    {n_dirs}            Count of directories
    {n_symlinks}        Count of symlinks
    {n_special}         Count of special files
    {n_blkdev}          Count of block device nodes
    {n_chrdev}          Count of character device nodes
    {n_fifos}           Count of fifos
    {n_sockets}         Count of sockets
    {n_missing}         Count of missing files (in compare)
    {n_exclude}         Count of excluded objects
    {n_objects}         Sum of all objects
    {sum_bytes}         Total number of bytes
    {sum_bytes_t}       Number of bytes in human readable form
  In compare mode, the summary fields for the left and right file objects can
  be accessed by replacing 'n_' with 'l_' or 'r_', e.g. {l_sum_bytes} and
  {l_files}.

  Supported summary fields in compare mode:
    {left}              Left side directory
    {right}             Right side directory
    {n_equal}           Count of equal comparisons
    {n_changed}         Count of changed files or directory
    {n_different_type}  Count of different types
    {n_left_only}       Count of files only in left side
    {n_right_only}      Count of files only in right side
    {n_left_newer}      Count of changed files where left is newest
    {n_right_newer}     Count of changed files where right is newest
    {n_scan}            Count of scanned files or folders (not compare)
    {n_excludes}        Count of excluded files or folders
    {n_errors}          Count of compare errors
    {n_skipped}         Count of skipped compares
    {n_err}             Total number of OS errors
    {sum_objects}       Total number of objects compared
'''

    ap = argparse.ArgumentParser(description=description,
                                 #epilog=format_help,
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 add_help=False)
    ap.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    ap.add_argument('--help', action='help')

    # Common options
    ap.add_argument('-a', '--all', action='store_true', dest='all', default=False,
                    help='''
        Print all file info
        ''')
    ap.add_argument('-c', '--compare', metavar='TYPES', action='store',
                    dest='comparetypes', default='', help='''
        Show only compare relationship TYPES:
            e=equal,
            l=left only,
            r=right only,
            c=changed,
            L=left is newest,
            R=right is newest,
            t=different type,
            E=error,
            x=excluded
        ''')
    ap.add_argument('-d', '--compare-dates', action='store_true',
                    dest='compare_dates', default=False, help='''
        Compare dates on files which are otherwise equal
        ''')
    ap.add_argument('-f', '--file-types', metavar='TYPES', action='store',
                    dest='filetypes', default='', help='''
        Show only file types.
            f=files,
            d=dirs,
            l=links,
            b=blkdev,
            c=chrdev,
            p=pipes,
            s=sockets
        ''')
    ap.add_argument('-F', '--format', metavar='TEMPLATE', dest='format',
                    default=None, help='''
        Custom file info line template. See FORMAT  ''')
    ap.add_argument('-h', '--human', action='store_true', dest='human',
                    default=False, help='''
        Display human readable sizes
        ''')
    ap.add_argument('-i', '--ignore', metavar='IGNORES', action='store',
                    dest='ignore', default='', help='''
        Ignore compare differences in u=uid, g=gid, p=permissions, t=time
        ''')
    ap.add_argument('-l', '--long', action='store_true', dest='long',
                    default=False, help='''
        Dump file in extended format
        ''')
    ap.add_argument('-o', '--output', metavar='FILE', action='store',
                    dest='outfile', help='''
        Store scan output in FILE
        ''')
    ap.add_argument('-q', '--quiet', action='store_true', dest='quiet',
                    default=False, help='''
        Quiet operation
        ''')
    ap.add_argument('-Q', '--suppress-errors', action='store_true',
                    dest='realquiet', default=False, help='''
        Suppress error messages
        ''')
    ap.add_argument('-r', '--reverse', action='store_true', dest='reverse',
                    default=False, help='''
        Traverse directories in reverse order
        ''')
    ap.add_argument('-s', action='store_true', dest='enable_summary',
                    default=False, help='''
        Print scan statistics summary.
        ''')
    ap.add_argument('--summary', metavar='SUMMARY_TEMPLATE', nargs='*',
                    action='append', dest='summary', default=None, help='''
        Print scan statistics summary and provide custom template.
        ''')
    ap.add_argument('-t', '--traverse-oneside', action='store_true',
                    dest='traverse_oneside', default=False, help='''
        Traverse directories that exists on only one side of comparison
        ''')
    ap.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                    default=False, help='''
        Verbose printing
        ''')
    ap.add_argument('-x', '--one-file-system', action='store_true', dest='onefs',
                    default=False, help='''
        Don't cross filesystem boundaries
        ''')
    ap.add_argument('-X', '--exclude', metavar='PATH', action='append',
                    dest='exclude', default=[], help='''
        Exclude PATH from scan. PATH is relative to DIR
        ''')
    ap.add_argument('--left', '--input', action='store_true', dest='left', default=None,
                    help='''
        Read LEFT_DIR argument as a scanfile
        ''')
    ap.add_argument('--right', action='store_true', dest='right', default=None,
                    help='''
        Read RIGHT_DIR argument as a scanfile
        ''')
    ap.add_argument('--format-help', action='store_true', dest='formathelp', default=None,
                    help='''
        Show help for --format and --summary
        ''')

    # Main arguments
    ap.add_argument('dir1', metavar='LEFT_DIR', default=None, nargs='?',
                    help='''
        Directory to scan/traverse, or LEFT side of comparison
        ''')
    ap.add_argument('dir2', metavar='RIGHT_DIR', default=None, nargs='?',
                    help='''
        RIGHT side of comparison if preset
        ''')


    # -- Parsing and washing
    opts = ap.parse_args()
    opts.prog = ap.prog

    # Requested more help?
    if opts.formathelp:
        ap.print_help()
        print(format_help)
        ap.exit(1)

    # Not having onesided traversion in scan mode does not print anything
    if opts.dir2 is None:
        opts.traverse_oneside = True

    # Enable summary if summary templates are given
    if opts.summary:
        opts.enable_summary = True

    # Missing options
    if not opts.dir1:
        ap.error("Missing LEFT_DIR argument")
    if opts.right and not opts.dir2:
        ap.error("Missing RIGHT_DIR argument")

    # Read the scan files
    if opts.left:
        opts.dir1 = readscanfile(opts.dir1)
    if opts.right:
        opts.dir2 = readscanfile(opts.dir2)


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
