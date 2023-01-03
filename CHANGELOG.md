# Changelog

## v0.11

* Added new features:
   * Finding duplicate files (--duplicates)
   * Tracking renamed files when comparing (--shadiff)
   * Added documentation
* Library fully type hinted
* Fixed debug info with -D, and extra info with -vv
* Added argument `sequential` to `walkdirs()` that allows sequential scanning
  instead of scanning in parallel.
* Format field changes:
   * `{change_t}` added, one letter for the change type
   * `{dupinfo}` added, human readable info about duplicated files
      (--duplicates)
   * `{dupcount}` added, the number of times the file has been duplicated
   * `{dup}` added, prints 'DUP' if duplicated file.
* Added more testing
* Fix `dir_compare1()` and `dir_compare2()` to facilitate sha diffing and
  refactor diffing issues
* Added new compare types `n` and `m` for renamed files in `--shadiff` and
  `d` (duplicated) in `--duplicates`.
* Added type checker hints
* Change command line parameters
   * Adding `-d, --duplicates` to show duplicated files in scan mode
   * Adding `-H, --shadiff` to track renamed files while diffing dirs
   * Rename `-c, --compare` to `-f, --filter`
   * Implemented proper invert `^` in `-f, --filter` and `-t, --types`
* Dirscan object changes:
  * Removed `DirObj.traverse()`
  * Added `DirscanObj.support_children()`
  * Renamed `DirscanObj.exclude_files()` into `DirscanObj.set_exclude()`
  * Removed `DirscanObj.exclude_otherfs()` and merge into
    `DirscanObj.set_exclude()`
* Update to 2023


## v0.10

* License change to MIT
* major overhaul including python3 migration
* Change command line parameters.
    * Adding `-0, --print0`
    * Rename `-d, --compare-dates` to `-t, --types`
    * Add count on `--debug`. Used more times = more verbose
    * Rename `-r` to `-R` (`--reverse`)
    * Rename `-t, --traverse-oneside` to `-r, --recursive`
    * Use `-s, --summary` as boolean arg only, while `-S, --summary-format`
      can be used for specifying format.
    * Rename `-f, --file-types` to `-t, --types`
    * Rename `-d, --compare-dates` to `-T, --compare-time`
* Format field changes:
    * `{path}` renamed to `{relpath}`
    * `{fullpath}` renamed to `{path}`
    * `{mode_t}` removed
    * `{mode_h}` added, representing human readable mode string
    * `{mtime}` removed
    * Added `{mtime_h}`, `{mtime_f}`, `{mtime_x}`
    * Renamed summary field `{sum_objects}` to `{n_objects}`
    * Add field `{relpath_u}` to print posixpath on windows (for dump files
      which is always in unix format)
* Rename `fileinfo.py` to `formatfields.py`
* Dirscan file object classes overhaul
    * Base class renamed from `BaseObj` to `DirscanObj`
    * Changed to `__slots__` to conserve memory
    * Save the file stat fields (mode, uid, gid, size, time) as class instance
      vars and not as stat values to save memory and increase speed
    * Remove `parse()` method
    * Make `compare()` method into a generator
    * Fix time comparison and allow for `TIME_THRESHOLD` slack before reporting
      difference
    * Change `FileObj.hashsum` and `FileObj.hashsum_hex` into properties
    * Remove `SpecialObj` class and add `BlockDevObj`, `CharDevObj`, `FifoObj`,
      `SocketObj` classes
    * Use `os.scandir()` to read a directory more efficiently
    * Add the `to_dict()` method to generate dict from any `DirscanObj` instance
    * Ensure `FileObj` and `DirObj` doesn't query the filesystem for missing
      field data
    * Added `DirObj.traverse()` to parse recursively the tree to build up the
      in-memory tree
* Fix scanfile reading and improved robustness of scan files in `scanfile.py`
    * Change to hex mtime timestamp
    * Change to octal modestring containting only filemode
* Added pytest and coverage framework
* Add support for Windows
* Implemented `create_from_dict()` factory and removed `create_from_data()`


## v0.9.1

* `dirscan/__main__.py` cleanups and refactoring. Splitting into several
  functions and files. Adding dirscan/compare.py, dirscan/usage.py.
* `dirscan/dirscan.py`, add support for `treeid=` in `BaseObj()` and inherited
  objects. Change order of arguments to `BaseObj(name, path='', ...)`, was
  `BaseObj(path, name, ...)`
* Add debug and log mechanism in `dirscan/log.py`
* Add `-D, --debug` option to dirscan


## v0.9

* pypi publish
