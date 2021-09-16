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
import stat
import string
import pwd
import grp


# Print formats in scan mode
#     A = --all,  H = --human,  L = --long
FMT_DEF = '{path}'
FMT_AHL = '{mode_h}  {user:8} {group:8}  {size:>5}  {data:>64}  {mtime_h}  {type}  {path}'
FMT_AL = '{mode_h}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {mtime_h}  {type}  {path}'
FMT_AH = '{mode_h}  {user:8} {group:8}  {size_h:>5}  {data:>64}  {type}  {path}'
FMT_A = '{mode_h}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {type}  {path}'
FMT_HL = '{mode_h}  {user:8} {group:8}  {size_h:>5}  {mtime_h}  {type}  {path}'
FMT_L = '{mode_h}  {uid:5} {gid:5}  {size:>10}  {mtime_h}  {path}'

# Print formats in compare mode
FMT_COMP_DEF = '{arrow}  {relpath}  :  {text}'

# All compare types
COMPARE_TYPES_ALL = 'elrcLRtEx'
COMPARE_TYPES_DEFAULT_SCAN = 's'
COMPARE_TYPES_DEFAULT_COMPARE = 'rltcLR'

# All file types
FILE_TYPES_ALL = 'fdlbcps'
FILE_TYPES_DEFAULT_SCAN = FILE_TYPES_ALL
FILE_TYPES_DEFAULT_COMPARE = FILE_TYPES_ALL


#
# LIST OF FORMAT FIELDS
# =====================
#
FILE_FIELDS = {

    # (bare) filename
    'name': lambda o: o.name,

    # The full file path
    'path': lambda o: o.fullpath,

    # User
    'user': lambda o: pwd.getpwuid(o.uid).pw_name,
    'uid': lambda o: o.uid,

    # Group
    'group': lambda o: grp.getgrgid(o.gid).gr_name,
    'gid': lambda o: o.gid,

    # Mode
    'mode': lambda o: o.mode,
    'mode_h': lambda o: stat.filemode(o.mode|o.objmode),

    # The object type, f=file, d=dir, l=symlink
    'type': lambda o: o.objtype,

    # The object size
    'size': lambda o: o.size,
    'size_h': lambda o: format_bytes(o.size, short=True),

    # Modification time
    'mtime_h': lambda o: o.mtime.strftime("%Y-%m-%d %H:%M:%S"),
    'mtime_f': lambda o: o.mtime.timestamp(),
    'mtime_x': lambda o: f"{int(o.mtime.timestamp()):x}",

    # Special data-payload of the file. For files: the hashsum, links: the link destination
    'data': lambda o: format_data(o),  # pylint: disable=unnecessary-lambda

    # The device node which the file resides
    'dev': lambda o: o.dev,
}


COMPARE_ARROWS = {
    # Change type    : ( filter, arrow )
    'error'          : ('E', 'ERROR'),
    'excluded'       : ('x', '    x'),
    'right_only'     : ('r', '   >>'),
    'left_only'      : ('l', '<<   '),
    'different_type' : ('t', '<~T~>'),
    'changed'        : ('c', '<--->'),
    'left_newer'     : ('L', '<<-->'),
    'right_newer'    : ('R', '<-->>'),
    'equal'          : ('e', '     '),
    'scan'           : ('s', '     '),
    'skipped'        : ('i', '    -'),
}


SCAN_SUMMARY = (
    # Condition,         Line to print
    (True,               "\nSummary of '{dir}':"),
    ('n_files',          "    {n_files}  files, total {sum_bytes_t}"),
    ('n_dirs',           "    {n_dirs}  directories"),
    ('n_symlinks',       "    {n_symlinks}  symbolic links"),
    ('n_special',        "    {n_special}  special files  "
                                "({n_blkdev} block devices, "
                                "{n_chrdev} char devices, "
                                "{n_fifos} fifos, "
                                "{n_sockets} sockets)"),
    ('n_exclude',        "    {n_exclude}  excluded files or directories"),
    (True,               "In total {n_objects} file objects"),
)


COMPARE_SUMMARY = (
    # Condition,         Line to print
    (True,               "\nSummary of compare between left '{left}' and right '{right}':"),
    ('n_equal',          "    {n_equal}  equal files or directories"),
    ('n_changed',        "    {n_changed}  changed files or directories"),
    ('n_different_type', "    {n_different_type}  files of same name but different type"),
    ('n_left_only',      "    {n_left_only}  files or directories only in left '{left}'"),
    ('n_right_only',     "    {n_right_only}  files or directories only in right '{right}'"),
    ('n_left_newer',     "    {n_left_newer}  newer files in left '{left}'"),
    ('n_right_newer',    "    {n_right_newer}  newer files in right '{right}'"),
    ('n_scan',           "    {n_scan}  scanned objects in '{left}'"),
    ('n_excludes',       "    {n_excludes}  excluded files or directories"),
    ('n_errors',         "    {n_errors}  compare errors"),
    ('n_skipped',        "    {n_skipped}  skipped comparisons"),
    (True,               "In total {n_objects} file objects"),
)


FINAL_SUMMARY = (
    # Condition,         Line to print
    ('n_err',            "\n{prog}: **** {n_err} files or directories could not be read"),
)


# Error contents
ERROR_FIELD = '**-ERROR-**'


def split_number(number):
    ''' Split a number into groups of 3 chars. E.g "1234776" will be
        returned as "1 234 776".
    '''
    text = str(number)
    group = []
    # Traverse the string in reverse and insert a space foreach 3rd group
    for i in range(-1, -len(text)-1, -1):
        group.append(text[i])
        if i % 3 == 0:
            group.append(' ')
    group.reverse()
    return ''.join(group).lstrip()


def format_bytes(size, print_full=False, short=False):
    ''' Return a string with a human printable representation of a
        (file) size.  The print_full option will append "(26 552 946
        485 bytes)" to the string.  E.g. format_bytes(26552946485)
        will return "24.74 GiB"
    '''

    # Make exceptions for low values
    if size is None:
        return None

    if size < 10000:
        sizestr = str(size)

    else:
        # kb_int = integer part, kb_mod = modulus part
        # scaled_size = reconstructed float
        kb_int = size
        kb_mod = 0
        scaled_size = kb_int
        # Iterate through each "decade" unit
        for unit in "BKMGTP":

            if not short:
                unit = ' ' + unit + ('iB' if unit != 'B' else '')

            scaled_size = float(kb_int) + float(kb_mod)/1024

            # Various print options. If a matching value range is found then exit loop
            if kb_int < 10:
                sizestr = f"{scaled_size:.2f}{unit}"
                break
            if kb_int < 100:
                sizestr = f"{scaled_size:.1f}{unit}"
                break
            if kb_int < 1000:
                sizestr = f"{scaled_size:.0f}{unit}"
                break
            if kb_int < 2048:
                sizestr = f"{scaled_size:.0f}{unit}"
                break

            # If kb_int (remaining value) is >=2048 then we will go to
            # next unit. Hence we need to divide by 1024 for the next
            # round.
            kb_mod = kb_int % 1024
            kb_int = kb_int >> 10

    if print_full:
        extra = ' bytes'
        if size >= 10000:
            extra = f" ({split_number(size)} bytes)"
        sizestr += extra
    return sizestr


def format_data(obj):
    ''' Return the information for the special field 'data', which return various
        information, depending on type. Files return their sha256 hashsum, links
        their symlink target.
    '''
    if obj.objtype == 'f' and obj.size:
        return obj.hashsum_hex
    if obj.objtype == 'l':
        return obj.link
    return None


def get_fields(objs, prefixes, fieldnames):
    ''' Get a dict of field values from the objects using the given
        fieldnames.
    '''

    fields = {}
    errs = []

    for field in fieldnames:

        for (obj, prefix) in zip(objs, prefixes):

            # Consider only fieldnames with the specific prefix
            if not field.startswith(prefix):
                continue

            # Get the basename of the field and find it in the FILE_FIELDS dict
            fld = field[len(prefix):]
            if fld not in FILE_FIELDS:
                continue

            # Get the data for that field
            try:
                data = FILE_FIELDS[fld](obj)

                # Never print None
                if data is None:
                    data = ''
            except OSError as err:
                data = ERROR_FIELD
                errs.append(err)

            # Store the field
            fields[field] = data

    return (errs, fields)


def get_fieldnames(formatstr):
    ''' Get a set of {fields} used in formatstr '''

    fieldnames = set()
    for (_text, field, _fmt, _conv) in string.Formatter().parse(formatstr):
        if field:
            fieldnames.add(field)
    return fieldnames


def write_fileinfo(formatstr, fields, quoter=None, file=sys.stdout, end='\n'):
    ''' Write the formatstr to the given file. The format fields are
        read from the fields dicts.
    '''

    if not quoter:
        quoter = lambda a: a

    file.write(Formatter(quoter).format(formatstr, **fields) + end)


def write_summary(summary, fields, file=sys.stdout, end='\n'):
    ''' Write the summary '''

    # Use the pre-defined summary_text
    for (var, line) in summary:
        # d.get(n,n) will return d[n] if n exists, otherwise return n.
        # Thus if n is True, True will be returned
        if line and fields.get(var, var):
            file.write(line.format(**fields) + end)


def get_compare_types(comparestr):
    ''' Parse the compare types argument to --compare '''
    if not comparestr:
        return comparestr

    invert = False
    cset = set(comparestr)
    if comparestr[0] == '^':
        invert = True
        cset = set(comparestr[1:])
    foreign = cset.difference(COMPARE_TYPES_ALL)
    if foreign:
        raise ValueError((
            f"Unknown compare type(s): {''.join(foreign)}, "
            f"valid values {''.join(sorted(COMPARE_TYPES_ALL))}"))
    if invert:
        return set(COMPARE_TYPES_ALL).difference(cset)
    return cset


def get_file_types(typestr):
    ''' Parse the type to --types '''
    if not typestr:
        return typestr

    invert = False
    cset = set(typestr)
    if typestr[0] == '^':
        invert = True
        cset = set(typestr[1:])
    foreign = cset.difference(FILE_TYPES_ALL)
    if foreign:
        raise ValueError((
            f"Unknown file type(s): {''.join(foreign)}, "
            f"valid values {''.join(sorted(FILE_TYPES_ALL))}"))
    if invert:
        return set(FILE_TYPES_ALL).difference(cset)
    return cset


class Formatter(string.Formatter):
    ''' Custom formatter class which implements the 'qs' conversion, e.g.
        "My text is {name:qs}". When encountered it will run the quoter
        function prior to printing it with '{name:s}'
    '''

    def __init__(self, quoter, *args, **kwargs):
        self.quoter = quoter
        super().__init__(*args, **kwargs)

    def format_field(self, value, format_spec):
        if format_spec == 'qs':
            format_spec = 's'
            value = self.quoter(value)
        return super().format_field(value, format_spec)


class FileHistogram:
    ''' Histogram for counting file objects '''

    def __init__(self, directory):
        self.dir = directory
        self.size = 0
        self.bins = {}

    def add(self, item):
        ''' Increase count of variable item '''
        self.bins[item] = self.bins.get(item, 0) + 1

    def get(self, item):
        ''' Return count value of v '''
        return self.bins.get(item, 0)

    def add_size(self, size):
        ''' Add size variable '''
        self.size += size

    def get_summary_fields(self):
        ''' Return a dict with all histogram fields '''
        return {
            'dir': self.dir,
            'n_files': self.get('f'),
            'n_dirs': self.get('d'),
            'n_symlinks': self.get('l'),
            'n_special': self.get('b')+self.get('c')+self.get('p')+self.get('s'),
            'n_blkdev': self.get('b'),
            'n_chrdev': self.get('c'),
            'n_fifos': self.get('p'),
            'n_sockets': self.get('s'),
            'n_missing': self.get('-'),
            'n_exclude': self.get('x'),
            'n_objects': sum(self.bins.values()),
            'sum_bytes': self.size,
            'sum_bytes_t': format_bytes(self.size, print_full=True),
        }


class CompareHistogram:
    ''' Histogram for counting compare relationship '''

    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.bins = {}

    def add(self, item):
        ''' Increase count of variable item '''
        self.bins[item] = self.bins.get(item, 0) + 1

    def get(self, item):
        ''' Return count value of item '''
        return self.bins.get(item, 0)

    def get_summary_fields(self):
        ''' Return a dict with all histogram fields '''
        return {
            'left': self.left,
            'right': self.right,
            'n_equal': self.get('equal'),
            'n_changed': self.get('changed'),
            'n_different_type': self.get('different_type'),
            'n_left_only': self.get('left_only'),
            'n_right_only': self.get('right_only'),
            'n_left_newer': self.get('left_newer'),
            'n_right_newer': self.get('right_newer'),
            'n_scan': self.get('scan'),
            'n_excludes': self.get('excluded'),
            'n_errors': self.get('error'),
            'n_skipped': self.get('skipped'),
            'n_err': self.get('err'),
            'n_objects': sum(self.bins.values())-self.get('err'),
        }


class Statistics:
    ''' Class for collecting dirscan statistics '''

    def __init__(self, left, right):
        self.compare = CompareHistogram(left, right)
        if right is None:
            self.filehist = [FileHistogram(left)]
        else:
            self.filehist = [FileHistogram(left), FileHistogram(right)]

    def add_stats(self, change):
        ''' Collect compare statistics '''
        self.compare.add(change)

    def add_filestats(self, objs):
        ''' Collect file statistics from objs list '''

        for (obj, filehist) in zip(objs, self.filehist):
            objtype = 'x' if obj.excluded else obj.objtype
            filehist.add(objtype)
            if objtype == 'f':
                filehist.add_size(obj.size)

    def get_fields(self, prefixes):
        ''' Get the summary fields '''

        # Get the main comparison fields
        fields = self.compare.get_summary_fields()

        # Assemble the per-directory summaries
        for (filehist, prefix) in zip(self.filehist, prefixes):

            for field, data in filehist.get_summary_fields().items():

                # Replace 'n_' with specified prefix
                if field.startswith('n_') and prefix:
                    field = field[2:]
                fields[prefix + field] = data

        return fields
