"""Dirscan - recursively scanning and comparing one or more directories"""

#
# Copyright (C) 2010-2025 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan
import importlib.metadata

__version__ = importlib.metadata.version("dirscan")


from dirscan.__main__ import main
from dirscan.dirscan import (
    BlockDevObj,
    CharDevObj,
    DirObj,
    DirscanException,
    DirscanObj,
    FifoObj,
    FileObj,
    LinkObj,
    NonExistingObj,
    SocketObj,
    create_from_dict,
    create_from_fs,
)
from dirscan.log import set_debug
from dirscan.scanfile import (
    is_scanfile,
    open_dir_or_scanfile,
    read_scanfile,
)
from dirscan.walkdirs import (
    obj_compare1,
    obj_compare2,
    scan_shadb,
    walkdirs,
)

# Order matter to documentation
__all__ = [
    "BlockDevObj",
    "CharDevObj",
    "DirObj",
    "DirscanException",
    "DirscanObj",
    "FifoObj",
    "FileObj",
    "LinkObj",
    "NonExistingObj",
    "SocketObj",
    "create_from_dict",
    "create_from_fs",
    "is_scanfile",
    "main",
    "obj_compare1",
    "obj_compare2",
    "open_dir_or_scanfile",
    "read_scanfile",
    "scan_shadb",
    "set_debug",
    "walkdirs",
]
