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

import argparse

from . import __version__


DIRSCAN_DESCRIPTION = '''
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


DIRSCAN_FORMAT_HELP = '''
format template:
  The --format, -F, option enables printing custom lines for each of the
  scanned files. The argument is a string using Python str.format() syntax.

  Common format fields:
    {path}              Common relative path
    {change}            Compare relationship, e.g. 'equal'
    {arrow}             ASCII graphics for ease of indication
    {text}              Human readable text for the change

  File-specific format fields:
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
  The --summary option enables custom output fields for printing the
  statistics at the end of execution.

  Common summary fields:
    {prog}              Name of the program

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

  Supported summary fields in comparing two directories:
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


def dirscan_argumentparser():
    ''' Return argument parser object for dirscan, and setting all command-line
        options
    '''

    argp = argparse.ArgumentParser(description=DIRSCAN_DESCRIPTION,
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   add_help=False)

    argp.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    argp.add_argument('--help', action='help')

    argp.add_argument('-a', '--all', action='store_true', dest='all', default=False,
                      help='''
        Print all file info
        ''')
    argp.add_argument('-c', '--compare', metavar='TYPES', action='store',
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
    argp.add_argument('-d', '--compare-dates', action='store_true',
                      dest='compare_dates', default=False, help='''
        Compare dates on files which are otherwise equal
        ''')
    argp.add_argument('-f', '--file-types', metavar='TYPES', action='store',
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
    argp.add_argument('-F', '--format', metavar='TEMPLATE', dest='format',
                      default=None, help='''
        Custom file info line template. See FORMAT  ''')
    argp.add_argument('-h', '--human', action='store_true', dest='human',
                      default=False, help='''
        Display human readable sizes
        ''')
    argp.add_argument('-i', '--ignore', metavar='IGNORES', action='store',
                      dest='ignore', default='', help='''
        Ignore compare differences in u=uid, g=gid, p=permissions, t=time
        ''')
    argp.add_argument('-l', '--long', action='store_true', dest='long',
                      default=False, help='''
        Dump file in extended format
        ''')
    argp.add_argument('-o', '--output', metavar='FILE', action='store',
                      dest='outfile', help='''
        Store scan output in FILE
        ''')
    argp.add_argument('-q', '--quiet', action='store_true', dest='quiet',
                      default=False, help='''
        Quiet operation
        ''')
    argp.add_argument('-Q', '--suppress-errors', action='store_true',
                      dest='realquiet', default=False, help='''
        Suppress error messages
        ''')
    argp.add_argument('-r', '--reverse', action='store_true', dest='reverse',
                      default=False, help='''
        Traverse directories in reverse order
        ''')
    argp.add_argument('-s', action='store_true', dest='enable_summary',
                      default=False, help='''
        Print scan statistics summary.
        ''')
    argp.add_argument('--summary', metavar='SUMMARY_TEMPLATE',
                      action='append', dest='summary', default=None, help='''
        Print scan statistics summary and provide custom template.
        ''')
    argp.add_argument('-t', '--traverse-oneside', action='store_true',
                      dest='traverse_oneside', default=False, help='''
        Traverse directories that exists on only one side of comparison
        ''')
    argp.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                      default=False, help='''
        Verbose printing
        ''')
    argp.add_argument('-x', '--one-file-system', action='store_true', dest='onefs',
                      default=False, help='''
        Don't cross filesystem boundaries
        ''')
    argp.add_argument('-X', '--exclude', metavar='PATH', action='append',
                      dest='exclude', default=[], help='''
        Exclude PATH from scan. PATH is relative to DIR
        ''')
    argp.add_argument('--left', '--input', action='store_true', dest='left', default=None,
                      help='''
        Read LEFT_DIR argument as a scanfile
        ''')
    argp.add_argument('--right', action='store_true', dest='right', default=None,
                      help='''
        Read RIGHT_DIR argument as a scanfile
        ''')
    argp.add_argument('--format-help', action='store_true', dest='formathelp', default=None,
                      help='''
        Show help for --format and --summary
        ''')

    # Main arguments
    argp.add_argument('dir1', metavar='LEFT_DIR', default=None, nargs='?',
                      help='''
        Directory to scan/traverse, or LEFT side of comparison
        ''')
    argp.add_argument('dir2', metavar='RIGHT_DIR', default=None, nargs='?',
                      help='''
        RIGHT side of comparison if preset
        ''')

    return argp
