''' Dirscan - command line interface '''
#
# Copyright (C) 2010-2025 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

from __future__ import annotations

from argparse import Namespace
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Collection, Sequence
from typing_extensions import Self  # Due to Python 3.10 compatibility, remove when Python 3.11+ is minimum

import dirscan.formatfields as fmtfields
from dirscan.dirscan import OBJTYPES, DirscanException, DirscanObj, FileObj
from dirscan.digest import TPath
from dirscan.formatfields import (
    Statistics,
    TField,
    TSummary,
    format_shaid,
    get_compare_types,
    get_fieldnames,
    get_fields,
    get_file_types,
    write_fileinfo,
    write_summary,
)
from dirscan.log import debug, set_debug
from dirscan.progress import PrintProgress, setprogress
from dirscan.scanfile import (
    SCANFILE_FORMAT, file_quote, get_fileheader, open_dir_or_scanfile,
    text_quote
)
from dirscan.usage import DIRSCAN_FORMAT_HELP, argument_parser
from dirscan.walkdirs import obj_compare1, obj_compare2, scan_shadb, walkdirs

# Update interval of the progress in ms
UPDATE_DELAY = 300
UPDATE_INTERVAL = 100


@dataclass
class DirscanContext:
    """ Context for dirscan operations. """

    printfmt: str = ''
    """ Print format string. """
    writefmt: str = ''
    """ Write format string. """
    compare_types: str = ''
    """ Compare types specifier. """
    filetypes: str = ''
    """ File types specifier. """
    field_prefix: list[str] = field(default_factory=list)
    """ Prefixes for the fields. Used to separate left/right side fields. """
    enable_summary: bool = False
    """ Whether to enable summary printing. """
    summary: list[TSummary] = field(default_factory=list)
    """ Summary settings. """

    # -- SHA database
    shadb: dict[bytes, list[tuple[int, FileObj]]] = field(default_factory=dict)
    """ SHA database for duplicate detection. """
    shaids: dict[bytes, str] = field(default_factory=dict)
    """ Mapping of SHA sums to short IDs. """
    shaids_used: set[str] = field(default_factory=set)
    """ Set of used short SHA IDs. """
    shavisited: set[bytes] = field(default_factory=set)
    """ Set of visited SHA sums. """

    # -- Flags
    duponce: bool = False
    """ Whether to print duplicates only once. """
    recurse: bool = False
    """ Whether to recurse into subdirectories. """
    sequential: bool = False
    """ Whether to process directories sequentially instead of simultaneously. """
    duplicates: bool = False
    """ Whether in duplicate scanning mode. """

    def setup_for_scanning(self, opts: Namespace) -> None:
        """ Setup the context for scanning mode. """
        self.printfmt = fmtfields.FMT_DEF
        self.writefmt = ''
        self.compare_types = fmtfields.COMPARE_TYPES_DEFAULT_SCAN
        self.filetypes = fmtfields.FILE_TYPES_DEFAULT_SCAN
        self.field_prefix = ['']
        self.summary = list(fmtfields.SCAN_SUMMARY)
        self.enable_summary = opts.enable_summary
        self.duplicates = opts.duplicates
        self.sequential = True
        self.recurse = True

        if opts.outfile:
            self.writefmt = SCANFILE_FORMAT
            if not opts.verbose:
                self.printfmt = ''
        else:
            if opts.quiet:
                self.printfmt = ''
            elif opts.all and opts.long:
                self.printfmt = fmtfields.FMT_AHL if opts.human else fmtfields.FMT_AL
            elif opts.all:
                self.printfmt = fmtfields.FMT_AH if opts.human else fmtfields.FMT_A
            elif opts.long:
                self.printfmt = fmtfields.FMT_HL if opts.human else fmtfields.FMT_L
            elif opts.verbose:
                self.printfmt = '{path}'
            elif opts.duplicates:
                self.compare_types = 'd'
                self.duponce = not bool(opts.format)
                self.printfmt = '{dupinfo}'

        if opts.duplicates:
            self.filetypes = 'f'
            # Sneaky way to add DUP to printings
            self.printfmt = self.printfmt.replace('{path}', '{dup}  {dupid}  {path}')

    def setup_for_comparing(self, opts: Namespace) -> None:
        """ Setup the context for compare mode. """
        self.printfmt = fmtfields.FMT_COMP_DEF
        self.writefmt = ''
        self.compare_types = fmtfields.COMPARE_TYPES_DEFAULT_COMPARE
        self.filetypes = fmtfields.FILE_TYPES_DEFAULT_COMPARE
        self.field_prefix = ['l_', 'r_']
        self.summary = list(fmtfields.COMPARE_SUMMARY)
        self.enable_summary = opts.enable_summary
        self.duplicates = opts.duplicates
        self.sequential = False
        self.recurse = opts.recurse

        if opts.quiet:
            self.printfmt = ''

        # The all or verbose option will show all compare types
        if opts.all or opts.verbose:
            self.compare_types = ''.join(x[0] for x in fmtfields.COMPARE_ARROWS.values())

        if opts.shadiff:
            # Want to walk the entire tree on both sides to find any
            # duplicates
            self.recurse = True

    def setup(self, scan_mode: bool, opts: Namespace) -> Self:
        """ Setup the printing formats. """

        # -- Initialize according to mode
        if scan_mode:
            self.setup_for_scanning(opts)
        else:
            self.setup_for_comparing(opts)

        # -- User provided formats overrides any defaults
        self.printfmt = opts.format or self.printfmt
        self.compare_types = get_compare_types(opts.compare_types, self.compare_types)
        self.filetypes = get_file_types(opts.filetypes, self.filetypes)

        # Unless compare_types contains these compares, there isn't any need to
        # make any detailed comparisons.
        self.no_compare = not bool(set('cLRe').intersection(self.compare_types))

        # -- Extra verbose
        if opts.verbose > 1:
            # Prefix fields
            self.printfmt = '{change_t}  ' + self.printfmt

        # -- Summary options
        if opts.summary:
            self.summary = [(True, s) for s in opts.summary]
            self.enable_summary = True
        if not self.enable_summary:
            self.summary = []

        # The final summary contains any notes if there are any errors
        self.summary.extend(fmtfields.FINAL_SUMMARY)

        # -- Get the fields names used in the printing formats.
        self.fieldnames = set()
        if self.printfmt:
            self.fieldnames.update(get_fieldnames(self.printfmt))
        if self.writefmt:
            self.fieldnames.update(get_fieldnames(self.writefmt))

        # FIXME: Evaluate valid format fields in summary, printfmt and writefmt

        return self


def main(argv: Sequence[str] | None=None) -> int:
    '''
    Entry-point for command-line and ``-mdirscan`` usage.

    Args:
        argv: Optional list of arguments. If omitted, ``sys.argv`` will be
            used.

    Returns:
        Error code of the operation, where 0 indicates success
    '''

    #
    # Input validation and option parsing
    # -----------------------------------

    # -- Get arguments, set command line arguments and parse arguments
    if argv is None:
        argv = sys.argv[1:]
    argp = argument_parser()
    opts = argp.parse_args(args=argv)
    set_debug(opts.debug)

    # -- Requested more help?
    if opts.formathelp:
        argp.print_help()
        print(DIRSCAN_FORMAT_HELP)
        argp.exit(1)

    # -- Ensure we have the minimum required number of arguments
    left: str | None = opts.dir1
    right: str | None = opts.dir2
    if left is None:
        argp.error("Missing required LEFT_DIR argument")

    # -- Determine settings and print format
    if right is None or opts.duplicates:
        # -- Settings for scanning
        scan_mode = True
        dir_comparator = obj_compare1
        pr_prefix = 'Scanned'

        if opts.shadiff:
            argp.error("--sha doesn't work when scanning")

    else:
        # -- Settings for comparing
        scan_mode = False
        dir_comparator = obj_compare2
        pr_prefix = 'Compared'

        if opts.outfile:
            argp.error("Writing to an outfile is not supported "
                       "when comparing directories")

    # -- Setup the context
    try:
        ctx = DirscanContext().setup(scan_mode, opts)
    except ValueError as err:
        argp.error(str(err))

    # -- Verify file types
    if ctx.duplicates and ctx.filetypes != 'f':
        argp.error("Cannot use other filetypes than 'f' in --duplicates mode")

    # -- Printing settings
    end = '\x00' if opts.print0 else '\n'

    # Ensure printability in powershell (that won't encode surrogates).
    # surrogatepass?
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(errors='backslashreplace')
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(errors='backslashreplace')

    # -- Debug info --
    debug(1, "Command options:")
    debug(1, "  Left          : '{}'", left)
    debug(1, "  Right         : '{}'", right)
    debug(1, "  Print format  : '{}'", ctx.printfmt)
    debug(1, "  Write format  : '{}'", ctx.writefmt)
    debug(1, "  Fields in use : {}", ctx.fieldnames)
    debug(1, "  Compare types : '{}'", ctx.compare_types)
    debug(1, "                : ({})", ", ".join(fmtfields.COMPARE_TYPES[c] for c in ctx.compare_types))
    debug(1, "  File types    : '{}'", ctx.filetypes)
    debug(1, "                : ({})", ", ".join(OBJTYPES[o].objname for o in ctx.filetypes))
    for i, s in enumerate(ctx.summary, start=1):
        debug(1, "  Summary {:2d}    : '{}'", i, s)
    debug(1, "  Opts          : {}", opts)
    debug(1, "")

    # -- Handler for printing progress to stderr
    #    Set the global scope to allow inner functions to report progress
    progressmgr = PrintProgress(file=sys.stderr,
                                update_interval=UPDATE_INTERVAL,
                                update_delay=UPDATE_DELAY,
                                show_progress=opts.progress)
    progressmgr.__enter__()
    setprogress(progressmgr)

    # -- Prepare the histograms to collect statistics
    stats = Statistics(left, right)

    # -- Error handler
    def error_handler(exception: Exception, path: DirscanObj | TPath) -> bool:
        ''' Callback for handling scanning errors during parsing '''
        stats.add_stats('err')
        if not opts.quieterr:
            if isinstance(path, DirscanObj):
                path = path.fullpath
            progressmgr.print(f"{path}: {exception.__class__.__qualname__}: {exception}")

        # True will swallow the exception. In debug mode
        # the error will be raised
        return not opts.debug

    #
    # Directory scanning
    # -------------------

    outfile = None
    try:
        dirs: Collection[DirscanObj]

        # -- Check and read the scan files
        if right is None:
            dirs = [open_dir_or_scanfile(left,
                                         subdir=opts.leftsubdir or opts.subdir,
                                         prefix=opts.prefix)]
        else:
            dirs = [open_dir_or_scanfile(left,
                                         subdir=opts.leftsubdir or opts.subdir,
                                         prefix=opts.prefix),
                    open_dir_or_scanfile(right,
                                         subdir=opts.rightsubdir or opts.subdir,
                                         prefix=opts.prefix)]

        # -- Scan the database
        if ctx.duplicates or opts.shadiff:
            progressmgr.print("Building SHA database...")

            # -- Build the sha database
            ctx.shadb = scan_shadb(
                dirs,
                include_single_entries=not ctx.duplicates,
                reverse=opts.reverse,
                excludes=opts.exclude,
                onefs=opts.onefs,
                exception_fn=error_handler,
            )

        # -- First pass
        obj_count = -1
        if opts.twopass:
            progressmgr.print("Pass 1...")

            with progressmgr.progress(
                prefix=f"{pr_prefix} {{count}} files:  ",
                format="{text}",
            ) as progress:

                # -- Do the first pass to count the number of objects
                for (path, objs) in walkdirs(
                        dirs,
                        reverse=opts.reverse,
                        excludes=opts.exclude,
                        onefs=opts.onefs,
                        traverse_into_oneside=ctx.recurse,
                        exception_fn=error_handler,
                        close_during=False,
                        sequential=True,
                    ):

                    # Progress printing
                    progress.update(text=str(objs[0].fullpath if len(objs) == 1 else path))

                obj_count = progress.count
                ctx.sequential = False

        # -- Open output file
        if opts.outfile:
            outfile = open(opts.outfile, 'w', encoding='utf-8',
                           errors='surrogateescape')
            outfile.write(get_fileheader())

        # -- Setup progress printing context
        with progressmgr.progress(
            prefix=f"{pr_prefix} {{count}} files:  " if obj_count < 0 else f"{pr_prefix} {{count}} / {{total_count}} files:  ",
            total_count=obj_count,
            format="{text}",
        ) as progress:

            if opts.twopass:
                progressmgr.print("Pass 2...")

            # -- TRAVERSE THE DIR(S)
            for (path, objs) in walkdirs(
                    dirs,
                    reverse=opts.reverse,
                    excludes=opts.exclude,
                    onefs=opts.onefs,
                    traverse_into_oneside=ctx.recurse,
                    exception_fn=error_handler,
                    close_during=False,
                    sequential=ctx.sequential,
            ):

                # Progress printing
                progress.update(text=str(objs[0].fullpath if len(objs) == 1 else path))

                # Compare the objects
                try:
                    change = dir_comparator(
                        objs,
                        ignores=opts.ignore,
                        no_compare=ctx.no_compare,
                        ignore_time=not opts.compare_time,
                        shadb=ctx.shadb,
                    )

                except OSError as err:
                    # Errors here are due to comparisons that fail.
                    if not error_handler(err, path):
                        raise
                    change = ('error', 'Compare failed: ' + str(err))

                debug(3, "      Compare: {} {}", change[0], change[1])

                # -- PROCESS THE COMPARE

                # Save histogram info for the change type
                stats.add_stats(change[0])

                # Determine whether to show the entry
                show = show_entry(objs, change, ctx)
                if not show:
                    debug(3, "      hidden")
                    continue

                # Save file histogram info
                stats.add_filestats(objs)

                # Generate the fields for printing and log any errors from it
                fields, errors = generate_fields(path, objs, change, ctx)
                for error in errors:
                    if not error_handler(error, path):
                        raise error

                # Print to stdout
                if ctx.printfmt:
                    write_fileinfo(ctx.printfmt, fields, quoter=text_quote,
                                   file=sys.stdout, end=end)

                # Write to file -- don't write if we couldn't get all fields
                if outfile and ctx.writefmt and not errors:
                    write_fileinfo(ctx.writefmt, fields, quoter=file_quote,
                                   file=outfile)

    except (DirscanException, OSError) as err:
        # Handle user-specific errors
        progressmgr.print(argp.prog + ': ' + str(err))

        # Show the full traceback in debug mode
        if opts.debug:
            raise

        return 1

    finally:
        # Close the statistics
        stats.set_end_time()

        # Close any open output file
        if outfile:
            outfile.close()

        # Exit the progress manager context
        progressmgr.__exit__(None, None, None)

    #
    # Statistics printing
    # -------------------

    # Set the summary fields
    summary_fields: dict[str, TField] = {
        'prog': argp.prog,
        **stats.get_fields(ctx.field_prefix),
    }

    # Print the summary
    write_summary(ctx.summary, summary_fields, file=sys.stderr)

    # Return error code if we have encountered any errors scanning
    return 1 if summary_fields.get('n_err') else 0


def show_entry(objs: tuple[DirscanObj, ...], change: tuple[str, str], ctx: DirscanContext) -> bool:
    """ Determine whether to show the entry. """

    # Show this filetype?
    if not any(o.objtype in ctx.filetypes for o in objs):
        return False

    # Show this compare type?
    if fmtfields.COMPARE_ARROWS[change[0]][0] not in ctx.compare_types:
        return False

    return True


def generate_fields(path: Path, objs: tuple[DirscanObj, ...],
                    change: tuple[str, str], ctx: DirscanContext) -> tuple[dict[str, TField], list[Exception]]:
    """ Assemble the fields for printing from comparison results. """

    # Set the base fields
    fields: dict[str, TField] = {
        'relpath': str(path),
        'relpath_p': str(PurePosixPath(path)),  # Posix formatted path
        'change': change[0],
        'change_t': fmtfields.COMPARE_ARROWS[change[0]][0],
        'arrow' : fmtfields.COMPARE_ARROWS[change[0]][1],
        'text'  : change[1].capitalize(),
    }

    # Write list of duplicates to the extra field
    if ctx.duplicates:
        fields.update({
            'dupinfo': '',
            'dup': '   ',
            'dupid': '      ',
            'dupcount': 0,
        })

        # Technically not needed, due to sequential setting ensures it
        # will only contain one directory. Probably smart to keep this
        # as a safeguard. Same applies to the FileObj test.
        for obj in objs:
            if not isinstance(obj, FileObj):
                continue
            sha = obj.hashsum_cache  # Don't force calculation here
            if not sha:
                continue

            visited = sha in ctx.shavisited
            if not visited:
                ctx.shavisited.add(sha)

            # Skip if the duplicated entry has already been printed
            if ctx.duponce and visited:
                continue

            samesha = ctx.shadb.get(sha, [])
            len_samesha = len(samesha)
            fields['dupcount'] = len_samesha
            if len_samesha > 1:
                shaid = format_shaid(sha, ctx.shaids, ctx.shaids_used)
                fields['dupid'] = shaid
                j = '\n    '.join([str(o[1].fullpath) for o in samesha])
                fields['dupinfo'] = (
                    f'File duplicated {len_samesha} times:  '
                    f'(ID {shaid})  {obj.size} bytes\n    {j}\n')
                fields['dup'] = 'DUP'

    # Update the fields from the file objects. This retries the values
    # for the fields which are in actual use. This saves a lot of
    # resources instead of fetching everything
    (errors, filefields) = get_fields(objs, ctx.field_prefix, ctx.fieldnames)
    fields.update(filefields)

    return fields, errors


if __name__ == '__main__':
    main()
