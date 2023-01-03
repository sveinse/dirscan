''' Dirscan - directory objects '''
#
# Copyright (C) 2010-2023 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

from __future__ import annotations  # for Python 3.7-3.9
from typing import (Any, Collection, Dict, Generator, Optional,
                    Type, Union, Tuple)

import os
import datetime
import stat as osstat
import hashlib
import filecmp
import fnmatch
import binascii
from pathlib import Path

from typing_extensions import NotRequired, TypedDict  # for Python <3.11

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
    '''
    Base class for directory scan file objects, and it provides the common
    functionality of the dirscan file objects. This class shouldn't be
    used directly, but rather the derived classes :py:class:`DirObj`,
    :py:class:`FileObj`, :py:class:`LinkObj`, :py:class:`BlockDevObj`,
    :py:class:`CharDevObj`, :py:class:`FifoObj`, :py:class:`SocketObj`.
    These derived classes represents the different file types that can be
    encounted in a file system. :py:class:`NonexistingObj` represents an
    object that doesn't exist and is used when comparing multiple directories
    and a file is missing from one side.
    '''

    # Declare to help type checkers
    objtype: str
    objname: str
    objmode: int

    __slots__ = ('name', 'path', 'excluded',
                 'mode', 'uid', 'gid', 'dev', 'size', '_mtime')

    # Type definitions
    name: str
    ''' Object filename without preceding path. It can be empty when its
        the top-level object.
    '''

    path: TPath
    ''' Object path, excluding its name. '''

    excluded: bool
    ''' Flag indicating that the object has been excluded '''

    mode: int
    ''' Mode bits '''

    uid: int
    ''' User ID of the owner '''

    gid: int
    ''' Group ID of the owner '''

    dev: int
    ''' Device inode '''

    size: int
    ''' Size in bytes '''

    _mtime: float

    def __init__(self, name: str, *, path: TPath='', stat: os.stat_result):
        '''
        Args:
            name: Name of file object, without preceing path
            path: Path of the file object excluding the name of the object
            stat: The stat information to copy into the object
        '''

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
        '''
        Returns the full path of the object, i.e. the concatenation of path and
        name
        '''
        return Path(self.path, self.name)

    @property
    def mtime(self) -> datetime.datetime:
        '''
        Returns the last modified timestamp of the object
        '''
        return datetime.datetime.fromtimestamp(self._mtime)

    def support_children(self) -> bool:
        '''
        Returns:
            Boolean if this object supports children objects
        '''
        return False

    def children(self) -> Tuple['DirscanObj', ...]:  # pylint: disable=no-self-use
        '''
        Returns:
            A tuple containing the children of this object. It will return
            an empty tuple even if the object doesn't support children.
        '''
        return ()

    def close(self) -> None:
        ''' Delete any allocated objecs used in this class to allow GC cleanup
        when parsing larger directory trees. It will unset any references to
        its children. Please note that once this function has been called,
        :py:meth:`DirscanObj.children()` will return an empty list of children.
        '''

    def compare(self, other: 'DirscanObj') -> Generator[str, None, None]:
        ''' Generator that yields the differences between this and ``other``.

        Args:
            other: Object to compare with
        Returns:
            A generator that indicates differences between the object
        '''
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

    def set_exclude(self, excludes: Collection[TPath],
                    base: 'DirscanObj',
                    onefs: bool=False,
                    ) -> None:
        '''
        Set excluded flag if any of the entries in exludes matches
        this object or if it resides on another file system when onefs is
        True.

        Args:
            excludes: Collection of paths to exclude. If this object matches
                any in the excludes list, the excluded flag will be set. Each
                path can support wild-cards according to the
                ``fnmatch.fnmatch()`` function.
            base: Top-level base object for this tree. This is used to determine
                the path to compare against
            onefs: If set, the exclude flag will be set.
        '''
        for ex in excludes:
            ex = Path(base.fullpath, ex)
            if fnmatch.fnmatch(self.fullpath, ex):  # type: ignore
                self.excluded = True
                return

        # If set, exclude if this object resides on another fs than the base
        if onefs and self.dev != base.dev:
            self.excluded = True

    def to_dict(self) -> DirscanDict:
        '''
        Returns:
            Serialization of this object into a dict. The dict can
            later be input to :py:func:`create_from_dict()` to recreate this
            object.
        '''
        data: DirscanDict = {  # type: ignore
            k: getattr(self, k) for k in (
                # Not exactly __slots__
                'objtype', 'name', 'path', 'mode', 'uid', 'gid', 'dev', 'size',
            )}
        data['mtime'] = self._mtime
        return data


class FileObj(DirscanObj):
    ''' Regular file object.
        Derived from :py:class:`DirscanObj` and it inherits attributes
        and methods.
    '''
    objtype = 'f'
    objname = 'file'
    objmode = osstat.S_IFREG

    __slots__ = ('_hashsum',)

    # Type definitions
    _hashsum: Optional[bytes]

    def __init__(self, name: str, *, path: TPath='', stat: os.stat_result,
                 hashsum: Optional[bytes]=None):
        '''
        Args:
            name: Name of file object, without preceing path
            path: Path of the file object excluding the name of the object
            stat: The stat information to copy into the object
            hashsum: Optional cached hashsum to initalize with. If default
                ``None``, the hashsum will be read from the file system.
        '''
        super().__init__(name, path=path, stat=stat)

        # Protocol:
        #   None: Unknown value, will read from fs if self.hashsum is accessed
        #   Falsey: Unknown value, will not read from fs
        #   <*>: Stored hashsum
        self._hashsum = hashsum

    @property
    def hashsum(self) -> bytes:
        '''
        Returns the hashsum of the file. If no data exists, an empty ``''``
        bytes sequence is returned.
        '''

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
        data = super().to_dict()
        if self._hashsum is not None:
            data['hashsum'] = self.hashsum_hex
        return data


class LinkObj(DirscanObj):
    ''' Symbolic link file object.
        Derived from :py:class:`DirscanObj` and it inherits attributes
        and methods.
    '''
    objtype = 'l'
    objname = 'symbolic link'
    objmode = osstat.S_IFLNK

    __slots__ = ('link',)

    # Type definitions
    link: str
    ''' Link destination '''

    def __init__(self, name: str, *, path: TPath='', stat: os.stat_result,
                 link:str=''):
        '''
        Args:
            name: Name of file object, without preceing path
            path: Path of the file object excluding the name of the object
            stat: The stat information to copy into the object
            link: Link destination
        '''
        super().__init__(name, path=path, stat=stat)
        self.link = link

    def compare(self, other: 'DirscanObj') -> Generator[str, None, None]:
        if not isinstance(other, type(self)):
            yield 'type mismatch'
            return
        yield from super().compare(other)
        if self.link != other.link:
            yield 'link differs'

    def to_dict(self) -> DirscanDict:
        data = super().to_dict()
        data['link'] = self.link
        return data


class DirObj(DirscanObj):
    ''' Directory file object.
        Derived from :py:class:`DirscanObj` and it inherits attributes
        and methods.
    '''
    objtype = 'd'
    objname = 'directory'
    objmode = osstat.S_IFDIR

    __slots__ = ('_children',)

    _children: Optional[Tuple[DirscanObj, ...]]

    def __init__(self, name: str, *, path: TPath='', stat: os.stat_result,
                 children: Optional[Collection[DirscanObj]]=None):
        '''
        Args:
            name: Name of file object
            path: Path of the file object (excluding the name itself)
            stat: The stat information to copy into the object
            children: Optional list children of this object. If ``None``,
                the file system will be read when children() is called.
        '''
        super().__init__(name, path=path, stat=stat)

        # Override the stat default filled in by super().__init__
        self.size = 0

        # Setting to None will read from fs. All other values won't
        self._children = children if children is None else tuple(children)

    def close(self) -> None:
        # Don't traverse into children and close them, because that will
        # interfer with the close option of walkdirs()
        self._children = ()
        super().close()

    def support_children(self) -> bool:
        return True

    def children(self) -> Tuple[DirscanObj, ...]:
        '''
        Returns:
            A tuple containing the children of this object. If the list of
            children is unset, the function will read the list of children
            from the file system. Subsequent calls will returned the cached
            list of children.
        '''
        if self._children is None:
            self._children = tuple(create_from_fsdir(self.fullpath))
        return self._children

    def set_children(self, children: Collection[DirscanObj]) -> None:
        ''' Set the children of this object

        Args:
            children: A collection of children
        '''
        self._children = tuple(children)

    def to_dict(self) -> DirscanDict:
        data = super().to_dict()
        data['children'] = tuple(c.to_dict() for c in self._children or {})
        return data


class BlockDevObj(DirscanObj):
    ''' Block device object.
        No info is stored from the block device in this object.
        Derived from :py:class:`DirscanObj` and it inherits attributes
        and methods.
    '''
    objtype = 'b'
    objname = 'block device'
    objmode = osstat.S_IFBLK


class CharDevObj(DirscanObj):
    ''' Charater device object.
        No info is stored from the char device in this object.
        Derived from :py:class:`DirscanObj` and it inherits attributes
        and methods.
    '''
    objtype = 'c'
    objname = 'char device'
    objmode = osstat.S_IFCHR


class FifoObj(DirscanObj):
    ''' Fifo file object.
        No info is stored about the fifo in this object.
        Derived from :py:class:`DirscanObj` and it inherits attributes
        and methods.
    '''
    objtype = 'p'
    objname = 'fifo'
    objmode = osstat.S_IFIFO


class SocketObj(DirscanObj):
    ''' Socket file object.
        No info is stored about the socket object.
        Derived from :py:class:`DirscanObj` and it inherits attributes
        and methods.
    '''
    objtype = 's'
    objname = 'socket'
    objmode = osstat.S_IFSOCK


class NonExistingObj(DirscanObj):
    ''' NonExisting File Object. Used by :py:func:`walkdirs()` when parsing
        multiple trees in parallell to indicate a non-existing file object in
        one or more of the trees.
    '''
    objtype = '-'
    objname = 'missing file'

    def __init__(self, name: str, *, path: TPath=''):
        '''
        Args:
            name: Name of file object
            path: Path of the file object (excluding the name itself)
        '''
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

def create_from_fs(name: TPath,
                   path: TPath='',
                   stat: Optional[os.stat_result]=None,
                   ) -> DirscanObj:
    '''
    Factory for creating a new :py:class:`DirscanObj`-like object read from the
    file system. The object type returned is based on the type of the actual
    file system entry.

    Args:
        name: Name of the file object
        path: Path of the file object (excluding the name itself)
        stat: Optional cached stat value for the file. If unset, the stat value
            will be read from the file system
    Returns:
        A :py:class:`DirscanObj`-derived object instance representing the file
        in the file system. The type of the object depends on the type of file.
        See :py:class:`FileObj`, :py:class:`DirObj`, :py:class:`LinkObj` as the
        most common types.
    '''
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

    return objcls(str(name), path=path, stat=stat, **kwargs)


def create_from_fsdir(path: TPath) -> Generator[DirscanObj, None, None]:
    ''' Generator that produces file object instances for directory 'path' '''

    # Iterate over the directory
    # FIXME: This should possibly be done with bytes as path in order to get
    #        the filename as bytes and then do a controlled decode to str.
    with os.scandir(path) as dirit:
        for direntry in dirit:
            stat = direntry.stat(follow_symlinks=False)
            yield create_from_fs(direntry.name, path=path, stat=stat)


def create_from_dict(data: DirscanDict) -> DirscanObj:
    '''
    Create a new :py:class:`DirscanObj`-like instance from a dict. This function
    is the inverse of :py:meth:`DirscanObj.to_dict()`.

    Args:
        data: Dict-like object representing the data contents of a
            :py:class:`DirscanObj`-like object.

    Returns:
        A :py:class:`DirscanObj`-derived object instance. The type of object
        is determined by the dict member ``objtype``.
    '''

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
