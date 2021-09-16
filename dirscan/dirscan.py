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
import os
import datetime
import stat as osstat
import itertools
import hashlib
import filecmp
import fnmatch
import binascii
from pathlib import Path

from dirscan.log import debug


# Select hash algorthm to use
HASHALGORITHM = hashlib.sha256

# Number of bytes to read per round in the hash reader
HASHCHUNKSIZE = 16*4096

# Minimum difference in seconds to consider it a changed timestamp
TIME_THRESHOLD = 1


class DirscanException(Exception):
    ''' Directory scan error '''


############################################################
#
#  FILE CLASS OBJECTS
#  ==================
#
############################################################

class DirscanObj:
    ''' Directory scan file objects base class '''

    __slots__ = ('name', 'path', 'excluded',
                 'mode', 'uid', 'gid', 'dev', 'size', '_mtime')

    def __init__(self, name, path='', stat=None):

        # Ensure the name does not end with a slash, that messes up path
        # calculations later in directory compares
        if name != '/':
            name = name.rstrip('/')

        self.name = name
        self.path = path
        self.excluded = False

        # Only save the actual file mode, not the type field. However, this
        # will lose additional mode field information.
        self.mode = osstat.S_IMODE(stat.st_mode)
        self.uid = stat.st_uid
        self.gid = stat.st_gid
        self.dev = stat.st_dev
        self.size = stat.st_size
        self._mtime = stat.st_mtime

    @property
    def fullpath(self):
        ''' Return the complete path of the object '''
        return Path(self.path, self.name)

    @property
    def mtime(self):
        ''' Return the modified timestamp of the file '''
        return datetime.datetime.fromtimestamp(self._mtime)

    def children(self):  # pylint: disable=no-self-use
        ''' Return iterator of sub objects. Non-directory file objects that
            does not have any children will return an empty tuple. '''
        return ()

    def close(self):
        ''' Delete any allocated objecs within this class '''

    def compare(self, other):
        ''' Return a list of differences '''
        if type(self) is not type(other):
            yield 'type mismatch'
            return
        time_delta = self._mtime - other._mtime
        if time_delta > TIME_THRESHOLD:
            yield 'newer'
        if time_delta < -TIME_THRESHOLD:
            yield 'older'
        if self.mode != other.mode:
            yield 'permissions differs'
        if self.uid != other.uid:
            yield 'UID differs'
        if self.gid != other.gid:
            yield 'GID differs'

    def __repr__(self):
        return f"{type(self).__name__}({self.path},{self.name})"


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
            ex = Path(base.fullpath, ex)
            if fnmatch.fnmatch(self.fullpath, ex):
                self.excluded = True
                return


class FileObj(DirscanObj):
    ''' Regular File Object '''
    objtype = 'f'
    objname = 'file'
    objmode = osstat.S_IFREG

    __slots__ = ('hashsum_cache',)

    def __init__(self, name, path='', stat=None, hashsum=None):
        super().__init__(name, path=path, stat=stat)
        self.hashsum_cache = hashsum

    @property
    def hashsum(self):
        ''' Return the hashsum of the file '''

        # This is not a part of the parse() structure because it can take
        # considerable time to evaluate the hashsum, hence its done on
        # need-to have basis.
        if self.hashsum_cache:
            return self.hashsum_cache

        shahash = HASHALGORITHM()
        with open(self.fullpath, 'rb') as shafile:
            while True:
                data = shafile.read(HASHCHUNKSIZE)
                if not data:
                    break
                shahash.update(data)
            self.hashsum_cache = shahash.digest()
        return self.hashsum_cache

    @property
    def hashsum_hex(self):
        ''' Return the hex hashsum of the file '''
        return binascii.hexlify(self.hashsum).decode('ascii')

    def compare(self, other):
        ''' Compare two file objects '''
        yield from super().compare(other)
        if self.size != other.size:
            yield 'size differs'
        elif self.hashsum_cache or other.hashsum_cache:
            # Does either of them have hashsum_cache set? If yes, make use of
            # hashsum based compare. filecmp might be more efficient, but if we
            # read from listfiles, we have to use hashsums.
            if self.hashsum != other.hashsum:
                yield 'contents differs'
        elif not filecmp.cmp(self.fullpath, other.fullpath, shallow=False):
            yield 'contents differs'


class LinkObj(DirscanObj):
    ''' Symbolic Link File Object '''
    objtype = 'l'
    objname = 'symbolic link'
    objmode = osstat.S_IFLNK

    __slots__ = ('link',)

    def __init__(self, name, path='', stat=None, link=None):
        super().__init__(name, path=path, stat=stat)
        self.link = link

    def compare(self, other):
        ''' Compare two link objects '''
        yield from super().compare(other)
        if self.link != other.link:
            yield 'link differs'


class DirObj(DirscanObj):
    ''' Directory File Object '''
    objtype = 'd'
    objname = 'directory'
    objmode = osstat.S_IFDIR

    __slots__ = ('_children',)

    def __init__(self, name, path='', stat=None, children=None):
        super().__init__(name, path=path, stat=stat)
        self.size = None
        self._children = children

    def close(self):
        ''' Delete all used references to allow GC cleanup '''
        super().close()
        self._children = None

    def children(self):
        ''' Return an iterator of the sub object names '''
        if self._children is None:
            self._children = tuple(create_from_fsdir(self.fullpath))
        return self._children

    def set_children(self, children):
        ''' Set the directory children '''
        self._children = children


class BlockDevObj(DirscanObj):
    ''' Block Device Object '''
    objtype = 'b'
    objname = 'block device'
    objmode = osstat.S_IFBLK


class CharDevObj(DirscanObj):
    ''' Char Device Object '''
    objtype = 'c'
    objname = 'char device'
    objmode = osstat.S_IFCHR


class FifoObj(DirscanObj):
    ''' Fifo File Object '''
    objtype = 'p'
    objname = 'fifo'
    objmode = osstat.S_IFIFO


class SocketObj(DirscanObj):
    ''' Socket File Object '''
    objtype = 's'
    objname = 'socket'
    objmode = osstat.S_IFSOCK


class NonExistingObj(DirscanObj):
    ''' NonExisting File Object. Evaluates to false for everything. Used by the
        walkdirs() when parsing multiple trees in parallell to indicate a
        non-existing file object in one or more of the trees. '''
    objtype = '-'
    objname = 'missing file'

    def __init__(self, name, path=''):
        stat = os.stat_result((None, None, None, None, None, None, None, None, None, None))
        super().__init__(name, path=path, stat=stat)


# Tuple of all file objects. NonExistingObj is deliberately omitted
ALL_FILEOBJECT_CLASS = (
    FileObj,
    DirObj,
    LinkObj,
    BlockDevObj,
    CharDevObj,
    FifoObj,
    SocketObj,
)

# Dict of all file object class, indexed by the stat mode key (.objmode)
FILETYPES = {obj.objmode: obj for obj in ALL_FILEOBJECT_CLASS}

# Dict pointing to the class indexed by objtype
OBJTYPES = {obj.objtype: obj for obj in ALL_FILEOBJECT_CLASS}



############################################################
#
#  OBJECT FACTORIES
#  ================
#
############################################################

def create_from_fs(name, path='', stat=None):
    ''' Create a new object from file system path and return an
        instance of the object. The object type returned is based on
        stat of the actual file system entry.'''
    fullpath = Path(path, name)
    if not stat:
        stat = os.lstat(fullpath)
    objcls = FILETYPES.get(osstat.S_IFMT(stat.st_mode))
    if not objcls:
        raise DirscanException(f"{fullpath}: Uknown file type")

    # Extra parameters
    kwargs = {}

    if objcls is LinkObj:
        kwargs['link'] = os.readlink(fullpath)

    # Don't want to start the read of any directories here. That would result
    # in a full traversal of the directory, which could take considerable time.
    # Reading the directory objects are done with the .children() function

    return objcls(name, path=path, stat=stat, **kwargs)


def create_from_fsdir(path):
    ''' Generator that produces file object instances for directory 'path' '''

    # Iterate over the directory
    with os.scandir(path) as dirit:
        for direntry in dirit:
            stat = direntry.stat(follow_symlinks=False)
            yield create_from_fs(direntry.name, path=path, stat=stat)


def create_from_data(name, path, objtype, size, mode, uid, gid, mtime, data=None):
    ''' Create a new object from the given data and return an
        instance of the object. '''

    # Get the file object class from the type
    objcls = OBJTYPES.get(objtype)
    if not objcls:
        raise DirscanException(f"Unknown object type '{objtype}'")

    # Extra parameters
    kwargs = {}

    # Do necessary post processing of the file object
    if objcls is FileObj:
        if data:
            kwargs['hashsum'] = binascii.unhexlify(data)
        elif size == 0:
            # Hashsum is normally not defined if the size is 0.
            kwargs['hashsum'] = HASHALGORITHM().digest()

    elif objcls is LinkObj:
        kwargs['link'] = data

    if osstat.S_IFMT(mode) == objcls.objmode:
        raise DirscanException(f"Object type '{objtype}' does not match mode 'o{mode:o}'")
    #debug(0, "Mode {} -> {}", mode, mode|objcls.objmode)

    # Make a fake stat element from the given meta-data
    # st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size, st_atime, st_mtime, st_ctime
    fakestat = os.stat_result((mode|objcls.objmode, None, None, None, uid, gid,
                               size, None, mtime, None))

    # Make the file object instance
    return objcls(name, path=path, stat=fakestat, **kwargs)



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
    list. The objects returned are derived types of ``DirscanObj``, such
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
        side. Otherwise the one-sided directory will be skipped from scanning/
        traversal.

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
        # Not set, default value. True for scanning, False for comparing
        traverse_oneside = len(dirs) == 1

    # Check list of dirs indeed are dirs and create initial object list to
    # start from
    base = []
    for obj in dirs:

        # If we're not handed a FileObj-instance
        if not isinstance(obj, DirscanObj):
            obj = create_from_fs(obj)

        # The object must be a directory object
        if not isinstance(obj, DirObj):
            raise NotADirectoryError()

        base.append(obj)

    # Start the queue
    queue = [(Path('.'), tuple(base))]

    # Traverse the queue
    while queue:

        # Get the next set of objects
        path, objs = queue.pop(-1)

        debug(1, ">>>>  OBJECT {}:  {}", path, objs)

        # Parse the objects, getting object metadata
        for obj, baseobj in zip(objs, base):
            try:
                # Test for exclusions
                obj.exclude_files(excludes, base=baseobj)
                if onefs:
                    obj.exclude_otherfs(base=baseobj)

            # Parsing the object failed
            except OSError as err:
                # Call the user exception callback, raise if not
                if not exception_fn or not exception_fn(err):
                    raise

        # How many objects are present?
        present = sum(not isinstance(obj, NonExistingObj) and not obj.excluded
                      for obj in objs)

        # Send back object list to caller
        yield (path, objs)

        # Create a list of unique children names seen across all objects, where
        # excluded objects are removed from parsing
        childobjs = []
        for obj in objs:
            children = {}
            try:
                # Skip the children if...

                # ...the parent is excluded
                if obj.excluded:
                    continue

                # ..the parent is the only one
                if not traverse_oneside and present == 1:
                    continue

                # Get and append the children names
                children = {obj.name: obj for obj in obj.children()}
                #debug(2, "    Children of {} is {}", obj, children)

            # Getting the children failed
            except OSError as err:
                # Call the user exception callback, raise if not
                if not exception_fn or not exception_fn(err):
                    raise

            finally:
                # Append the children collected so far
                childobjs.append(children)

        # Merge all found objects into a single list of unique, sorted, children names
        # and iterate over it
        for name in sorted(set(itertools.chain.from_iterable(childobjs)),
                           reverse=not reverse):

            # Get the child if it exists for each of the dirs being traversed
            child = tuple(
                children.get(name) or NonExistingObj(name, path=parent.fullpath)
                for parent, children in zip(objs, childobjs)
            )

            # Append the newly discovered objects to the queue
            queue.append((Path(path, name), child))

        # Close objects to conserve memory
        if close_during:
            for obj in objs:
                obj.close()
