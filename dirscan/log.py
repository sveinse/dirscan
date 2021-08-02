# -*- coding: utf-8 -*-
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

_ENABLE_DEBUG = False


def set_debug(enable):
    ''' Set global debug mode '''
    global _ENABLE_DEBUG  # pylint: disable=global-statement
    _ENABLE_DEBUG = enable


def debug(*args, **kwargs):
    ''' Print debug text, if enabled '''
    if not _ENABLE_DEBUG:
        return
    sys.stderr.write('DEBUG:   ')
    sys.stderr.write(*args, **kwargs)
    sys.stderr.write('\n')
