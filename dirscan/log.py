# -*- coding: utf-8 -*-
'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2018 Svein Seldal, sveinse@seldal.com
URL: https://github.com/sveinse/dirscan

This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.
'''
from __future__ import absolute_import, division, print_function

import sys

_ENABLE_DEBUG = False

def set_debug(debug):
    global _ENABLE_DEBUG
    _ENABLE_DEBUG = debug

def debug(*args, **kwargs):
    if not _ENABLE_DEBUG:
        return
    sys.stderr.write('DEBUG:   ')
    sys.stderr.write(*args, **kwargs)
    sys.stderr.write('\n')
