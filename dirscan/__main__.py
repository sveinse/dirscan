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
from .log import set_debug
from .scanfile import SCANFILE_FORMAT, readscanfile, fileheader
from .scanfile import file_quoter, text_quoter
from .compare import dir_compare1, dir_compare2
from .dirscan import walkdirs, DirscanException, DirObj
from .usage import dirscan_argumentparser, DIRSCAN_FORMAT_HELP
from .progress import PrintProgress



# Print formats in scan mode
#     A = --all,  H = --human,  L = --long
FMT_AHL = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {mtime}  {type}  {fullpath}'
FMT_AL = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {mtime}  {type}  {fullpath}'
FMT_AH = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {type}  {fullpath}'
FMT_A = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {type}  {fullpath}'
FMT_HL = '{mode_t}  {user:8} {group:8}  {size:>5}  {mtime}  {type}  {fullpath}'
FMT_L = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {type}  {fullpath}'



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
    argp = dirscan_argumentparser()


    # -- Parsing
    opts = argp.parse_args()
    prog = argp.prog
    left = opts.dir1
    right = opts.dir2
    set_debug(opts.debug)


    # -- Requested more help?
    if opts.formathelp:
        argp.print_help()
        print(DIRSCAN_FORMAT_HELP)
        argp.exit(1)


    # -- Not having onesided traversion in scan mode does not print anything
    if right is None:
        opts.traverse_oneside = True


    # -- Missing options
    if not left:
        argp.error("Missing LEFT_DIR argument")
    if opts.right and not right:
        argp.error("Missing RIGHT_DIR argument")


    # -- Determine settings and print format
    if right is None:

        # -- Setting for scanning
        dirs = [DirObj(left, treeid=0)]
        printfmt = '{fullpath}'
        writefmt = None
        comparetypes = 's'
        filetypes = 'fdlbcps'
        prefixes = ['']
        summary = list(fileinfo.SCAN_SUMMARY)
        dir_comparator = dir_compare1
        name = 'Scanned'

        if opts.outfile:
            writefmt = SCANFILE_FORMAT
        elif opts.all and opts.long:
            printfmt = FMT_AHL if opts.human else FMT_AL
        elif opts.all:
            printfmt = FMT_AH if opts.human else FMT_A
        elif opts.long:
            printfmt = FMT_HL if opts.human else FMT_L

    else:

        # -- Setting for comparing
        dirs = [DirObj(left, treeid=0), DirObj(right, treeid=1)]
        printfmt = '{arrow}  {path}  :  {text}'
        writefmt = None
        comparetypes = 'rltcLR'
        filetypes = 'fdlbcps'
        prefixes = ['l_', 'r_']
        summary = list(fileinfo.COMPARE_SUMMARY)
        dir_comparator = dir_compare2
        name = 'Compared'

        if opts.outfile:
            argp.error("Writing to an outfile is not supported when comparing directories")


    # -- Read the scan files
    if opts.left:
        dirs[0] = readscanfile(left, treeid=0)
    if opts.right:
        dirs[1] = readscanfile(right, treeid=1)


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
        print(prog + ': Print format error: ' + str(err))
        return 1


    # -- Handler for printing progress to stderr
    progress = PrintProgress(file=sys.stderr, delta_ms=200, show_progress=opts.progress)


    # -- Prepare the histograms to collect statistics
    stats = fileinfo.Statistics(left, right)


    # -- Error handler
    def error_handler(exception):
        ''' Callback for handling scanning errors during parsing '''
        stats.add_stats('err')
        if not opts.quieterr:
            progress.print('%s: %s' %(prog, exception))
        # True will swallow the exception
        return True


    #
    # Directory scanning
    # -------------------
    #

    outfile = None
    try:

        # -- Open output file
        if opts.outfile:
            kwargs = {}
            if sys.version_info[0] >= 3:
                kwargs['errors'] = 'surrogateescape'
            outfile = open(opts.outfile, 'w', **kwargs)
            outfile.write(fileheader())

        # Prepare progress values
        count = 0

        # -- TRAVERSE THE DIR(S)
        for (path, objs) in walkdirs(
                dirs,
                reverse=opts.reverse,
                excludes=opts.exclude,
                onefs=opts.onefs,
                traverse_oneside=opts.traverse_oneside,
                exception_fn=error_handler):

            # Progress printing
            count += 1
            cur = objs[0].fullpath if len(objs) == 1 else path
            progress.progress("%s %s files:  %s " %(name, count, cur))

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
            stats.add_stats(change)

            # Skip this entry if its not going to be printed
            if not show:
                continue

            # Save file histogram info
            stats.add_filestats(objs)

            # Set the base fields
            fields = {
                'path'  : path,
                'change': change,
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
                fileinfo.write_fileinfo(printfmt, fields, quoter=text_quoter)

            # Write to file -- don't write if we couldn't get all fields
            if writefmt and not errs:
                fileinfo.write_fileinfo(writefmt, fields, quoter=file_quoter, file=outfile)


    except DirscanException as err:
        # Handle user-specific errors
        print(prog + ': ' + str(err))
        return 1

    finally:
        # Close any open output file
        if outfile:
            outfile.close()

        # Close the progress output
        progress.close()


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
    if fields.get('n_err'):
        return 1

    return 0



if __name__ == '__main__':
    dirscan_main()
