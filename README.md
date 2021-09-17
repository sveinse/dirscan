# Directory scanner

`dirscan` is a recursive directory traverser for efficiently scanning and
comparing directories. It can store scan results in *scan files* which can be
used later as input for comparing or verifying contents.

The module is written in Python 3.
The module provides `dirscan.walkdirs()` which is similar to `os.walk()`,
with the added ability to walk multiple directories in lock step simulaneously.
The tool provides both a command-line tool, as well as a Python API for use
in own projects.

Project home:

          https://github.com/sveinse/dirscan

Copyright 2010-2021, Svein Seldal <sveinse@seldal.com>


## Installation

Download `dirscan` by installing from https://pypi.org/project/dirscan

    $ pip install dirscan

Alternatively it can be built from source

    $ git clone https://github.com/sveinse/dirscan.git
    $ cd dirscan
    $ pip install .


## Command-line usage

The basic usage for the command line utility is

```
    dirscan [options] LEFT_DIR [RIGHT_DIR]
```

`dirscan` can operate in **scan mode** or **compare mode**, which is selected
by the number of directories given. `dirscan` provides a rich set of options
and `dirscan --help` provides detailed information about them.

### Scan mode

**scan mode** is used when only `LEFT_DIR` is specified. It will traverse the
directory and print the found files. `dirscan` is capable of printing the
sha256 hashsum for each of the scanned files.

`dirscan` can store the scan results in a **scan file** with the
`--output, -o` option. The scan file can be later read into `dirscan` as input
and be printed or compared with other directories or scan files. When generating
the scan file the sha256 hashsum will be generated for each of the file. This
can be used later to compare or verify any changes to the contents of the files
in a secure manner.

### Compare mode

**compare mode** is selected when both the `LEFT_DIR` and `RIGHT_DIR`
arguments are specified. It will compare the differences between **left** and
**right** and print their difference, including comparing the contents of the
files. Either of left and right arguments can be read from scan files.

`dirscan` supports customization by filtering and printing. The options
`--compare`, `--file-types`, `--ignore` can be used to filter out what
type of file or comparison result to show. Options `--format` and
`--summary` provides extensive custom format printing capabilities.


## API

`dirscan` can be used from Python by importing the module

```python
    import dirscan
```


### `dirscan.walkdirs()`

```python
    dirscan.walkdirs(dirs, reverse=False, excludes=None, onefs=False,
                     traverse_oneside=None, exception_fn=None,
                     close_during=True)
```

Generator function that recursively traverses the directories in iterator
`dirs`. It will scan a single or multile directories in tandem and return the
found files and directories in lock step.

```python
    # Scan directory and print path and file type for each entry in directory
    for path, (obj,) in dirscan.walkdirs(('path/to/dir',)):

        print(f"{path} is a {obj.objname}")
```

As it traverses the directory, it will yield tuples containing `(path, objs)`
for each file object it finds. `path` represents the common relative file path.
`objs` is a tuple of file objects from each of the `dirs` input (trees). Its
length is equal to the length of `dirs`. Each object in `objs` are instances of
`dirscan.DirscanObj`, depending on the type of the found object. E.g.
`dirscan.FileObj` and `dirscan.DirObj`.

When more than one directory is specified in `dirs`, it will scan both
directories in tandem and yeild the tuples from each of the trees in lock-step.
If a file is not present in one dir, it will yield a `dirscan.NonExistingObj`
instance instead.

```python
    # Compare directories
    for path, (left, right) in dirscan.walkdirs((left_path, right_path)):

      if isinstance(left, dirscan.NonExistingObj):
        print(f"{path}: Only in right")
      if isinstance(right, dirscan.NonExistingObj):
        print(f"{path}: Only in left")
```

**Function arguments:**
  - `dirs` -
    List of directories to walk. The elements must either be a path string
    to a physical directory or a previously loaded `DirObj` object tree.

  - `reverse` -
    Reverses the scanning order

  - `excludes` -
    List of excluded paths, relative to the common path

  - `onefs` -
    Scan file objects belonging to the same file system only

  - `traverse_onside` -
    Will walk/yield all file objects in a directory that exists on only one
    side. I.e. comparing two directories, and one directory only exists on
    side, the scanner will not enter the onesided directory unless this option
    is set. See the command-line option `--recurse`.

  - `exception_fn` -
    Exception handler callback. It has format `exception_fn(exception)`
    returning `Bool`. It will be called if any scanning exceptions occur
    during traversal. If `exception_fn()` returns `False` or is not set, an
    ordinary exception will be raised.

  - `close_during` -
    will call `obj.close()` on objects that have been yielded to the
    caller. This allows freeing up parsed objects to conserve memory. Note
    that this tears down the in-memory directory tree, making it impossible
    to reuse the object tree after `walkdirs()` is complete.


### `dirscan.is_scanfile()`

```python
    dirscan.is_scanfile(filename)
```

Function to check if the input filename is readable and contains a valid
scanfile header.


### `dirscan.read_scanfile()`

```python
    dirscan.read_scanfile(filename, root=None)
```

Read the given scanfile `filename` and return the root `dirscan.DirObj()`
object. The `root` argument specifies the sub-dir within the scanfile which
shall be returned as the root object. It has to point to a directory object.


### `dirscan.create_from_fs()`

```python
    dirscan.create_from_fs(name, path='', stat=None)
```

Create a new file system object instance (inherited from `dirscan.DirscanObj`)
by querying the filesystem by the path given by `path/name`. If `stat` is
None, the function will fetch the information itself from the filesystem.

If querying a directory, this function will not automatically traverse the
filesystem. This will happen when `obj.children()` is called. Use the
`obj.traverse()` method to traverse the whole tree into memory.


### `dirscan.create_from_dict()`

```python
    dirscan.create_from_dict(data)
```

Create a new file system object instance (inherited from `dirscan.DirscanObj`)
from the dict `data`. This function is the oposite of `obj.to_dict()`


### `class dirscan.DirscanObj()`

This is the base class for all file objects used by dirscan. This class
is inherited into specific file-object types:

  * `FileObj()` - Files
  * `LinkObj()` - (Symbolic) links
  * `DirObj()` - Directories
  * `BlockDevObj()` - Block devices files
  * `CharDevObj()` - Character device files
  * `SocketObj()` - Socket files
  * `FifoObj()` - Pipe files
  * `NonExistingObj()` - Missing file object. See `walkdirs()`.

This base class should not be used directly.

**Attributes**
  - `obj.name`
    Bare filename of the file path to the object

  - `obj.path`
    Directory part of the file path to the object

  - `obj.fullpath`
    Full filename path of the object. Same as `pathlib.Path(obj.path, obj.name)`

  - `obj.objtype` (deprecated)
    One character object type
      * `f` - File
      * `l` - Link
      * `d` - Directory
      * `b` - Block device
      * `c` - Character device
      * `p` - Fifo
      * `s` - Socket
      * `-` - Non existing file

  - `obj.mode`
    File mode, `stat.st_mode`, without filetype fields

  - `obj.uid`
    File user ID, `stat.st_uid`

  - `obj.gid`
    File group ID, `stat.st_gid`

  - `obj.size`
    File size, `stat.st_size`

  - `obj.dev`
    File system device, `stat.st_dev`

  - `obj.mtime`
    File modify timestamp, `datetime.fromtimestamp(stat.st_mtime)`

  - `obj.hashsum` and `obj.hashsum_hex` (FileObj only)
    Link destination, `os.readlink()`

  - `obj.link` (LinkObj only)
    Link destination, `os.readlink()`

  - `obj.excluded`
    If set the file has been excluded by the exclude filters. This attribute
    will not be serialized with `obj.to_dict()`.


**Methods**

  - `obj.__init__(self, name, path='', stat=None)`
    Create a new file object.

  - `obj.compare(self, other)`
    A generator that compares this object with `other`. It yields a list of
    differences between `self` and `other`. An empty list is returned if the
    objects are equal. For files, compare will try to compare the contents of
    the files using `filecmp.cmp()` or by comparing the sha256 sum.

  - `obj.children(self)`
    Return an iterator of this object's children names.

  - `obj.set_children(self, children)` (DirObj only)
    Set the children for a directory. Useful when building the tree.

  - `obj.close(self)`
    Close this object. It breaks any links to any other objects to help up
    garbage collection.

  - `obj.to_dict(self)`
    Serialize and return a dict representation of the object. In DirObj it will
    recurse and return the full file tree.

  - `obj.traverse(self)` (DirObj only)
    Traverse through the directory tree. This will read the full tree into
    memory. This function is necessary when creating a `DirObj` instance with
    `create_from_fs()` to traverse the whole file system tree into children
    objects.
