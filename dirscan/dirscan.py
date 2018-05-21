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


# Select hash algorthm to use
HASHALGORITHM = hashlib.sha256


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
    parsed = False
    excluded = False
    objname = 'Base'

    # Standard file entries
    stat = None
    mode = None
    uid = None
    gid = None
    size = None
    dev = None
    mtime = None


    def __init__(self, path, name, stat=None):
        self.path = path
        self.name = name
        self.stat = stat

        fullpath = os.path.join(path, name)
        self.fullpath = fullpath


    def parse(self, done=True):
        ''' Parse the object. Get file stat info. '''
        if self.parsed:
            return
        if not self.stat:
            self.stat = os.lstat(self.fullpath)
        self.mode = self.stat.st_mode
        self.uid = self.stat.st_uid
        self.gid = self.stat.st_gid
        self.size = self.stat.st_size
        self.dev = self.stat.st_dev
        self.mtime = datetime.datetime.fromtimestamp(self.stat.st_mtime)
        self.parsed = done


    def children(self):
        ''' Return hash of sub objects. Non-directory file objects that does not
            have any children will return an empty dict. '''
        return {}


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
    def get(self, k, v):
        return v


    def __repr__(self):
        return "%s('%s')" %(type(self).__name__, self.fullpath)


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
                d = f.read(16*1024*1024)
                if not d:
                    break
                m.update(d)
            self.hashsum_cache = m.hexdigest()
        return self.hashsum_cache


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
        if self.parsed: return
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


    def __init__(self, path, name, stat=None):
        BaseObj.__init__(self, path, name, stat)
        self.dir = {}
        self.dir_parsed = False


    def parse(self, done=True):
        ''' Parse the directory tree and add children to self '''
        # Call super, but we're not done (i.e. False)
        if self.parsed: return
        BaseObj.parse(self, done=False)
        self.size = None

        self.parsed = True


    def close(self):
        ''' Delete all used references to allow GC cleanup '''
        self.dir.clear()
        self.dir_parsed = False
        BaseObj.close(self)


    def children(self):
        ''' Return a dict of the sub objects '''
        if not self.dir_parsed:

            # Try to get list of sub directories and make new sub object
            for name in os.listdir(self.fullpath):
                self.dir[name] = create_from_fs(self.fullpath, name)

            self.dir_parsed = True

        return self.dir.copy()


    def get(self, k, v):
        return self.dir.get(k, v)


    def set_child(self, child):
        self.dir[child.name] = child



class SpecialObj(BaseObj):
    ''' Device (block or char) device '''
    objtype = 's'
    objname = 'special file'


    def __init__(self, path, name, stat=None, dtype='s'):
        BaseObj.__init__(self, path, name, stat)
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


    def parse(self, done=True):
        # Execute super
        if self.parsed: return
        BaseObj.parse(self, done=False)
        self.size = None

        # Read the contents of the device
        self.parsed = True


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
        self.parsed = False



############################################################
#
#  OBJECT FACTORIES
#  ================
#
############################################################

def create_from_fs(path, name):
    ''' Create a new object from file system path and return an
        instance of the object. The object type returned is based on
        stat of the actual file system entry.'''
    fullpath = os.path.join(path, name)
    s = os.lstat(fullpath)
    o = None
    t = s.st_mode
    if fstat.S_ISREG(t):
        o = FileObj(path, name, s)
    elif fstat.S_ISDIR(t):
        o = DirObj(path, name, s)
    elif fstat.S_ISLNK(t):
        o = LinkObj(path, name, s)
    elif fstat.S_ISBLK(t):
        o = SpecialObj(path, name, s, 'b')
    elif fstat.S_ISCHR(t):
        o = SpecialObj(path, name, s, 'c')
    elif fstat.S_ISFIFO(t):
        o = SpecialObj(path, name, s, 'p')
    elif fstat.S_ISSOCK(t):
        o = SpecialObj(path, name, s, 's')
    else:
        raise DirscanException("%s: Uknown file type" %(fullpath))
    return o



def create_from_data(path, name, objtype, size, mode, uid, gid, mtime, data=None):
    ''' Create a new object from the given data and return an
        instance of the object. '''
    o = None

    if objtype == 'f':
        o = FileObj(path, name)
        o.hashsum_cache = data
        o.size = size

        # Hashsum is normally not defined if the size is 0.
        if not data and size == 0:
            m = HASHALGORITHM()
            o.hashsum_cache = m.hexdigest()

    elif objtype == 'l':
        o = LinkObj(path, name)
        o.link = data
        o.size = size

    elif objtype == 'd':
        o = DirObj(path, name)
        o.dir_parsed = True

    elif objtype == 'b' or objtype == 'c' or objtype == 'p' or objtype == 's':
        o = SpecialObj(path, name, dtype=objtype)

    # The common fields
    o.mode = mode
    o.uid = uid
    o.gid = gid
    o.mtime = mtime

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
             traverse_oneside=None, exception_fn=None):
    ''' Generator function that traverses the directories in list/tuple dirs
        simultaneously in paralell. This function is useful for scanning a file
        system, and for comparing two or more directories.

        As it walks down the directories, for each file object it finds it will
        it will yield a tuple containing (path, objs). path represents the
        common file path. objs is a tuple of objects representing the found
        file/directory-object found in the directory tree from the dirs list.
        The entries in objs represents the file objects, such as FileObj,
        DirObj, all derived from the BaseObj class. If a file is only present
        in one of the trees, the object returned in the other tree(s) where
        the file isn't present, will be returned as NonExistingObj() object.
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
            o = DirObj('', d)
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

    baserepl = './' if base[0].name.startswith('/') else '.'

    # Start the queue
    queue = [tuple(base)]

    # Traverse the queue
    while queue:

        # Get the next set of objects
        objs = queue.pop(-1)

        # Relative path: Gives './', './a', './b'
        path = objs[0].fullpath.replace(base[0].name, baserepl, 1)
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
                subobjs.append(o.children().keys())

            # Getting the children failed
            except OSError as err:
                # Call the user exception callback, raise if not
                if not exception_fn or not exception_fn(err):
                    raise

        # Merge all subobjects into a single list of unique, sorted, children names
        children = []
        for name in sorted(set(itertools.chain.from_iterable(subobjs)), reverse=not reverse):

            # Create a list of children objects for that name
            child = [o.get(name, NonExistingObj(o.fullpath, name)) for o in objs]

            # Append it to the processing list
            children.append(tuple(child))

        # Close objects to conserve memory
        for o in objs:
            o.close()

        # Append the newly discovered objects to the queue
        queue.extend(children)
