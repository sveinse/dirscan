'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2022 Svein Seldal
This code is licensed under MIT license (see LICENSE for details)
URL: https://github.com/sveinse/dirscan
'''
from typing import Dict, List, Tuple
from pathlib import PurePosixPath
import sys

import dirscan.formatfields as fmtfields
from dirscan.log import set_debug, debug
from dirscan.scanfile import read_scanfile, get_fileheader, is_scanfile
from dirscan.scanfile import file_quote, text_quote, SCANFILE_FORMAT
from dirscan.compare import dir_compare1, dir_compare2
from dirscan.dirscan import walkdirs, create_from_fs, DirscanException, DirscanObj, FileObj
from dirscan.usage import argument_parser, DIRSCAN_FORMAT_HELP
from dirscan.progress import PrintProgress


# Update interval of the progress in ms
UPDATE_INTERVAL = 300


def scan_shadb(dirs, reverse=False, excludes=None, onefs=False,
               exception_fn=None, progress=None):
    """ Build a sha database for a scanned tree """

    # -- Build the sha database
    shadb: Dict[bytes, List[Tuple[int, DirscanObj]]] = {}

    # Prepare progress values
    count = 0

    for i, sdir in enumerate(dirs):
        for (path, objs) in walkdirs(
                [sdir],
                reverse=reverse,
                excludes=excludes,
                onefs=onefs,
                exception_fn=exception_fn,
                close_during=False):

            # Progress printing
            count += 1
            if progress:
                progress.progress("Scanning %s files:  %s " %(count, objs[0].fullpath))

            # Evaluate the hashsum for each of the objects and store in
            # sha database
            for obj in objs:
                if not isinstance(obj, FileObj) or obj.excluded:
                    continue

                try:
                    # Get the hashsum and store it to the shadb list
                    shadb.setdefault(obj.hashsum, []).append((i, obj))
                except IOError as err:
                    if not exception_fn or not exception_fn(err):
                        raise

    return shadb


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

    # -- Determine settings and print format
    duponce = False
    if right is None or opts.duplicates:
        # -- Settings for scanning
        printfmt = fmtfields.FMT_DEF
        writefmt = None
        comparetypes = fmtfields.COMPARE_TYPES_DEFAULT_SCAN
        filetypes = fmtfields.FILE_TYPES_DEFAULT_SCAN
        field_prefix = ['']
        summary = list(fmtfields.SCAN_SUMMARY)
        dir_comparator = dir_compare1
        pr_prefix = 'Scanned'
        sequential = True

        # Must recurse in scan mode
        opts.recurse = True

        if opts.outfile:
            writefmt = SCANFILE_FORMAT
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
                printfmt = '{path}'
            elif opts.duplicates:
                comparetypes = 'd'
                duponce = not bool(opts.format)
                printfmt = '{dupinfo}'

        if opts.duplicates:
            filetypes = 'f'
            # Sneaky way to add DUP to printings
            printfmt = printfmt.replace('{path}', '{dup}  {path}')

            if opts.shadiff:
                argp.error("--sha doesn't work with --duplicates")

        if opts.shadiff:
            argp.error("--sha doesn't work when scanning")

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
        sequential = False

        if opts.outfile:
            argp.error("Writing to an outfile is not supported when comparing directories")
        if opts.quiet:
            printfmt = None

        # The all or verbose option will show all compare types
        if opts.all or opts.verbose:
            comparetypes = ''.join(x[0] for x in fmtfields.COMPARE_ARROWS.values())

        if opts.shadiff:
            # Want to walk the entire tree on both sides to find any
            # duplicates
            opts.traverse_oneside = True

    # -- Scanfile prefix settings
    opts.leftprefix = opts.leftprefix or opts.prefix
    opts.rightprefix = opts.rightprefix or opts.prefix

    # -- User provided formats overrides any defaults
    try:
        printfmt = opts.format or printfmt
        comparetypes = fmtfields.get_compare_types(opts.comparetypes, comparetypes)
        filetypes = fmtfields.get_file_types(opts.filetypes, filetypes)
    except ValueError as err:
        argp.error(err)

    # -- Extra verbose
    if opts.verbose > 1:
        # Prefix fields
        printfmt = '{change_t}  ' + printfmt

    # -- Verify file types
    if opts.duplicates and filetypes != 'f':
        argp.error("Cannot use other filetypes than 'f' in --duplicates mode")

    # -- Summary options
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

    # -- Debug info --
    debug(1, "Command options:")
    debug(1, "  Left          : '{}'", left)
    debug(1, "  Right         : '{}'", right)
    debug(1, "  Print format  : '{}'", printfmt)
    debug(1, "  Write format  : '{}'", writefmt)
    debug(1, "  Fields in use : {}", fieldnames)
    debug(1, "  Compare types : '{}'", comparetypes)
    debug(1, "  File types    : '{}'", filetypes)
    for i, s in enumerate(summary, start=1):
        debug(1, "  Summary {:2d}    : '{}'", i, s)
    debug(1, "  Opts          : {}", opts)
    debug(1, "")

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

    # The filter must return True to show the line
    show_filter = lambda obj: True

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

        # -- Scan the database
        shadb = {}
        shavisited = set()
        if opts.duplicates or opts.shadiff:

            # -- Build the sha database
            shadb = scan_shadb(
                dirs,
                reverse=opts.reverse,
                excludes=opts.exclude,
                onefs=opts.onefs,
                exception_fn=error_handler,
                progress=progress
            )

        # -- Open output file
        if opts.outfile:
            outfile = open(opts.outfile, 'w', encoding='utf-8', errors='surrogateescape')  # pylint: disable=consider-using-with
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
                sequential=sequential,
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
                    shadb=shadb,
                )

            except OSError as err:
                # Errors here are due to comparisons that fail.
                error_handler(err)
                change = 'error'
                text = 'Compare failed: ' + str(err)

            debug(3, "      Compare: {} {}", change, text)

            # Going to show this entry?
            show = show_filter(objs)

            # Show this filetype?
            if not any(o.objtype in filetypes for o in objs):
                show = False

            # Show this compare type?
            if fmtfields.COMPARE_ARROWS[change][0] not in comparetypes:
                show = False

            # Save histogram info for the change type
            stats.add_stats(change)

            # Skip this entry if its not going to be printed
            if not show:
                debug(3, "     hidden")
                continue

            # Save file histogram info
            stats.add_filestats(objs)

            # Set the base fields
            fields = {
                'relpath': str(path),
                'relpath_p': str(PurePosixPath(path)),  # Posix formatted path
                'change': change,
                'change_t': fmtfields.COMPARE_ARROWS[change][0],
                'arrow' : fmtfields.COMPARE_ARROWS[change][1],
                'text'  : text.capitalize(),
            }

            # Write list of duplicates to the extra field
            if opts.duplicates: # and right is None:
                fields['dupinfo'] = ''
                fields['dup'] = '   '
                fields['dupcount'] = 0

                # Technically not needed, due to sequential setting ensures it
                # will only contain one directory. Probably smart to keep this
                # as a safeguard. Same applies to the FileObj test.
                for obj in objs:
                    if not isinstance(obj, FileObj):
                        continue
                    sha = obj.hashsum

                    # Skip if the duplicated entry has already been printed
                    if duponce and sha in shavisited:
                        continue

                    shavisited.add(sha)
                    compares = [str(o[1].fullpath) for o in shadb[sha]]
                    fields['dupcount'] = len(compares)
                    if len(compares) > 1:
                        fields['dupinfo'] = f'File duplicated {len(compares)} times:\n    ' + \
                            '\n    '.join(compares) + '\n'
                        fields['dup'] = 'DUP'

            # Update the fields from the file objects. This retries the values
            # for the fields which are in actual use. This saves a lot of
            # resources instead of fetching everything
            (errors, filefields) = fmtfields.get_fields(objs, field_prefix, fieldnames)
            fields.update(filefields)
            for error in errors:
                error_handler(error)

            # Print to stdout
            if printfmt:
                fmtfields.write_fileinfo(printfmt, fields, quoter=text_quote,
                                         file=sys.stdout, end=end)

            # Write to file -- don't write if we couldn't get all fields
            if writefmt and not errors:
                fmtfields.write_fileinfo(writefmt, fields, quoter=file_quote,
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
