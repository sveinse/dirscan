#################
Directory scanner
#################

``dirscan`` is a recursive directory traverser for scanning and comparing
directories. It can store scan results in *scan files* which can be used
later for comparing or verifying contents.

The module is written in Python and supports Python 2.7 and Python 3.6. The
module provides ``dirscan.walkdirs()`` which is similar to ``os.walk()``,
with the added ability to walk multiple directories simulaneously.

Home for the project:

          https://github.com/sveinse/dirscan

Copyright 2010-2018, Svein Seldal <sveinse@seldal.com>


Installation
============

Download ``dirscan`` by installing from https://pypi.org/project/dirscan ::

  pip install dirscan

Alternatively it can be built from source ::

  git clone https://github.com/sveinse/dirscan.git
  cd dirscan
  pip install .


Usage
=====
The basic usage for the command line utility is::

  dirscan [options] LEFT_DIR [RIGHT_DIR]

``dirscan`` can operate in *scan mode* or *compare mode*, which is selected
by the number of directories given. ``dirscan`` provides a rich set of options
and ``dirscan --help`` provides detailed information about them.

**scan mode** is used when only the ``LEFT_DIR`` is given as input to
``dirscan``. It will traverse the directory and print the found files.
``dirscan`` is capable of calculating the sha256 hashsum for each of the
scanned files.

``dirscan`` can store the scan results in a *scan file* with the
``--output, -o`` option. The scan file can be later read into ``dirscan`` for
printing or comparison with other directories or scan files. The scan file will
evaluate the sha256 hashsum for each of the files. This can be used later to
compare or verify any changes to the contents of the files.

**compare mode** is selected when both the ``LEFT_DIR`` and ``RIGHT_DIR``
arguments are given. It will compare the differences between **left** and
**right** and print their difference, including comparing the contents of the
files. Either left or right or both arguments can be read from scan files.

``dirscan`` supports customization by filtering and printing. The options
``--compare``, ``--file-types``, ``--ignore`` can be used to filter out what
type of file or comparison result to show. Options ``--format`` and
``--summary`` provides extensive custom format printing capabilities.


API
===

``dirscan`` can be used from Python by importing the module::

   import dirscan


``dirscan.walkdirs()``
----------------------
::

    dirscan.walkdirs(dirs, reverse=False, excludes=None, onefs=False,
                     traverse_oneside=None, exception_fn=None,
                     close_during=True)

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


``class dirscan.BaseObj()``
---------------------------
This is the base class for all file objects used by dirscan. This class
is inherited into specific file-object types:

  * ``FileObj()`` - Files
  * ``LinkObj()`` - (Symbolic) links
  * ``DirObj()`` - Directories
  * ``SpecialObj()`` - Block devices, character devices, fifos and sockets
  * ``NonExistingObj()`` - Missing file object. See ``walkdirs()``.


**Attributes**
  ``obj.name``
    Filename of the object

  ``obj.path``
    Directory path of the object

  ``obj.fullpath``
    Full path of the object. Same as ``os.path.join(obj.path, obj.name)``

  ``obj.objtype``
    One character object type
      * ``f`` - File
      * ``l`` - Link
      * ``d`` - Directory
      * ``b`` - Block device
      * ``c`` - Character device
      * ``p`` - Fifo
      * ``s`` - Socket
      * ``-`` - Non existing file

  ``obj.objname``
    Text string of the object type for printing

  ``obj.treeid``
    Optional ID to identify which tree this object belongs to

  ``obj.parsed``
    If set the following data below can be read

  ``obj.mode``
    File mode, ``stat.st_mode``

  ``obj.uid``
    File user ID, ``stat.st_uid``

  ``obj.gid``
    File group ID, ``stat.st_gid``

  ``obj.size`` (FileObj only)
    File size, ``stat.st_size``

  ``obj.dev``
    File system device, ``stat.st_dev``

  ``obj.mtime``
    File modify timestamp, ``datetime.fromtimestamp(stat.st_mtime)``

  ``obj.link`` (LinkObj only)
    Link destination, ``os.readlink()``


**Methods**
  ``obj.__init__(self, name, path='', stat=None, treeid=None)``
    Create a new file object.

  ``obj.parse(self, done=True)``
    Read the file object meta-data parameters from the file-system
    and label the object as parsed.

  ``obj.compare(self, other, s=None)``
    Compare this object with ``other``. It returns a list of differences
    between the objects. An empty list is returned if the objects are equal.
    For files, compare will try to compare the contents of the files using
    ``filecmp.cmp()`` or by comparing the sha256 sum.

  ``obj.children(self)``
    Return a tuple of this object's children names.

  ``obj.get(self, child, nochild=None)``
    Return child object ``child``. If ``child`` does not exits, return
    ``nochild``

  ``obj.add_child(self, child)`` (DirObj only)
    Add a new child to the current directory object.

  ``obj.hashsum(self)``  (FileObj only)
    Return the file sha256 hashsum for the object. It will read the file
    once and cache the results for later invocations.

  ``obj.close(self)``
    Close this object. It cleans up the list of children.
