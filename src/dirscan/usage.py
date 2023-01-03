''' Dirscan - command-line arguments and help descriptions '''
#
# Copyright (C) 2010-2023 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

import argparse

from dirscan import __version__


DIRSCAN_DESCRIPTION = '''
Tool for scanning and comparing directories.

A single LEFT_DIR argument will traverse the given directory or scan file and
print the contents, similar to ls or find, and can provide a customizable
summary of the found files.

The -o options will save the directory traversal into a scan file, which can
be used for later comparisons against other directories or scan files. The
scan file stores file metadata for the directory tree, and it stores a sha256
hashsum for the files. This makes it reliable to use a scan file to check for
changes to a directory.

Using a LEFT_DIR RIGHT_DIR argument will compare directories, showing the
differences between LEFT_DIR and RIGHT_DIR. Either arguments can be
directories or scan files.

Copyright (C) 2010-2023 Svein Seldal
This application is licensed under MIT license (see
https://github.com/sveinse/dirscan for details)

'''


DIRSCAN_FORMAT_HELP = '''
FORMAT template:
  The --format, -F, option enables printing custom lines for each of the
  scanned files. The argument is a string using Python str.format() syntax.

  Common format fields:
    {relpath}           Common relative path
    {relpath_p}         Common relative path in unix '/' format
    {change}            Compare relationship, e.g. 'equal'
    {change_t}          Compare relationship in single letter
    {arrow}             ASCII graphics for ease of indication
    {text}              Human readable text for the change

  File-specific format fields:
    {name}              Name of the file or directory
    {path}              Full path of the file or directory
    {user}              Username
    {uid}               User ID
    {group}             The group name
    {gid}               Group ID
    {mode}              The mode fields as a number
    {mode_h}            Human readable representation of the mode field
    {type}              File type, f=file, d=dir, l=link, b=block device,
                        c=char device, p=pipe, s=socket
    {size}              File size
    {size_h}            File size in human readable size
    {mtime_h}           Modify time in format '%Y-%m-%d %H:%M:%S'
    {mtime_f}           Modify time in seconds (float)
    {mtime_x}           Modify time in seconds (hex)
    {data}              Data field. The hashsum for files and the link target
                        for symlinks
    {dev}               The device number for the filesystem
  In compare mode, the fields for the left and right file objects can be
  accessed by prefixing with 'l_' or 'r_'. e.g. {l_name}.

  Format fields available under --duplicates:
    {dupinfo}           List of all files that are equal to this file
    {dup}               The text 'DUP' otherwise '   '
    {dupcount}          The number of occurrences this file has

SUMMARY_FORMAT template:
  The --summary-format option enables custom output fields for printing the
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
    {n_err}             Count of OS errors
    {n_objects}         Count of objects compared

FILTER_TYPES description:
  The --filter, -f option allows specifying which relation types are shown
  when scanning or comparing directories. The argument supports the following
  combinable options:
    e - equal files. Both files are the same type and contents are equal
    c - content differs. The file exists in both sides and are of the same type,
        but the contents differs.
    l - left only. The file is only present on LEFT side
    r - right only. The file is only present on RIGHT side
    L - left is newest. The files exists in both sides, but the contents
        differs with the LEFT file being the newest. Using --ignore=t will
        change this compare type into a 'c'.
    R - right is newest. The files exists in both sides, but the contents
        differs with the RIGHT file being the newest. Using --ignore=t will
        change this compare type into a 'c'.
    n - left has been renamed. This applies when used with --shadiff
    m - right has been renamed. This applies when used with --shadiff
    t - different type. The file/object exists in both LEFT and RIGHT side, but
        as different file types, e.g. file and directory.
    E - compare error. One object could not be read.
    x - excluded. File has been excluded.
    s - scan. The filter type when scanning a directory
    d - duplicated. Indicates that the file exists multiple times. Used with
        --duplicates
    i - ignored. Any file that is of type NOT shown with --types

  If the FILTER_TYPES are prefixed with '^', the types will be inverted, where
  the listed types will not be included.
'''


def argument_parser() -> argparse.ArgumentParser:
    ''' Return argument parser object for dirscan, and setting all command-line
        options
    '''

    argp = argparse.ArgumentParser(
        description=DIRSCAN_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
        prog="dirscan",
    )

    argp.add_argument('--help', action='help')

    argp.add_argument('-0', '--print0', action='store_true', dest='print0',
                      default=False, help='''
        Print each line using the NUL char instead of the newline char
        ''')
    argp.add_argument('-a', '--all', action='store_true', dest='all',
                      default=False, help='''
        Print all file info
        ''')
    argp.add_argument('-d', '--dup', '--duplicates', action='store_true',
                      dest='duplicates', default=False, help='''
        Find and show duplicate files.
        ''')
    argp.add_argument('-D', '--debug', action='count', dest='debug',
                      default=0, help='''
        Enable debug output
        ''')
    argp.add_argument('-f', '--filter', metavar='FILTER_TYPES', action='store',
                      dest='compare_types', default='', help='''
        When comparing, show only the following compare relationship:
            e=equal,
            c=changed,
            l=left only,
            L=left is newest,
            n=left only and renamed from right,
            r=right only,
            m=right renamed,
            R=right is newest,
            t=different type,
            E=error,
            x=excluded,
            s=scan,
            d=duplicated,
            i=ignored.
        Prefix with '^' inverts selection. See FILTER_TYPES under --format-help.
        ''')
    argp.add_argument('-F', '--format', metavar='FORMAT', dest='format',
                      default=None, help='''
        Per line file info template. See --format-help for detailed syntax
        ''')
    argp.add_argument('-h', '--human', action='store_true', dest='human',
                      default=False, help='''
        Display human readable sizes
        ''')
    argp.add_argument('-H', '--sha', '--shadiff', action='store_true',
                      dest='shadiff', default=None, help='''
        Turn on comparing using the calculated sha hashsum of the files. This
        enables showing files that have been renamed.
        ''')
    argp.add_argument('-i', '--ignore', metavar='IGNORES', action='store',
                      dest='ignore', default='', help='''
        Ignore compare differences in:
            u=uid,
            g=gid,
            p=permissions,
            t=time.
        ''')
    argp.add_argument('-l', '--long', action='store_true', dest='long',
                      default=False, help='''
        Dump file in extended format
        ''')
    argp.add_argument('-o', '--output', metavar='FILE', action='store',
                      dest='outfile', help='''
        Store scan output in FILE
        ''')
    argp.add_argument('-p', '--progress', action='store_true', dest='progress',
                      default=False, help='''
        Show progress while scanning
        ''')
    argp.add_argument('-q', '--quiet', action='store_true', dest='quiet',
                      default=False, help='''
        Quiet operation
        ''')
    argp.add_argument('-Q', '--suppress-errors', action='store_true',
                      dest='quieterr', default=False, help='''
        Suppress error messages
        ''')
    argp.add_argument('-R', '--reverse', action='store_true', dest='reverse',
                      default=False, help='''
        Traverse directories in reverse order
        ''')
    argp.add_argument('-r', '--recursive', action='store_true',
                      dest='recurse', default=False, help='''
        Traverse directories recursively that exists on only one side of
        comparison. Normally dirscan skips entering directories that only exists
        on one side.
        ''')
    argp.add_argument('-s', '--summary', action='store_true',
                      dest='enable_summary', default=False, help='''
        Print scan statistics summary.
        ''')
    argp.add_argument('-S', '--summary-format', metavar='SUMMARY_FORMAT',
                      action='append', dest='summary', default=None, help='''
        Print scan statistics summary and provide custom template. See
        --format-help for more info about syntax
        ''')
    argp.add_argument('-t', '--types', metavar='TYPES', action='store',
                      dest='filetypes', default='', help='''
        Show only file types.
            f=files,
            d=dirs,
            l=links,
            b=blkdev,
            c=chrdev,
            p=pipes,
            s=sockets.
        Prefix with '^' inverts selection.
        ''')
    argp.add_argument('-T', '--compare-time', action='store_true',
                      dest='compare_time', default=False, help='''
        Compare timestamp on files which are otherwise equal. By default
        difference in file timestamp are ignored.
        ''')
    argp.add_argument('-v', '--verbose', action='count', dest='verbose',
                      default=0, help='''
        Verbose printing during writing to scan output file
        ''')
    argp.add_argument('-x', '--one-file-system', action='store_true',
                      dest='onefs', default=False, help='''
        Don't cross filesystem boundaries
        ''')
    argp.add_argument('-X', '--exclude', metavar='PATH', action='append',
                      dest='exclude', default=[], help='''
        Exclude PATH from scan. PATH is relative to DIR
        ''')
    argp.add_argument('--format-help', action='store_true', dest='formathelp',
                      default=None, help='''
        Show help for --format and --summary-format
        ''')
    argp.add_argument('--prefix', metavar='PATH', dest='prefix', default=None,
                      help='''
        When reading from scanfiles on either sides, use the given prefix PATH
        to read a subsection of the scan file(s).
        ''')
    argp.add_argument('--left-prefix', metavar='PATH', dest='leftprefix',
                      default=None, help='''
        When reading from a scanfile on the left side, use the given prefix PATH
        to read a subsection of the scan file.
        ''')
    argp.add_argument('--right-prefix', metavar='PATH', dest='rightprefix',
                      default=None, help='''
        When reading from a scanfiles on the right side, use the given
        prefix PATH to read a subsection of the scan file.
        ''')
    argp.add_argument('--version', action='version',
                      version='%(prog)s ' + __version__)

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
