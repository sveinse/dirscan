=========
Changelog
=========

v0.9.1
------

- dirscan/__main__.py cleanups and refactoring. Splitting into several functions
  and files. Adding dirscan/compare.py, dirscan/usage.py.
- dirscan/dirscan.py, add support for treeid= in BaseObj() and inherited objects.
  Change order of arguments to BaseObj(name, path='', ...),
  was BaseObj(path, name, ...)
- Add debug/log mechanism in dirscan/log.py
- Add -D, --debug option to dirscan

v0.9
----

- pypi publish
