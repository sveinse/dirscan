''' Dirscan - recursively scanning and comparing one or more directories '''
#
# Copyright (C) 2010-2026 Svein Seldal
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

    # Primary functions
    "main",
    "walkdirs",
    "scan_shadb",
    "obj_compare1",
    "obj_compare2",

    # Scanfile functions
    "is_scanfile",
    "open_dir_or_scanfile",
    "read_scanfile",

    # Factories
    "create_from_fs",
    "create_from_dict",

    # Dirscan objects
    "DirscanObj",
    "FileObj",
    "LinkObj",
    "DirObj",
    "BlockDevObj",
    "CharDevObj",
    "SocketObj",
    "FifoObj",
    "NonExistingObj",

    # Helpers
    "set_debug",
    "DirscanException",
]
