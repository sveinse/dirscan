''' Dirscan - logging utils '''
#
# Copyright (C) 2010-2025 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

from __future__ import annotations

import sys
from typing import Any

_DEBUG_LEVEL = 0


def set_debug(level: int) -> None:
    ''' Set global debug level

    Args:
        level: Verbosity level
    '''
    global _DEBUG_LEVEL
    _DEBUG_LEVEL = level


def debug(level: int, text: str, *args: Any, **kwargs: Any) -> None:
    ''' Print debug text, if enabled '''
    if level > _DEBUG_LEVEL:
        return
    sys.stderr.write("DEBUG: " + str(text).format(*args, **kwargs) + "\n")


def debug_level() -> int:
    """ Return the current debug level """
    return _DEBUG_LEVEL
