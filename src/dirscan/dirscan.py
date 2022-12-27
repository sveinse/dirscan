'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2022 Svein Seldal
This code is licensed under MIT license (see LICENSE for details)
URL: https://github.com/sveinse/dirscan
'''
from __future__ import annotations  # for Python 3.7-3.9
from typing import (Any, Callable, Collection, Dict, Generator, List, Optional,
                    Type, Union, Tuple)

import os
import datetime
import stat as osstat
import itertools
import hashlib
import filecmp
import fnmatch
import binascii
from pathlib import Path

from typing_extensions import NotRequired, TypedDict  # for Python <3.11
from dirscan.log import debug


# Select hash algorthm to use
HASHALGORITHM = hashlib.sha256

# Number of bytes to read per round in the hash reader
HASHCHUNKSIZE = 16*4096

# Minimum difference in seconds to consider it a changed timestamp
TIME_THRESHOLD = 1


# Typings
TPath = Union[str, Path]


class DirscanDict(TypedDict):
    ''' Type to declare the contents of the dict representation of a
        DirscanObj
    '''
    objtype: str
    name: str
    path: str
    mode: int
    uid: int
    gid: int
    dev: int
    size: int
    mtime: float
    hashsum: NotRequired[str]
    link: NotRequired[str]
    children: NotRequired[Collection['DirscanDict']]  # type: ignore


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

    # Declare to help type checkers
    objtype: str
    objname: str
    objmode: int

    __slots__ = ('name', 'path', 'excluded',
                 'mode', 'uid', 'gid', 'dev', 'size', '_mtime')

    # Type definitions
    name: str
    path: TPath
    excluded: bool
    mode: int
    uid: int
    gid: int
    dev: int
    size: int
    _mtime: float

    def __init__(self, name: str, *, path: TPath='', stat: os.stat_result):

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
    def fullpath(self) -> Path:
        ''' Return the complete path of the object '''
        return Path(self.path, self.name)

    @property
    def mtime(self) -> datetime.datetime:
        ''' Return the modified timestamp of the file '''
        return datetime.datetime.fromtimestamp(self._mtime)

    def children(self) -> Tuple['DirscanObj', ...]:  # pylint: disable=no-self-use
        ''' Return iterator of sub objects. Non-directory file objects that
            does not have any children will return an empty tuple. '''
        return ()

    def close(self) -> None:
        ''' Delete any allocated objecs within this class '''

    def compare(self, other: 'DirscanObj') -> Generator[str, None, None]:
        ''' Return a list of differences '''
        if not isinstance(other, type(self)):
            yield 'type mismatch'
            return
        time_delta = self._mtime - other._mtime  # pylint: disable=protected-access
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

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path},{self.name})"

    def exclude_otherfs(self, other: 'DirscanObj') -> None:
        ''' Set excluded flag if this object resides on
            another fs than other  '''

        # Note that self.excluded will be set on NonExistingObj() since they
        # have dev = None
        if self.dev != other.dev:
            self.excluded = True

    def exclude_files(self, excludes: Collection[TPath],
                      base: 'DirscanObj') -> None:
        ''' Set excluded flag if any of the entries in exludes matches
            this object '''
        for ex in excludes:
            ex = Path(base.fullpath, ex)
            if fnmatch.fnmatch(self.fullpath, ex):  # type: ignore
                self.excluded = True
                return

    def to_dict(self) -> DirscanDict:
        ''' Return a dict representation of this class '''
        data: DirscanDict = {  # type: ignore
            k: getattr(self, k) for k in (
                # Not exactly __slots__
                'objtype', 'name', 'path', 'mode', 'uid', 'gid', 'dev', 'size',
            )}
        data['mtime'] = self._mtime
        return data


class FileObj(DirscanObj):
    ''' Regular File Object '''
    objtype = 'f'
    objname = 'file'
    objmode = osstat.S_IFREG

    __slots__ = ('_hashsum',)

    # Type definitions
    _hashsum: Optional[bytes]

    def __init__(self, name: str, *, path: TPath='', stat: os.stat_result,
                 hashsum: Optional[bytes]=None):
        super().__init__(name, path=path, stat=stat)

        # Protocol:
        #   None: Unknown value, will read from fs if self.hashsum is accessed
        #   Falsey: Unknown value, will not read from fs
        #   <*>: Stored hashsum
        self._hashsum = hashsum

    @property
    def hashsum(self) -> bytes:
        ''' Return the hashsum of the file '''

        # This is not a part of the parse() structure because it can take
        # considerable time to evaluate the hashsum, hence its done on
        # need-to have basis.

        # Only query the fs if None
        if self._hashsum is None:
            shahash = HASHALGORITHM()
            with open(self.fullpath, 'rb') as shafile:
                while True:
                    data = shafile.read(HASHCHUNKSIZE)
                    if not data:
                        break
                    shahash.update(data)
                self._hashsum = shahash.digest()

        return self._hashsum

    @property
    def hashsum_hex(self) -> str:
        ''' Return the hex hashsum of the file '''
        return binascii.hexlify(self.hashsum).decode('ascii')

    def compare(self, other: DirscanObj) -> Generator[str, None, None]:
        ''' Compare two file objects '''
        if not isinstance(other, type(self)):
            yield 'type mismatch'
            return
        yield from super().compare(other)
        # pylint: disable=protected-access
        if self.size != other.size:
            yield 'size differs'
        elif self._hashsum == b'' and other._hashsum == b'':
            # Don't compare if neither has hashsum data
            pass
        elif self._hashsum == b'' or other._hashsum == b'':
            yield 'W:cannot compare'
        elif self._hashsum or other._hashsum:
            # Does either of them have _hashsum set? If yes, make use of
            # hashsum based compare. filecmp might be more efficient, but if we
            # read from listfiles, we have to use hashsums.
            if self.hashsum != other.hashsum:
                yield 'contents differs'
        elif not filecmp.cmp(self.fullpath, other.fullpath, shallow=False):
            yield 'contents differs'

    def to_dict(self) -> DirscanDict:
        ''' Return a dict representation of this class '''
        data = super().to_dict()
        if self._hashsum is not None:
            data['hashsum'] = self.hashsum_hex
        return data


class LinkObj(DirscanObj):
    ''' Symbolic Link File Object '''
    objtype = 'l'
    objname = 'symbolic link'
    objmode = osstat.S_IFLNK

    __slots__ = ('link',)

    # Type definitions
    link: str

    def __init__(self, name: str, *, path: TPath='', stat: os.stat_result,
                 link:str=''):
        super().__init__(name, path=path, stat=stat)
        self.link = link

    def compare(self, other: 'DirscanObj') -> Generator[str, None, None]:
        ''' Compare two link objects '''
        if not isinstance(other, type(self)):
            yield 'type mismatch'
            return
        yield from super().compare(other)
        if self.link != other.link:
            yield 'link differs'

    def to_dict(self) -> DirscanDict:
        ''' Return a dict representation of this class '''
        data = super().to_dict()
        data['link'] = self.link
        return data


class DirObj(DirscanObj):
    ''' Directory File Object '''
    objtype = 'd'
    objname = 'directory'
    objmode = osstat.S_IFDIR

    __slots__ = ('_children',)

    _children: Optional[Tuple[DirscanObj, ...]]

    def __init__(self, name: str, *, path: TPath='', stat: os.stat_result,
                 children: Optional[Collection[DirscanObj]]=None):
        super().__init__(name, path=path, stat=stat)

        # Override the stat default filled in by super().__init__
        self.size = 0

        # Setting to None will read from fs. All other values won't
        self._children = children if children is None else tuple(children)

    def close(self) -> None:
        ''' Delete all used references to allow GC cleanup '''
        super().close()
        self._children = None

    def children(self) -> Tuple[DirscanObj, ...]:
        ''' Return an iterator of the sub object names '''
        if self._children is None:
            self._children = tuple(create_from_fsdir(self.fullpath))
        return self._children

    def set_children(self, children: Collection[DirscanObj]) -> None:
        ''' Set the directory children '''
        self._children = tuple(children)

    def to_dict(self) -> DirscanDict:
        ''' Return a dict representation of this class '''
        data = super().to_dict()
        data['children'] = tuple(c.to_dict() for c in self._children or {})
        return data


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

    def __init__(self, name: str, *, path: TPath=''):
        stat = os.stat_result((0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        super().__init__(name, path=path, stat=stat)


# Tuple of all real file objects. NonExistingObj is deliberately omitted
ALL_FILEOBJECT_CLASS: Tuple[Type[DirscanObj], ...] = (
    FileObj,
    DirObj,
    LinkObj,
    BlockDevObj,
    CharDevObj,
    FifoObj,
    SocketObj,
)

# Dict of all file object class, indexed by the stat mode key (.objmode)
FILETYPES = {cls.objmode: cls for cls in ALL_FILEOBJECT_CLASS}

# Dict pointing to the class indexed by objtype
OBJTYPES = {cls.objtype: cls for cls in ALL_FILEOBJECT_CLASS}



############################################################
#
#  OBJECT FACTORIES
#  ================
#
############################################################

def create_from_fs(name: str, path: TPath='',
                   stat: Optional[os.stat_result]=None,
                   ) -> DirscanObj:
    ''' Create a new object from file system path and return an
        instance of the object. The object type returned is based on
        stat of the actual file system entry.'''
    fullpath = Path(path, name)
    if not stat:
        stat = os.stat(fullpath, follow_symlinks=False)
    mode = osstat.S_IFMT(stat.st_mode)
    objcls: Optional[Type[DirscanObj]] = FILETYPES.get(mode)
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


def create_from_fsdir(path: Path) -> Generator[DirscanObj, None, None]:
    ''' Generator that produces file object instances for directory 'path' '''

    # Iterate over the directory
    # FIXME: This should possibly be done with bytes as path in order to get
    #        the filename as bytes and then do a controlled decode to str.
    with os.scandir(path) as dirit:
        for direntry in dirit:
            stat = direntry.stat(follow_symlinks=False)
            yield create_from_fs(direntry.name, path=path, stat=stat)


def create_from_dict(data: DirscanDict) -> DirscanObj:
    ''' Create a new fs object from a dict '''

    # Get the file object class from the type
    objtype = data['objtype']
    objcls: Optional[Type[DirscanObj]] = OBJTYPES.get(objtype)
    if not objcls:
        raise DirscanException(f"Unknown object type '{objtype}'")

    # Class parameters
    kwargs: Dict[str, Any] = {
        'name': data['name'],
        'path': data.get('path',''),
    }

    # Do necessary post processing of the file object
    if objcls is FileObj:
        _hashsum = data.get('hashsum')
        if _hashsum is not None:
            hashsum = binascii.unhexlify(_hashsum)
        elif data.get('size') == 0:
            # Hashsum is normally not defined if the size is 0.
            hashsum = HASHALGORITHM().digest()
        else:
            # Setting hashsum to falsey indicates that the fs should not be
            # queried to find the result
            hashsum = b''
        kwargs['hashsum'] = hashsum

    elif objcls is LinkObj:
        kwargs['link'] = data['link']  # pyright: ignore

    elif objcls is DirObj:
        if data.get('children'):
            # This will recurse all children
            kwargs['children'] = tuple(
                create_from_dict(c) for c in data['children']  # pyright: ignore
            )
        else:
            # Setting this to empty tuple prevents the class
            # from querying the fs
            kwargs['children'] = ()

    # If the mode carries object type fields, check this against the object
    objmode = osstat.S_IFMT(data.get('mode', objcls.objmode))
    if objmode and objmode != objcls.objmode:
        raise DirscanException(f"Object type '{objtype}' does not match mode "
                               f"'o{data['mode']:o}'")

    # Make a fake stat element from the given meta-data
    fakestat = os.stat_result((  # type: ignore
        data.get('mode', 0) | objcls.objmode,  # st_mode
        0,  # st_ino
        0,  # st_dev
        0,  # st_nlink
        data.get('uid', 0),  # st_uid
        data.get('gid', 0),  # st_gid
        data.get('size', 0),  # st_size
        0,  # st_atime
        data.get('mtime', 0.),  # st_mtime
        0,  # st_ctime
    ))
    kwargs['stat'] = fakestat

    # Make the file object instance
    return objcls(**kwargs)



############################################################
#
#  DIRECTORY TRAVERSER
#  ===================
#
############################################################

def walkdirs(dirs: Collection[DirscanObj],
             reverse: bool=False,
             excludes: Optional[Collection[TPath]]=None,
             onefs: bool=False,
             traverse_oneside: Optional[bool]=None,
             exception_fn: Optional[Callable[[Exception], bool]]=None,
             close_during: bool=True,
             sequential: bool=False,
             ) -> Generator[Tuple[Path, Tuple[DirscanObj, ...]], None, None]:
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

     ``ìn_tandem``
        If True, the directories will be traversed in parallel simulaneously.
        If False, each of the directories will be scanned one by one.
    '''

    if sequential:
        for obj in dirs:
            yield from walkdirs((obj,), reverse=reverse, excludes=excludes,
                                onefs=onefs, traverse_oneside=traverse_oneside,
                                exception_fn=exception_fn,
                                close_during=close_during,
                                sequential=False)
        return

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
    queue: List[Tuple[Path, Tuple[DirscanObj, ...]]] = [(Path('.'), tuple(base))]

    debug(2, "")

    # Traverse the queue
    while queue:

        # Get the next set of objects
        path, objs = queue.pop(-1)

        debug(2, ">>>>  OBJECT {}:  {}", path, objs)

        # Parse the objects, getting object metadata
        for obj, baseobj in zip(objs, base):
            try:
                # Test for exclusions
                obj.exclude_files(excludes, base=baseobj)
                if onefs:
                    obj.exclude_otherfs(baseobj)

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
                debug(4, "      Children of {} is {}", obj, children)

            # Getting the children failed
            except OSError as err:
                # Call the user exception callback, raise if not
                if not exception_fn or not exception_fn(err):
                    raise

            finally:
                # Append the children collected so far
                childobjs.append(children)

        # Merge all found objects into a single list of unique, sorted,
        # children names and iterate over it
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
