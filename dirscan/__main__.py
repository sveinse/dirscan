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

from . import fileinfo
from .scanfile import SCANFILE_FORMAT, readscanfile, quote
from .compare import dir_compare1, dir_compare2
from .dirscan import walkdirs, DirscanException
from .usage import dirscan_argumentparser, DIRSCAN_FORMAT_HELP



def dirscan_main(argv=None):
    ''' Dirscan command-line entry-point '''

    #
    # Input validation and option parsing
    # -----------------------------------
    #

    # -- Get arguments
    if argv is None:
        argv = sys.argv[1:]


    # -- Set command line arguments and get the parser
    ap = dirscan_argumentparser()


    # -- Parsing
    opts = ap.parse_args()
    prog = ap.prog
    left = opts.dir1
    right = opts.dir2


    # -- Requested more help?
    if opts.formathelp:
        ap.print_help()
        print(DIRSCAN_FORMAT_HELP)
        ap.exit(1)


    # -- Not having onesided traversion in scan mode does not print anything
    if right is None:
        opts.traverse_oneside = True


    # -- Enable summary if any summary templates are given
    #if opts.summary:
    #    opts.enable_summary = True


    # -- Missing options
    if not left:
        ap.error("Missing LEFT_DIR argument")
    if opts.right and not right:
        ap.error("Missing RIGHT_DIR argument")


    # -- Read the scan files
    if opts.left:
        left = readscanfile(left)
    if opts.right:
        right = readscanfile(right)


    # -- Determine settings and print format
    if right is None:

        # -- Setting for scanning
        dirs = [left]
        printfmt = '{fullpath}'
        writefmt = None
        comparetypes = 's'
        filetypes = 'fdlbcps'
        prefixes = ['']
        summary = list(fileinfo.SCAN_SUMMARY)
        dir_comparator = dir_compare1

        if opts.outfile:
            writefmt = SCANFILE_FORMAT

        elif opts.all and opts.long:
            if opts.human:
                printfmt = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {mtime}  {type}  {fullpath}'
            else:
                printfmt = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {mtime}  {type}  {fullpath}'

        elif opts.all:
            if opts.human:
                printfmt = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {type}  {fullpath}'
            else:
                printfmt = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {type}  {fullpath}'

        elif opts.long:
            if opts.human:
                printfmt = '{mode_t}  {user:8} {group:8}  {size:>5}  {mtime}  {type}  {fullpath}'
            else:
                printfmt = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {type}  {fullpath}'

    else:

        # -- Setting for comparing
        dirs = [left, right]
        printfmt = '{arrow}  {path}  :  {text}'
        writefmt = None
        comparetypes = 'rltcLR'
        filetypes = 'fdlbcps'
        prefixes = ['l_', 'r_']
        summary = list(fileinfo.COMPARE_SUMMARY)
        dir_comparator = dir_compare2


    # -- The all option will show all compare types
    if opts.all:
        comparetypes = ''.join([
            fileinfo.COMPARE_ARROWS[x][0] for x in fileinfo.COMPARE_ARROWS])


    # -- User provided formats overrides any defaults
    printfmt = opts.format or printfmt
    comparetypes = opts.comparetypes or comparetypes
    filetypes = opts.filetypes or filetypes


    # --- Summary options
    if opts.summary:
        summary = [(True, s) for s in opts.summary]
        opts.enable_summary = True
    if not opts.enable_summary:
        summary = []

    summary.extend(fileinfo.FINAL_SUMMARY)


    # -- Set print strings
    if not opts.outfile:
        if opts.quiet:
            printfmt = None
    else:
        if not opts.verbose:
            printfmt = None


    # -- Get the fields names used in the printing formats
    try:
        fieldnames = set()
        if printfmt:
            fieldnames.update(fileinfo.get_fieldnames(printfmt))
        if writefmt:
            fieldnames.update(fileinfo.get_fieldnames(writefmt))
    except ValueError as err:
        print(ap.prog + ': Print format error: ' + str(err))
        return 1


    # -- Prepare the histograms to collect statistics
    stats = fileinfo.Statistics(opts.dir1, opts.dir2)


    #
    # Directory scanning
    # -------------------
    #

    f = None
    try:

        # -- Open output file
        if opts.outfile:
            f = open(opts.outfile, 'w')


        def error_handler(exception):
            ''' Callback for handling scanning errors during parsing '''
            stats.add('err')
            if not opts.realquiet:
                sys.stderr.write('%s: %s\n' %(prog, exception))
            return True


        # -- TRAVERSE THE DIR(S)
        for (path, objs) in walkdirs(
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
                text = 'Compare failed: ' + str(err)

            # Show this file and compare types?
            show = True
            if not any([o.objtype in filetypes for o in objs]):
                show = False
            if fileinfo.COMPARE_ARROWS[change][0] not in comparetypes:
                show = False

            # Save histogram info for the change type
            stats.add(change)

            # Skip this entry if its not going to be printed
            if not show:
                continue

            # Save file histogram info
            stats.add_filehist(objs)

            # Set the base fields
            fields = {
                'path'  : str(path),
                'change': str(change),
                'arrow' : fileinfo.COMPARE_ARROWS[change][1],
                'text'  : text.capitalize(),
            }

            # Update the fields from the file objects
            (errs, filefields) = fileinfo.get_fields(objs, prefixes, fieldnames)
            fields.update(filefields)

            for err in errs:
                error_handler(err)

            # Print to stdout
            if printfmt:
                fileinfo.write_fileinfo(printfmt, fields)

            # Write to file
            if writefmt:
                fileinfo.write_fileinfo(writefmt, fields, quoter=quote, file=f)


    except DirscanException as err:
        # Handle user-specific errors
        print(ap.prog + ': ' + str(err))
        return 1

    finally:
        # Close any open output file
        if f:
            f.close()


    #
    # Statistics printing
    # -------------------
    #

    # Set the summary fields
    fields = {
        'prog': prog,
    }
    fields.update(stats.get_fields(prefixes))

    # Print the summary
    fileinfo.write_summary(summary, fields, file=sys.stderr)

    # Return error code if we have encountered any errors scanning
    if fields.get('err'):
        return 1

    return 0



if __name__ == '__main__':
    dirscan_main()
