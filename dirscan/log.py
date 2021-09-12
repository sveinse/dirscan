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
