'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2021 Svein Seldal, sveinse@seldal.com
URL: https://github.com/sveinse/dirscan

This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.
'''
import sys

import dirscan.formatfields as fmtfields
from dirscan.log import set_debug, debug
from dirscan.scanfile import ScanfileRecord, read_scanfile, get_fileheader, is_scanfile
from dirscan.scanfile import file_quoter, text_quoter
from dirscan.compare import dir_compare1, dir_compare2
from dirscan.dirscan import walkdirs, create_from_fs, DirscanException
from dirscan.usage import argument_parser, DIRSCAN_FORMAT_HELP
from dirscan.progress import PrintProgress


# Update interval of the progress in ms
UPDATE_INTERVAL = 300




def main(argv=None):
    ''' Dirscan command-line entry-point '''

    #
    # Input validation and option parsing
    # -----------------------------------
    #

    # -- Get arguments
    if argv is None:
        argv = sys.argv[1:]

    # -- Set command line arguments and get the parser
    argp = argument_parser()

    # -- Parsing
    opts = argp.parse_args(args=argv)
    prog = argp.prog
    left = opts.dir1
    right = opts.dir2
    set_debug(opts.debug)
    end = '\x00' if opts.print0 else '\n'

    # -- Requested more help?
    if opts.formathelp:
        argp.print_help()
        print(DIRSCAN_FORMAT_HELP)
        argp.exit(1)

    # -- Ensure we have the minimum required number of arguments
    if left is None:
        argp.error("Missing required LEFT_DIR argument")

    # -- Argument options parsing
    try:
        opts.comparetypes = fmtfields.get_compare_types(opts.comparetypes)
        opts.filetypes = fmtfields.get_file_types(opts.filetypes)
    except ValueError as err:
        argp.error(err)

    # -- Must recurse in scan mode
    if right is None:
        opts.recurse = True

    # -- Determine settings and print format
    if right is None:
        # -- Settings for scanning
        printfmt = fmtfields.FMT_DEF
        writefmt = None
        comparetypes = fmtfields.COMPARE_TYPES_DEFAULT_SCAN
        filetypes = fmtfields.FILE_TYPES_DEFAULT_SCAN
        field_prefix = ['']
        summary = list(fmtfields.SCAN_SUMMARY)
        dir_comparator = dir_compare1
        pr_prefix = 'Scanned'

        if opts.outfile:
            writefmt = ScanfileRecord.FORMAT
            if not opts.verbose:
                printfmt = None
        else:
            if opts.quiet:
                printfmt = None
            elif opts.all and opts.long:
                printfmt = fmtfields.FMT_AHL if opts.human else fmtfields.FMT_AL
            elif opts.all:
                printfmt = fmtfields.FMT_AH if opts.human else fmtfields.FMT_A
            elif opts.long:
                printfmt = fmtfields.FMT_HL if opts.human else fmtfields.FMT_L
            elif opts.verbose:
                printfmt = '{path}{extra}'

    else:
        # -- Settings for comparing
        printfmt = fmtfields.FMT_COMP_DEF
        writefmt = None
        comparetypes = fmtfields.COMPARE_TYPES_DEFAULT_COMPARE
        filetypes = fmtfields.FILE_TYPES_DEFAULT_COMPARE
        field_prefix = ['l_', 'r_']
        summary = list(fmtfields.COMPARE_SUMMARY)
        dir_comparator = dir_compare2
        pr_prefix = 'Compared'

        if opts.outfile:
            argp.error("Writing to an outfile is not supported when comparing directories")
        if opts.quiet:
            printfmt = None

        # The all or verbose option will show all compare types
        if opts.all or opts.verbose:
            comparetypes = ''.join(x[0] for x in fmtfields.COMPARE_ARROWS.values())

    # -- Scanfile prefix settings
    opts.leftprefix = opts.leftprefix or opts.prefix
    opts.rightprefix = opts.rightprefix or opts.prefix

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

    # The final summary contains any notes if there are any errors
    summary.extend(fmtfields.FINAL_SUMMARY)

    # -- Get the fields names used in the printing formats.
    try:
        fieldnames = set()
        if printfmt:
            fieldnames.update(fmtfields.get_fieldnames(printfmt))
        if writefmt:
            fieldnames.update(fmtfields.get_fieldnames(writefmt))

        # FIXME: Evaluate valid format fields in summary, printfmt and writefmt
    except ValueError as err:
        argp.error(f'Print format {err}')

    # -- Handler for printing progress to stderr
    progress = PrintProgress(file=sys.stderr, delta_ms=UPDATE_INTERVAL,
                             show_progress=opts.progress)

    # -- Prepare the histograms to collect statistics
    stats = fmtfields.Statistics(left, right)

    # -- Error handler
    def error_handler(exception):
        ''' Callback for handling scanning errors during parsing '''
        stats.add_stats('err')
        if not opts.quieterr:
            progress.print(f"{prog}: {exception}")

        # True will swallow the exception. In debug mode the error will be raised
        return not opts.debug

    #
    # Directory scanning
    # -------------------
    #

    #hide_unselected = False
    outfile = None
    try:

        # -- Check and read the scan files
        dirs = [None] if right is None else [None, None]

        if is_scanfile(left):
            dirs[0] = read_scanfile(left, root=opts.leftprefix)
        else:
            dirs[0] = create_from_fs(left)

        if right is not None:
            if is_scanfile(right):
                dirs[1] = read_scanfile(right, root=opts.rightprefix)
            else:
                dirs[1] = create_from_fs(right)

        # -- Open output file
        if opts.outfile:
            outfile = open(opts.outfile, 'w', errors='surrogateescape')  # pylint: disable=consider-using-with
            outfile.write(get_fileheader())

        # Prepare progress values
        count = 0

        # -- TRAVERSE THE DIR(S)
        for (path, objs) in walkdirs(
                dirs,
                reverse=opts.reverse,
                excludes=opts.exclude,
                onefs=opts.onefs,
                traverse_oneside=opts.recurse,
                exception_fn=error_handler,
                close_during=False,
            ):


            # Progress printing
            count += 1
            cur = objs[0].fullpath if len(objs) == 1 else path
            progress.progress(f"{pr_prefix} {count} files:  {cur} ")

            # Compare the objects
            try:
                (change, text) = dir_comparator(
                    objs,
                    ignores=opts.ignore,
                    comparetypes=comparetypes,
                    compare_time=opts.compare_time,
                )

            except OSError as err:
                # Errors here are due to comparisons that fail.
                error_handler(err)
                change = 'error'
                text = 'Compare failed: ' + str(err)

            show = True

            # Show this filetype?
            if not any(o.objtype in filetypes for o in objs):
                show = False

            # Show this compare type?
            if fmtfields.COMPARE_ARROWS[change][0] not in comparetypes:
                show = False

            # Is none selected?
            #if hide_unselected and not any(o.selected for o in objs):
            #    show = False

            # Save histogram info for the change type
            stats.add_stats(change)

            # Skip this entry if its not going to be printed
            if not show:
                continue

            # Save file histogram info
            stats.add_filestats(objs)

            # Set the base fields
            fields = {
                'relpath': path,
                'change': change,
                'arrow' : fmtfields.COMPARE_ARROWS[change][1],
                'text'  : text.capitalize(),
                'extra' : '',
            }

            # Update the fields from the file objects. This retries the values
            # for the fields which are in actual use. This saves a lot of
            # resources instead of fetching everything
            (errors, filefields) = fmtfields.get_fields(objs, field_prefix, fieldnames)
            fields.update(filefields)
            for error in errors:
                error_handler(error)

            # Print to stdout
            if printfmt:
                fmtfields.write_fileinfo(printfmt, fields, quoter=text_quoter,
                                        file=sys.stdout, end=end)

            # Write to file -- don't write if we couldn't get all fields
            if writefmt and not errors:
                fmtfields.write_fileinfo(writefmt, fields, quoter=file_quoter,
                                        file=outfile)

    except (DirscanException, OSError) as err:
        # Handle user-specific errors
        print(prog + ': ' + str(err))

        # Show the full traceback in debug mode
        if opts.debug:
            raise

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
    fields.update(stats.get_fields(field_prefix))

    # Print the summary
    fmtfields.write_summary(summary, fields, file=sys.stderr)

    # Return error code if we have encountered any errors scanning
    if fields.get('n_err'):
        return 1

    return 0


if __name__ == '__main__':
    main()
