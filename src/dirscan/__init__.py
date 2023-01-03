''' Dirscan - recursively scanning and comparing one or more directories '''
#
# Copyright (C) 2010-2023 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

__version__ = '0.11a1'


from dirscan.__main__ import main
from dirscan.dirscan import (
    create_from_fs,
    create_from_dict,
    DirscanException,
    DirscanObj,
    FileObj,
    LinkObj,
    DirObj,
    BlockDevObj,
    CharDevObj,
    SocketObj,
    FifoObj,
    NonExistingObj,
)
from dirscan.log import set_debug
from dirscan.scanfile import (
    is_scanfile,
    read_scanfile,
)
from dirscan.walkdirs import (
    walkdirs,
    scan_shadb,
    obj_compare1,
    obj_compare2,
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
