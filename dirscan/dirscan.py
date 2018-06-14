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

import os
import datetime
import stat as fstat
import itertools
import hashlib
import errno
import filecmp
import fnmatch
import binascii

from .log import debug


# Select hash algorthm to use
HASHALGORITHM = hashlib.sha256

HASHCHUNKSIZE = 16*1024*1024


class DirscanException(Exception):
    ''' Directory scan error '''



############################################################
#
#  FILE CLASS OBJECTS
#  ==================
#
############################################################

class BaseObj(object):
    ''' File Objects Base Class '''

    def __init__(self, name, path='', stat=None, treeid=None):

        # Ensure the name does not end with a slash, that messes up path
        # calculations later in directory compares
        if name != '/':
            name = name.rstrip('/')

        self.path = path
        self.name = name
        self.stat = stat
        self.treeid = treeid

        self.parsed = False
        self.excluded = False


    @property
    def fullpath(self):
        return os.path.join(self.path, self.name)

    @property
    def mode(self):
        return self.stat.st_mode

    @property
    def uid(self):
        return self.stat.st_uid

    @property
    def gid(self):
        return self.stat.st_gid

    @property
    def dev(self):
        return self.stat.st_dev

    @property
    def size(self):
        return self.stat.st_size

    @property
    def mtime(self):
        return datetime.datetime.fromtimestamp(self.stat.st_mtime)


    def parse(self, done=True):
        ''' Parse the object. Get file stat info. '''
        if self.parsed:
            return
        if not self.stat:
            self.stat = os.lstat(self.fullpath)
        self.parsed = done


    def children(self):
        ''' Return tuple of sub objects. Non-directory file objects that does not
            have any children will return an empty tuple. '''
        return tuple()


    def close(self):
        ''' Delete any allocated objecs within this class '''
        self.parsed = False


    def compare(self, other, s=None):
        ''' Return a list of differences '''
        if s is None:
            s = []
        if type(other) is not type(self):
            return ['type mismatch']
        if self.uid != other.uid:
            s.append('UID differs')
        if self.gid != other.gid:
            s.append('GID differs')
        if self.mode != other.mode:
            s.append('permissions differs')
        if self.mtime > other.mtime:
            s.append('newer')
        elif self.mtime < other.mtime:
            s.append('older')
        return s


    #pylint: disable=unused-argument
    def get(self, child, nochild=None):
        ''' Return child object child, return nochild if not present '''
        return nochild


    def __repr__(self):
        treeid = '%s:' %(self.treeid) if self.treeid is not None else ''
        return "%s(%s'%s')" %(type(self).__name__, treeid, self.fullpath)


    def exclude_otherfs(self, base):
        ''' Set excluded flag if this object differs from fs '''

        # Note that self.excluded will be set on NonExistingObj() since they
        # have dev = None
        if self.dev != base.dev:
            self.excluded = True


    def exclude_files(self, excludes, base):
        ''' Set excluded flag if any of the entries in exludes matches
            this object '''
        for ex in excludes:
            ex = os.path.join(base.fullpath, ex)
            if fnmatch.fnmatch(self.fullpath, ex):
                self.excluded = True
                return



class FileObj(BaseObj):
    ''' Regular File Object '''
    objtype = 'f'
    objname = 'file'

    hashsum_cache = None


    def hashsum(self):
        ''' Return the hashsum of the file '''

        # This is not a part of the parse() structure because it can take
        # considerable time to evaluate the hashsum, hence its done on
        # need-to have basis.
        if self.hashsum_cache:
            return self.hashsum_cache

        m = HASHALGORITHM()
        with open(self.fullpath, 'rb') as f:
            while True:
                data = f.read(HASHCHUNKSIZE)
                if not data:
                    break
                m.update(data)
            self.hashsum_cache = m.digest()
        return self.hashsum_cache


    def hashsum_hex(self):
        return binascii.hexlify(self.hashsum()).decode('ascii')


    def compare(self, other, s=None):
        ''' Compare two file objects '''
        if s is None:
            s = []
        if self.size != other.size:
            s.append('size differs')
        elif self.hashsum_cache or other.hashsum_cache:
            # Does either of them have hashsum_cache set? If yes, make use of
            # hashsum based compare. filecmp might be more efficient, but if we
            # read from listfiles, we have to use hashsums.
            if self.hashsum() != other.hashsum():
                s.append('contents differs')
        elif not filecmp.cmp(self.fullpath, other.fullpath, shallow=False):
            s.append('contents differs')
        return BaseObj.compare(self, other, s)



class LinkObj(BaseObj):
    ''' Symbolic Link File Object '''
    objtype = 'l'
    objname = 'symbolic link'

    link = None


    def parse(self, done=True):
        # Execute super
        if self.parsed:
            return
        BaseObj.parse(self, done=False)

        # Read the contents of the link
        self.link = os.readlink(self.fullpath)
        self.parsed = True


    def compare(self, other, s=None):
        ''' Compare two link objects '''
        if s is None:
            s = []
        if self.link != other.link:
            s.append('link differs')
        return BaseObj.compare(self, other, s)



class DirObj(BaseObj):
    ''' Directory File Object '''
    objtype = 'd'
    objname = 'directory'

    size = None


    def __init__(self, name, path='', stat=None, treeid=None):
        BaseObj.__init__(self, name, path, stat, treeid)
        self.dir = {}
        self.dir_parsed = False


    def close(self):
        ''' Delete all used references to allow GC cleanup '''
        self.dir.clear()
        self.dir_parsed = False
        BaseObj.close(self)


    def children(self):
        ''' Return a dict of the sub objects '''
        if not self.dir_parsed:

            # Setting dir_parsed first has the subtle effect that if
            # os.lostdir() fails, it will still label the dir as parsed.
            # This avoids rescanning and thus failing if the tree is
            # scanned twice.
            self.dir_parsed = True

            # Try to get list of sub directories and make new sub object
            for name in os.listdir(self.fullpath):
                self.dir[name] = create_from_fs(name, self.fullpath, treeid=self.treeid)

        return tuple(self.dir.keys())


    def get(self, child, nochild=None):
        ''' Return child object child '''
        return self.dir.get(child, nochild)


    def add_child(self, child):
        ''' Add child object '''
        self.dir[child.name] = child



class SpecialObj(BaseObj):
    ''' Device (block or char) device '''
    objtype = 's'
    objname = 'special file'

    size = None


    def __init__(self, name, path='', stat=None, dtype='s', treeid=None):
        BaseObj.__init__(self, name, path, stat, treeid)
        self.objtype = dtype

        # The known special device types
        if dtype == 'b':
            self.objname = 'block device'
        elif dtype == 'c':
            self.objname = 'char device'
        elif dtype == 'p':
            self.objname = 'fifo'
        elif dtype == 's':
            self.objname = 'socket'


    def compare(self, other, s=None):
        ''' Compare two link objects '''
        if s is None:
            s = []
        if self.objtype != other.objtype:
            s.append('device type differs')
        return BaseObj.compare(self, other, s)



class NonExistingObj(BaseObj):
    ''' NonExisting File Object. Evaluates to false for everything. Used by the
        walkdirs() when parsing multiple trees in parallell to indicate a
        non-existing file object in one or more of the trees. '''
    objtype = '-'
    objname = 'missing file'

    def parse(self, done=True):
        self.stat = os.stat_result((None, None, None, None, None, None, None, None, None, None))
        self.parsed = True



############################################################
#
#  OBJECT FACTORIES
#  ================
#
############################################################

def create_from_fs(name, path='', treeid=None):
    ''' Create a new object from file system path and return an
        instance of the object. The object type returned is based on
        stat of the actual file system entry.'''
    fullpath = os.path.join(path, name)
    s = os.lstat(fullpath)
    o = None
    t = s.st_mode
    if fstat.S_ISREG(t):
        o = FileObj(name, path, s, treeid=treeid)
    elif fstat.S_ISDIR(t):
        o = DirObj(name, path, s, treeid=treeid)
    elif fstat.S_ISLNK(t):
        o = LinkObj(name, path, s, treeid=treeid)
    elif fstat.S_ISBLK(t):
        o = SpecialObj(name, path, s, 'b', treeid=treeid)
    elif fstat.S_ISCHR(t):
        o = SpecialObj(name, path, s, 'c', treeid=treeid)
    elif fstat.S_ISFIFO(t):
        o = SpecialObj(name, path, s, 'p', treeid=treeid)
    elif fstat.S_ISSOCK(t):
        o = SpecialObj(name, path, s, 's', treeid=treeid)
    else:
        raise DirscanException("%s: Uknown file type" %(fullpath))
    return o



def create_from_data(name, path, objtype, size, mode, uid, gid, mtime, data=None, treeid=None):
    ''' Create a new object from the given data and return an
        instance of the object. '''

    # Make a fake stat element from the given meta-data
    # st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size, st_atime, st_mtime, st_ctime
    fakestat = os.stat_result((mode, None, None, None, uid, gid, size, None, mtime, None))

    if objtype == 'f':
        o = FileObj(name, path, stat=fakestat, treeid=treeid)
        o.hashsum_cache = binascii.unhexlify(data) if data else None

        # Hashsum is normally not defined if the size is 0.
        if not data and size == 0:
            m = HASHALGORITHM()
            o.hashsum_cache = m.digest()

    elif objtype == 'l':
        o = LinkObj(name, path, stat=fakestat, treeid=treeid)
        o.link = data

    elif objtype == 'd':
        o = DirObj(name, path, stat=fakestat, treeid=treeid)
        o.dir_parsed = True

    elif objtype == 'b' or objtype == 'c' or objtype == 'p' or objtype == 's':
        o = SpecialObj(name, path, stat=fakestat, dtype=objtype, treeid=treeid)

    else:
        raise DirscanException("Unknown object type '%s'" %(objtype))

    # Ensure we don't go out on the FS
    o.parsed = True
    return o



############################################################
#
#  DIRECTORY TRAVERSER
#  ===================
#
############################################################

def walkdirs(dirs, reverse=False, excludes=None, onefs=False,
             traverse_oneside=None, exception_fn=None, close_during=True):
    '''
    Generator function that recursively traverses the directories in
    list ``dirs``. This function can scan a file system or compare two
    or more directories in parallel.

    As it walks the directories, it will yield tuples containing
    ``(path, objs)`` for each file object it finds. ``path`` represents the
    common file path. ``objs`` is a tuple of file objects representing the
    respective found file object from the directories given by the ``dirs``
    list. The objects returned are derived types of ``BaseObj``, such
    as ``FileObj``, ``DirObj``. If a file is only present in one of the
    dirs,  the object returned in the dirs where the file isn't present will
    be returned as a ``NonExistingObj`` object.

    **Arguments:**
     ``dirs``
        List of directories to walk. The elements must either be a path string
        to a physical directory or a previously parsed ``DirObj`` object.
        If a string is given, the file system given by the path will be
        recursively scanned for files. If a ``DirObj`` object is given, the
        in-object cached data will be used for traversal. The latter is useful
        e.g. when reading scan files from disk.

     ``reverse``
        Reverses the scanning order

     ``excludes``
        List of excluded paths, relative to the common path

     ``onefs``
        Scan file objects belonging to the same file system only

     ``traverse_onside``
        Will walk/yield all file objects in a directory that exists on only one
        side

     ``exception_fn``
        Exception handler callback. It has format ``exception_fn(exception)``
        returning ``Bool``. It will be called if any scanning exceptions occur
        during traversal. If exception_fn() returns False or is not set, an
        ordinary exception will be raised.

     ``close_during``
        will call ``obj.close()`` on objects that have been yielded to the
        caller. This allows freeing up parsed objects to conserve memory. Note
        that this tears down the in-memory directory tree, making it impossible
        to reuse the object tree after ``walkdirs()`` is complete.

    '''

   # Ensure the exclusion list is a list
    if excludes is None:
        excludes = []

    # Set default of traverse_oneside depending on if one-dir scanning or
    # comparing multiple dirs
    if traverse_oneside is None:
        traverse_oneside = True if len(dirs) == 1 else False

    # Check list of dirs indeed are dirs and create initial object list to
    # start from
    base = []
    for d in dirs:
        if isinstance(d, DirObj):
            o = d
        elif os.path.isdir(d):
            o = DirObj(d)
        else:
            e = OSError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), d)
            raise DirscanException(str(e))
        base.append(o)

        # Parse the object to get the device.
        try:
            o.parse()
            o.children()   # To force an exception here if permission denied
        except OSError as err:
            raise DirscanException(str(err))

    # Handle the special cases with '/' -> './'
    basename = base[0].name
    baserepl = '.'
    if basename == '/':
        baserepl = './'

    # Start the queue
    queue = [tuple(base)]

    # Traverse the queue
    while queue:

        # Get the next set of objects
        objs = queue.pop(-1)

        # Relative path: Gives '.', './a', './b'
        path = objs[0].fullpath.replace(basename, baserepl, 1)
        if path == './':
            path = '.'

        # Parse the objects, getting object metadata
        for o, b in zip(objs, base):
            try:
                # Get file object metadata
                o.parse()

                # Test for exclusions
                o.exclude_files(excludes, base=b)
                if onefs:
                    o.exclude_otherfs(base=b)

            # Parsing the object failed
            except OSError as err:
                # Call the user exception callback, raise if not
                if not exception_fn or not exception_fn(err):
                    raise

        # How many objects are present?
        present = sum([not isinstance(o, NonExistingObj) and not o.excluded for o in objs])

        # Send back object list to caller
        debug('scan %s:  %s' %(path, objs))
        yield (path, objs)

        # Create a list of unique children names seen across all objects, where
        # excluded objects are removed from parsing
        subobjs = []
        for o in objs:
            try:
                # Skip the children if...

                # ...the parent is excluded
                if o.excluded:
                    continue

                # ..the parent is the only one
                if not traverse_oneside and present == 1:
                    continue

                # Get and append the children names
                children = o.children()
                debug("  Children of %s is %s" %(o, children))
                subobjs.append(children)

            # Getting the children failed
            except OSError as err:
                # Call the user exception callback, raise if not
                if not exception_fn or not exception_fn(err):
                    raise

        # Merge all subobjects into a single list of unique, sorted, children names
        children = []
        for name in sorted(set(itertools.chain.from_iterable(subobjs)), reverse=not reverse):

            # Create a list of children objects for that name
            child = [o.get(name, NonExistingObj(name, o.fullpath, treeid=o.treeid)) for o in objs]

            # Append it to the processing list
            children.append(tuple(child))

        # Close objects to conserve memory
        if close_during:
            for o in objs:
                o.close()

        # Append the newly discovered objects to the queue
        queue.extend(children)
