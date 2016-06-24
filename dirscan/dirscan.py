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

import os
import datetime
import stat
import itertools
import hashlib
import errno


# Select hash algorthm to use
hashalgorithm = hashlib.sha256


class DirscanException(Exception):
    pass



############################################################
#
#  FILE CLASS OBJECTS
#  ==================
#
############################################################

class BaseObj(object):
    ''' File Objects Base Class '''
    parsed = False

    # Standard file entries
    stat = None
    mode = None
    uid = None
    gid = None
    size = None
    mtime = None


    def __init__(self,path,name,stat=None):
        self.path = path
        self.name = name
        self.stat = stat

        fp = os.path.join(path,name)
        #if fp.endswith('/.'):
        #    fp=fp[:-2]
        self.fullpath = fp


    def parse(self,done=True):
        ''' Parse the object. Get file stat info. '''
        if self.parsed: return
        if not self.stat:
            self.stat = os.lstat(self.fullpath)
        self.mode = self.stat.st_mode
        self.uid = self.stat.st_uid
        self.gid = self.stat.st_gid
        self.size = self.stat.st_size
        self.mtime = datetime.datetime.fromtimestamp(self.stat.st_mtime)
        self.parsed = done


    def children(self):
        ''' Return hash of sub objects. Non-directory file objects that does not have any
            children will return an empty dict. '''
        return {}


    def close(self):
        ''' Delete any allocated objecs within this class '''
        self.parsed = False


    def compare(self,other,s=None):
        ''' Return a list of differences '''
        if s is None:
            s=[]
        if type(other) is not type(self):
            return ['Type mismatch']
        if self.uid != other.uid:
            s.append('UID differs')
        if self.gid != other.gid:
            s.append('GID differs')
        if self.mode != other.mode:
            s.append('Perm differs')
        if self.mtime > other.mtime:
            s.append('newer')
        elif self.mtime < other.mtime:
            s.append('older')
        return s


    #def get(self,k,v):
    #    return v


    #def __repr__(self):
    #    return "%s:%s:%s:%s" %(self.objtype,self.fullpath,self.path,self.name)


    #def data(self):
    #    return None



class FileObj(BaseObj):
    ''' Regular File Object '''
    objtype = 'f'
    objname = 'file'

    _hashsum = None


    def hashsum(self):
        ''' Return the hashsum of the file '''
        if self._hashsum: return self._hashsum

        m = hashalgorithm()
        with open(self.fullpath,'rb') as f:
            while True:
                d = f.read(16*1024*1024)
                if not d:
                    break
                m.update(d)
            self._hashsum = m.hexdigest()
        return self._hashsum


    def compare(self,other,s=None):
        ''' Compare two file objects '''
        if s is None:
            s=[]
        if self.size != other.size:
            s.append('size differs')
        elif self._hashsum or other._hashsum:
            # Does either of them have _hashsum set? If yes, make use of hashsum based compare.
            # filecmp might be more efficient, but if we read from listfiles, we have to use hashsums.
            if self.hashsum() != other.hashsum():
                s.append('contents differs')
        elif not filecmp.cmp(self.fullpath,other.fullpath,shallow=False):
            s.append('contents differs')
        return BaseObj.compare(self,other,s)


    #def data(self):
    #    return self.hashsum()



class LinkObj(BaseObj):
    ''' Symbolic Link File Object '''
    objtype = 'l'
    objname = 'symbolic link'
    
    _link = None

    def link(self):
        if self._link is not None: return self._link

        self._link = os.readlink(self.fullpath)
        return self._link

    #def parse(self):
    #    # Execute super
    #    if self.parsed: return
    #    BaseObj.parse(self,done=False)

    #    # Read the contents of the link
    #    self.linkdst = os.readlink(self.fullpath)
    #    self.parsed = True


    def compare(self,other,s=None):
        ''' Compare two link objects '''
        if s is None:
            s=[]
        if self.link != other.link:
            s.append('link differs')
        return BaseObj.compare(self,other,s)


    #def data(self):
    #    return self.link



class DirObj(BaseObj,dict):
    ''' Directory File Object '''
    objtype = 'd'
    objname = 'directory'


    def parse(self):
        ''' Parse the directory tree and add children to self '''
        # Call super, but we're not done (i.e. False)
        if self.parsed: return
        BaseObj.parse(self,done=False)
        self.size = None

        # Try to get list of sub directories and make new sub object
        for name in os.listdir(self.fullpath):
            self[name] = newFromFS(self.fullpath,name)
        self.parsed = True


    def close(self):
        ''' Delete all used references to allow GC cleanup '''
        self.clear()
        self.parsed = False


    def children(self):
        ''' Return a dict of the sub objects '''
        c = { }
        c.update(self)
        return c


    def get(self,k,v):
        return dict.get(self,k,v)



class SpecialObj(BaseObj):
    ''' Device (block or char) device '''
    objtype = 's'
    objname = 'special file'


    def __init__(self,path,name,stat=None,dtype='s'):
        BaseObj.__init__(self,path,name,stat)
        self.objtype=dtype

        # The known special device types
        if dtype=='b':
            self.objname = 'block device file'
        elif dtype=='c':
            self.objname = 'char device file'
        elif dtype=='p':
            self.objname = 'fifo file'
        elif dtype=='s':
            self.objname = 'socket file'


    def parse(self):
        # Execute super
        if self.parsed: return
        BaseObj.parse(self,done=False)
        self.size = None

        # Read the contents of the device
        self.parsed = True


    def compare(self,other,s=None):
        ''' Compare two link objects '''
        if s is None:
            s=[]
        if self.objtype != other.objtype:
            s.append('device type differs')
        return BaseObj.compare(self,other,s)



class NonExistingObj(BaseObj):
    ''' NonExisting File Object. Evaluates to false for everything. Used by the
        walk2dirs() when parsing two trees in parallell to indicate a
        non-existing file object. '''
    objtype = '-'
    objname = 'missing file'

    def parse(self):
        self.parsed=False



############################################################
#
#  DIRECTORY TRAVERSER
#  ===================
#
############################################################

def newFromFS(path, name):
    ''' Create a new object from file system path and return an
        instance of the object. The object type returned is based on
        stat of the actual file system entry.'''
    fullpath = os.path.join(path,name)
    s = os.lstat(fullpath)
    o = None
    t = s.st_mode
    if stat.S_ISREG(t):
        o = FileObj(path,name,s)
    elif stat.S_ISDIR(t):
        o = DirObj(path,name,s)
    elif stat.S_ISLNK(t):
        o = LinkObj(path,name,s)
    elif stat.S_ISBLK(t):
        o = SpecialObj(path,name,s,'b')
    elif stat.S_ISCHR(t):
        o = SpecialObj(path,name,s,'c')
    elif stat.S_ISFIFO(t):
        o = SpecialObj(path,name,s,'p')
    elif stat.S_ISSOCK(t):
        o = SpecialObj(path,name,s,'s')
    else:
        raise DirscanException("%s: Uknown file type" %(fullpath))
    return o


def newFromData(path, name, objtype, size, mode, uid, gid, mtime, data=None):
    ''' Create a new object from the given data and return an
        instance of the object. '''
    o = None
    if objtype == 'f':
        o = FileObj(path, name)
        o._hashsum = data
    elif objtype == 'l':
        o = LinkObj(path, name)
        o.link = data
    elif objtype == 'd':
        o = DirObj(path, name)
    elif objtype == 'b' or objtype == 'c' or objtype == 'p' or objtype == 's':
        o = SpecialObj(path, name, dtype=objtype)
    o.mode = mode
    o.uid = uid
    o.gid = gid
    o.size = size
    o.mtime = mtime
    o.parsed = True
    return o



############################################################
#
#  DIRECTORY TRAVERSER
#  ===================
#
############################################################


def walkdirs(dirs,reverse=False,topdown=True):

    # Check list of dirs indeed are dirs and create initial object list
    objs = [ ]
    for d in dirs:
        # If d is file, then we read it as a listfile.
        #if os.path.isfile(d):
        #    o = readfilelist(d)
        if os.path.isdir(d):
            o = DirObj('',d)
        else:
            raise OSError(errno.ENOENT,os.strerror(errno.ENOENT),d)
        o.hasparent = True
        objs.append(o)


    # popno controls which object is taken next from the objects list. -1 is the last, while 0 is the first.
    # sortrev controls the order of the list going into the object's list.  Since the loop adds to the end
    # of the objects list, the default parsing (that is reverse=False and topdown=True) is to pick the last
    # object with popno=-1 and populate the object list in reversed order (for a to be picked first)
    if reverse==True and topdown==True:
        popno=-1
        sortrev=False
    elif reverse==False and topdown==False:
        popno=0
        sortrev=False
    elif reverse==True and topdown==False:
        popno=0
        sortrev=True
    else: # reverse==False and topdown==True
        popno=-1
        sortrev=True


    objects = [ objs ]
    basepath = dirs[0]

    while len(objects):

        # Get the next set of objects
        objs = objects.pop(popno)

        # Parse the objects (which investigates the objects and and creates children objects if present)
        for o in objs:
            try:
                o.parse()
                o.parserr = None
            except OSError as e:
                o.parserr = e

        # Path to give
        path = objs[0].fullpath.replace(basepath,'',1)
        if len(path)==0: path='.'
        if path.startswith('/'): path = path.replace('/','',1)

        # Send back object list to caller
        yield (path,objs)

        # Create a list of unique children names seen across all objects
        names = sorted(set(itertools.chain.from_iterable(o.children().keys() for o in objs)),reverse=sortrev)

        # Iterate over all unique children names
        children = [ ]
        for n in names:

            # Create a list of children object with name n
            child = [ o.get(n, NonExistingObj(os.path.join(o.path,o.name),n)) for o in objs ]

            # Set the hasparent if the parent object is a real file object
            for c,o in zip(child,objs):
                c.hasparent = type(o) is not NonExistingObj

            # Append it to the processing list
            children.append( child )

        # Close objects to conserve memory
        for o in objs:
            o.close()

        # Append the newly discovered objects to the stack
        objects.extend(children)
