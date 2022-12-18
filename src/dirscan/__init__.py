'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2022 Svein Seldal
This code is licensed under MIT license (see LICENSE for details)
URL: https://github.com/sveinse/dirscan
'''

__version__ = '0.11a1'


from dirscan.__main__ import main
from dirscan.dirscan import (
    walkdirs,
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
from dirscan.compare import (
    dir_compare1,
    dir_compare2,
)

__all__ = [
    "main",
    "walkdirs",
    "create_from_fs",
    "create_from_dict",
    "DirscanException",
    "DirscanObj",
    "FileObj",
    "LinkObj",
    "DirObj",
    "BlockDevObj",
    "CharDevObj",
    "SocketObj",
    "FifoObj",
    "NonExistingObj",
    "set_debug",
    "is_scanfile",
    "read_scanfile",
    "dir_compare1",
    "dir_compare2",
]
