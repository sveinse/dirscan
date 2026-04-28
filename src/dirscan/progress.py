"""Dirscan - helper for printing progress while scanning"""
#
# Copyright (C) 2010-2026 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

from __future__ import annotations

import concurrent.futures
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, TextIO, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def mimic(target: F) -> Callable[[Callable[..., Any]], F]:
    """A decorator factory that returns a 'cast' to the target's signature."""
    def decorator(real_func: Callable[..., Any]) -> F:
        return cast(F, real_func)
    return decorator


@dataclass
class PrintProgressItem:
    """Progress instance"""

    format: str = ""
    prefix: str = ""
    text: str = ""
    count: int = 0
    size: int = 0
    total_count: int = -1
    total_size: int = -1
    starttime: datetime = field(default_factory=datetime.now)
    timestamp: datetime = field(default_factory=datetime.now)
    _progress: PrintProgress | None = field(repr=False, default=None)

    def __enter__(self) -> PrintProgressItem:
        """Support for usage as a context manager"""
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Cleanups after the context manager"""
        if self._progress:
            self._progress.remove(self)

    def set_progressor(self, progress: PrintProgress) -> None:
        """Set the progressor"""
        self._progress = progress

    def update(self, text: str = "", size: int = -1, add_size: int = -1) -> None:
        """Update progression"""
        self.timestamp = datetime.now()
        self.count += 1
        self.text = text
        if size >= 0:
            self.size = size
        if add_size >= 0:
            self.size += add_size
        # if self._progress:
        #     self._progress.update()

    @property
    def percent(self) -> float:
        """Return the progress in %"""
        if self.total_size > 0:
            return 100.0 * self.size / self.total_size
        return -1.0

    def get_text(self) -> tuple[str, str]:
        """Return the current text string as a tuple (prefix, text)"""
        data = self.__dict__.copy()
        data.update(
            {
                "percent": self.percent,
            }
        )
        return self.prefix.format(**data), self.format.format(**data)


class PrintProgress:
    """Stderr-oriented progress handler"""

    def __init__(
        self,
        file: TextIO = sys.stdout,
        update_interval: int = 1000,
        update_delay: int = 1000,
        show_progress: bool = True,
    ):
        super().__init__()
        self.file = file
        self.timestamp = datetime.now()
        self.updateinterval = timedelta(milliseconds=update_interval)
        self.updatedelay = timedelta(milliseconds=update_delay)
        self.show_progress = show_progress
        self.progressors: list[PrintProgressItem] = []
        self._next_clear = False
        self._keep_running = True
        self._executor: concurrent.futures.ThreadPoolExecutor | None = None
        self._thread: concurrent.futures.Future[None] | None = None
        self._lock = threading.Lock()
        self._force_update = False

    def __enter__(self) -> PrintProgress:
        """Support for usage as a context manager"""
        self._executor = concurrent.futures.ThreadPoolExecutor().__enter__()
        self._keep_running = True
        if self.show_progress:
            self._thread = self._executor.submit(self._progress_main)
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Cleanups after the context manager"""
        self._keep_running = False
        if self._executor:
            self._executor.__exit__(exc_type, exc_value, traceback)
        self.close()

    @property
    def executor(self) -> concurrent.futures.ThreadPoolExecutor:
        """Return the executor"""
        if self._executor is None:
            raise RuntimeError("Progress executor not started")
        return self._executor

    def _progress_main(self) -> None:
        """Main progress loop"""
        while self._keep_running:
            latest_update = max((p.timestamp for p in self.progressors), default=self.timestamp)
            if self._force_update or latest_update > self.timestamp:
                self._update()

            time.sleep(self.updateinterval.total_seconds())

    def _update(self) -> None:
        """Update progress step"""
        self.timestamp = datetime.now()
        try:
            terminal_size = os.get_terminal_size(self.file.fileno())
            terminal_width = terminal_size.columns
        except (OSError, ValueError):
            terminal_width = 0

        text = fit_text([
            p.get_text()  # Returns tuple (prefix, text)
            for p in self.progressors
            if (self.timestamp - p.starttime) > self.updatedelay
        ], terminal_width)

        with self._lock:
            print("\r" + text, end="\x1b[K\r", file=self.file)
            self._next_clear = True
            self._force_update = False

    @mimic(PrintProgressItem)
    def progress(self, *args, **kwargs) -> PrintProgressItem:  # type: ignore
        """Register a new progress and return a context"""
        progressor = PrintProgressItem(*args, **kwargs)
        progressor.set_progressor(self)
        self.progressors.append(progressor)
        self.timestamp = datetime.now()
        return progressor

    def remove(self, progressor: PrintProgressItem) -> None:
        """Remove a progressor"""
        self.progressors.remove(progressor)
        self._force_update = True

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print a message"""

        with self._lock:
            if self._next_clear:
                # Go to start of line and erase rest of the line
                print("\r\x1b[K", end="", file=self.file)
                self._next_clear = False

            print(*args, **kwargs, file=self.file)
            self._force_update = True
            self.file.flush()

    def close(self) -> None:
        """Close the progress"""
        # Do an empty print to erase the progress line
        self.print("", end="")


def fit_text(textlist: list[tuple[str, str]], width: int) -> str:
    """Fit text to screen width

    textlist: List of (prefix, text) tuples
    width: Maximum width (0 = unlimited)
    returns: Fitted text
    """

    prefixlen = sum(len(prefix) for prefix, _ in textlist)
    textlen = sum(len(text) for _, text in textlist)
    if not width or prefixlen + textlen < width:
        return "".join(fixed + text for fixed, text in textlist)
    remain = width - prefixlen - 1

    # Truncate text to fit
    #
    # This code works by truncating the first text that is too long. If the
    # input contains multiple texts that are too long, it's the first one that
    # gets truncated.

    result = []
    for prefix, text in textlist:
        if remain > 0 and len(text) > remain:
            text = "\u2026" + text[-remain + 1 :]
            remain -= len(text) - 1
        result.append((prefix, text))
    return "".join(fixed + text for fixed, text in result)


PROGRESS: PrintProgress = PrintProgress()


def getprogress() -> PrintProgress:
    """Return the current progress instance"""
    return PROGRESS


def setprogress(progress: PrintProgress) -> None:
    """Set the current progress instance"""
    global PROGRESS
    PROGRESS = progress
