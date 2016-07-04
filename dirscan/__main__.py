# -*- coding: utf-8 -*-
#
# This file is a part of dirscan, a handy tool for recursively
# scanning and comparing directories and files
#
# Copyright (C) 2010-2016 Svein Seldal, sveinse@seldal.com
# URL: https://github.com/sveinse/dirscan
#
# This application is licensed under GNU GPL version 3
# <http://gnu.org/licenses/gpl.html>. This is free software: you are
# free to change and redistribute it. There is NO WARRANTY, to the
# extent permitted by law.
#
from __future__ import absolute_import

import sys
import os
import argparse
import fnmatch
import datetime

from . import dirscan
from . import fileinfo


#
# SCAN FILE READER
# ================
#
scanfile_format = "{type},{size},{mode},{uid},{gid},{mtime_n},{data},{path}"

def readscanfile(fname):
    ''' Read fname scan file and return a DirObj() with the file tree root '''

    dirtree = { }
    rootobj = None

    with open(fname, 'r') as f:
        n=0
        for line in f:
            n+=1

            # Read/parse the parameters
            args = [ fileinfo.unquote(e) for e in line.rstrip().split(',') ]
            otype = args[0]
            osize = int(args[1] or '0')
            omode = int(args[2])
            ouid  = int(args[3])
            ogid  = int(args[4])
            otime = datetime.datetime.fromtimestamp(float(args[5]))
            odata = args[6] or None
            opath = args[7]

            if opath == '.':
                opath = fname
            elif opath.startswith('./'):
                opath = opath.replace('./',fname+'/',1)

            # Split path into path and name
            (path, name) = os.path.split(opath)
            if path.endswith('/'):
                path=path[:-1]

            # Create new object.
            obj = dirscan.newFromData(path, name, otype, osize, omode, ouid, ogid, otime, odata)

            # The first object is special
            if path == '':
                rootobj = obj
                dirtree[opath] = obj
            else:
                # Add the object into the parent's children
                dirtree[path][name] = obj

            # Make sure we make an entry into the dirtree to ensure we have a list of the parents
            if otype == 'd':
                dirtree[opath] = obj

    # Now the tree should be populated
    return rootobj



#
# SCAN WORKER
# ===========
#
def scanworker(left,right,exclude,traverse=False,ignore=''):

    # If either left or write is file, they should be parsed as scan files
    left_path = left
    right_path = right
    if os.path.isfile(left):
        left = readscanfile(left)
    if right and os.path.isfile(right):
        right = readscanfile(right)

    # Create the list of directories to traverse
    dirlist = [ left ]
    if right is not None:
        dirlist.append(right)
    l = len(dirlist)

    # Traverse the directories
    for (path,ob) in dirscan.walkdirs(dirlist):

        # Excluded file?
        fullpath = ob[0].fullpath
        if [ fnmatch.fnmatch(fullpath, e) for e in exclude ].count(True) > 0:
            # File EXCLUDED
            # =============
            yield (path, ob, 'excluded', 'excluded')

        elif ob[0].parserr or ( l>1 and ob[1].parserr ):
            # File ERROR
            # ==========
            yield (path, ob, 'error', [ o.parserr for o in ob ] )

        elif l<2:
            # Left side SCANNING only
            # =======================
            yield (path, ob, 'scan', 'scan')

        elif ob[0].objtype == '-':
            # File present RIGHT only
            # =======================
            if traverse or ob[0].hasparent:
                text="%s only in %s" %(ob[1].objname,right_path)
                yield (path, ob, 'right_only', text)

        elif ob[1].objtype == '-':
            # File present LEFT only
            # ======================
            if traverse or ob[1].hasparent:
                text="%s only in %s" %(ob[0].objname,left_path)
                yield (path, ob, 'left_only', text)

        elif ob[0].objtype != ob[1].objtype:
            # File type DIFFERENT
            # ===================
            text="Different type, %s in %s and %s in %s" %(ob[0].objname,left_path,ob[1].objname,right_path)
            yield (path, ob, 'different_type', text)

        else:

            # File type EQUAL
            # ===============

            # compare returns a list of differences. If None, they are equal
            try:
                rl=ob[0].compare(ob[1])
            except IOError as e:
                # Compares might fail -- and then it not known if its ob[0] or ob[1] that fails.
                # Compare the filename in the error with the path in the object and use that
                # to construct the error we send back.
                err = [ e if e.filename == o.fullpath else None for o in ob ]
                # If no object match, send the error as the first object
                if not all(err):
                    err[0] = e
                yield (path, ob, 'error', err )
                continue

            if rl:
                # Make a new list and filter out the ignored differences
                el=[]
                change='changed'
                for r in rl:
                    if 'newer' in r:
                        if 't' in ignore:
                            continue
                        r = '%s is newer' %(left_path)
                        change='left_newer'
                    elif 'older' in r:
                        if 't' in ignore:
                            continue
                        r = '%s is newer' %(right_path)
                        change='right_newer'
                    elif 'u' in ignore and 'UID differs' in r:
                        continue
                    elif 'g' in ignore and 'GID differs' in r:
                        continue
                    elif 'p' in ignore and 'Permissions differs' in r:
                        continue
                    el.append(r)

                if el:  # else from this test indicates file changed, but all changes have been masked with
                        # the above ignore settings

                    # File contents CHANGED
                    # =====================
                    text="%s changed: %s" %(ob[0].objname,", ".join(el))
                    yield (path, ob, change, text)
                    continue

                # Compares with changes may fall through here because of ignore settings

            # File contents EQUAL
            # ===================
            yield (path, ob, 'equal', 'equal')



#
# SCAN DIRS
# =========
#
def scandirs(left,right,outfile,exclude,opts):
    ''' Scan dir and write output to outfile '''

    #
    # Determine print format
    # ----------------------
    #

    # Default format
    format = printformat = '{path}'

    # Determine default format from options
    if right is None:
        format = '{fullpath}'
        comparetypes = 's'
        filetypes = 'fdlbcps'
        printformat = format

        if outfile:
            format = scanfile_format

        elif opts.all and opts.long:
            if opts.human:
                format = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {mtime}  {type}  {fullpath}'
            else:
                format = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {mtime}  {type}  {fullpath}'

        elif opts.all:
            if opts.human:
                format = '{mode_t}  {user:8} {group:8}  {size:>5}  {data:>64}  {type}  {fullpath}'
            else:
                format = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {data:>64}  {type}  {fullpath}'

        elif opts.long:
            if opts.human:
                format = '{mode_t}  {user:8} {group:8}  {size:>5}  {mtime}  {type}  {fullpath}'
            else:
                format = '{mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {type}  {fullpath}'

    else:
        format = '{arrow}  {path}  :  {text}'
        comparetypes = 'rldcLR'
        filetypes = 'fdlbxps'

        # Does outfile make any sense in compare mode?

        if opts.all:
            comparetypes = ''.join([ fileinfo.compare_arrows[x][0] for x in fileinfo.compare_arrows ])

    # User provided format overrides any defaults
    format = opts.format or format
    comparetypes = opts.comparetypes or comparetypes
    filetypes = opts.filetypes or filetypes
    # -------------------------------------------------


    # Prepare the histograms to collect statistics
    comparehist = fileinfo.CompareHistogram(left,right)
    if right is None:
        filehist = [ fileinfo.FileHistogram(left) ]
        prefixlist = [ '' ]
    else:
        filehist = [ fileinfo.FileHistogram(left), fileinfo.FileHistogram(right) ]
        prefixlist = [ 'l_', 'r_' ]



    f = None
    try:
        size = 0

        # Setup output destination/files
        if not outfile:
            f = sys.stdout
            doprint = False
            dowrite = not opts.quiet
            quoter = lambda a: a   # No quoter on stdout
        else:
            f = open(outfile, 'w')
            doprint = opts.verbose
            dowrite = True
            quoter = lambda a: fileinfo.quote(a)


        # Prepare the list of formats to use
        formatlist = []
        if doprint:
            formatlist.append(printformat)
        if dowrite:
            if not (doprint and printformat == format):
                formatlist.append(format)


        # Traverse the directories
        for (path, ob, change, text) in scanworker(left, right, exclude, traverse=opts.traverse, ignore=opts.ignore):

            show = True
            fields = { }

            # Handle excludes
            if change == 'excluded':
                show = 'x' in comparetypes

            # Print errors errors
            if change == 'error':
                for (o,err) in zip(ob,text):
                    if err is not None and not opts.realquiet:
                        sys.stderr.write('%s: %s\n' %(opts.prog, err))

            # Show this file type? -- this works only on left side objects
            if ob[0].objtype not in filetypes:
                show = False

            # Get dict of file info fields used by the formatlist
            if show:
                (err, fields) = fileinfo.get_fileinfo(path, ob, change, text, prefixlist, formatlist)
                if err:
                    if not opts.realquiet:
                        sys.stderr.write('%s: %s\n' %(opts.prog, err))
                    change = 'error'
                    fields['change'] = change

            # Bail out if the change type is excluded from the show filter
            if fileinfo.compare_arrows[change][0] not in comparetypes:
                show = False

            # Print to stdout (used if writing to file)
            if show and doprint:
                fileinfo.write_fileinfo(fields, printformat, quoter=lambda a:a, f=sys.stdout)

            # Write to stdout or file
            if show and dowrite:
                fileinfo.write_fileinfo(fields, format, quoter=quoter, f=f)

            # Save file histogram info on the shown items only
            if show:
                for (o,fh) in zip(ob,filehist):
                    fh.add(o.objtype)
                    if o.objtype == 'f':
                        fh.add_size(o.size)

            # Save histogram info for the change type
            comparehist.add(change)


    finally:
        # Close any open output file
        if f and f != sys.stdout:
            f.close()


    has_errors = False
    if opts.summary is not None:

        summary_fields = {
            'prog':  opts.prog,
        }

        # Get the global comparison summary
        summary_fields.update(comparehist.get_summary_fields())

        # Assemble the per-directory summaries
        for (fh,pre) in zip(filehist,prefixlist):
            for e,d in fh.get_summary_fields().items():

                # Replace 'n_' with specified prefix
                if e.startswith('n_') and len(pre):
                    e = e[2:]
                summary_fields[pre + e] = d

        # Get the summary texts
        if any(opts.summary):
            summary_text = [ (True, s) for s in opts.summary ]
        else:
            if right is None:
                summary_text = fileinfo.summary_scan[:]
            else:
                summary_text = fileinfo.summary_compare[:]

            if not opts.realquiet:
                summary_text.append(
                    ( 'n_errors', "\n{prog}: **** {n_errors} files or directories could not be read due to errors" )
                )

        # Print the summary text
        try:
            # Use the pre-defined summary_text
            for (doprint,line) in summary_text:
                # d.get(n,n) will return the d value for n if n exists, otherwise return n.
                # Thus if n is True, True will be returned
                if line is not None and summary_fields.get(doprint,doprint):
                    sys.stderr.write(line.format(**summary_fields)+'\n')

        # .format() might fail
        except (KeyError, IndexError, ValueError) as e:
            raise SyntaxError("Format error: %s" %(e))


    # Return error code if we have encountered any errors scanning
    if comparehist.get('error'):
        return 1

    return 0



#
# MAIN
# ====
#
def main(args=None):

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

(C) 2010-2016 Svein Seldal. This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.

'''
    epilog = ''

    ap = argparse.ArgumentParser(description=description, epilog=epilog, add_help=False)
    ap.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    ap.add_argument('--help', action='help')

    # Common options
    ap.add_argument('-a', '--all', action='store_true', dest='all', default=False, help='Print all file info')
    ap.add_argument('-h', '--human', action='store_true', dest='human', default=False, help='Display human readable sizes')
    ap.add_argument('-l', '--long', action='store_true', dest='long', default=False, help='Dump file in extended format')
    ap.add_argument('-q', '--quiet', action='store_true', dest='quiet', default=False, help='Quiet operation')
    ap.add_argument('-Q', '--suppress-errors', action='store_true', dest='realquiet', default=False, help='Suppress error messages')
    ap.add_argument('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose printing')

    ap.add_argument('-F', '--format', metavar='TEMPLATE', dest='format', default=None, help='Custom file info line template')
    ap.add_argument('-s', '--summary', metavar='SUMMARY_TEMPLATE', nargs='?', action='append', dest='summary', default=None, help='Print scan statistics summary. Optional argument specified custom summary template. The option can be used multiple times for multiple template lines')
    ap.add_argument('-f', '--file-types', metavar='TYPES', action='store', dest='filetypes', default='', help='Show only file types. f=files, d=dirs, l=links, b=blkdev, c=chrdev, p=pipes, s=sockets')
    ap.add_argument('-X', '--exclude-dir', metavar='PATH', action='append', dest='exclude', default=[], help='Exclude PATH from scan. PATH is relative to DIR')

    # Scan options
    ap.add_argument('-o', '--output', metavar='FILE', action='store', dest='outfile', help='Store scan output in FILE')

    # Diff options
    ap.add_argument('-c', '--compare', metavar='TYPES', action='store', dest='comparetypes', default='', help='Show only compare types e=equal, l=only left, r=only right, c=changed, L=left is newest, R=right is newest, d=different type, E=error, x=excluded')
    ap.add_argument('-i', '--ignore', metavar='IGNORES', action='store', dest='ignore', default='', help='Ignore differences in u=uid, g=gid, p=permissions, t=time')
    ap.add_argument('-t', '--traverse', action='store_true', dest='traverse', default=False, help='Traverse the children of directories that exists on only one side when comparing directories')

    # Main arguments
    ap.add_argument('dir1', metavar='LEFT_DIR', help='Directory to scan/traverse, or LEFT side of comparison')
    ap.add_argument('dir2', metavar='RIGHT_DIR', help='If present, compare LEFT side with RIGHT side', default=None, nargs='?')

    # FIXME:  Other possible options:
    #   --print0  to safely interact with xargs -0
    #   --filter  on scan to show only certain kind of file types


    # -- Global options not passed via function arguments
    global opts
    opts = ap.parse_args()
    global prog
    opts.prog = ap.prog


    # -- Append additional 'name/*' in the list of excludes to make sure we also ignore sub-dirs
    exclude = []
    for e in opts.exclude:
        exclude.append( os.path.join(opts.dir1,e) )
        if not e.endswith('*'):
            exclude.append( os.path.join(opts.dir1,e,'*') )


    # -- COMMAND HANDLING
    return scandirs(opts.dir1,opts.dir2,opts.outfile,exclude,opts)



if __name__ == '__main__':
    main()
