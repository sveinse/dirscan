# Changelog


## v0.10

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
* Fix scanfile reading and improved robustness of scan files in `scanfile.py`
* Added pytest and coverage framework


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