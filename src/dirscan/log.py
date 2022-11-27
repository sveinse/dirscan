'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2022 Svein Seldal
This code is licensed under MIT license (see LICENSE for details)
URL: https://github.com/sveinse/dirscan
'''
import sys

_DEBUG_LEVEL = False


def set_debug(level):
    ''' Set global debug level '''
    global _DEBUG_LEVEL  # pylint: disable=global-statement
    _DEBUG_LEVEL = level


def debug(level, text, *args, **kwargs):
    ''' Print debug text, if enabled '''
    if level > _DEBUG_LEVEL:
        return
    sys.stderr.write("DEBUG: " + str(text).format(*args, **kwargs) + "\n")


def debug_level():
    """ Return the current debug level """
    return _DEBUG_LEVEL
