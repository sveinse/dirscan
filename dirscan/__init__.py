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
#from __future__ import absolute_import
#from .dirscan import *

__version__ = '0.9'


from .dirscan import walkdirs, create_from_fs, create_from_data
from .dirscan import DirscanException
from .dirscan import FileObj, LinkObj, DirObj, SpecialObj, NonExistingObj
