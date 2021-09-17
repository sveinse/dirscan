'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2021 Svein Seldal, sveinse@seldal.com
URL: https://github.com/sveinse/dirscan

This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.
'''

__version__ = '0.10a1'


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
