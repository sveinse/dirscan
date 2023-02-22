''' Dirscan - helper for printing progress while scanning '''
#
# Copyright (C) 2010-2023 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

from typing import Any, List, TextIO
from dataclasses import dataclass, field
import sys
from datetime import datetime, timedelta


@dataclass
class ProgressorABC:
    ''' Progress instance '''
    text: str
    count: int
    size: int

    def __enter__(self) -> 'ProgressorABC':
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        pass

    def step(self, text: str = '', size: int = -1) -> None:
        ''' Step progression '''
        # print(self.text, text)


class ProgressABC:
    ''' Placeholder progress tracker that does nothing '''

    def progress(self, *, text: str, count: int = -1, size: int = -1) -> ProgressorABC:
        ''' Register a new progress and return a context '''
        return ProgressorABC(text, count, size)

    def print(self, *args: Any, **kwargs: Any) -> None:
        ''' Print a message '''
        print(*args, **kwargs)


PROGRESS: ProgressABC = ProgressABC()


def getprogress() -> ProgressABC:
    ''' Return the current progress instance '''
    return PROGRESS


def setprogress(progress: ProgressABC) -> None:
    ''' Set the current progress instance '''
    global PROGRESS  # pylint: disable=global-statement
    PROGRESS = progress


@dataclass
class Progressor(ProgressorABC):
    ''' Progress instance '''
    text: str = ''
    count: int = 0
    size: int = 0
    line: str = ''
    total_count: int = -1
    total_size: int = -1
    progress: 'PrintProgress' = field(repr=False, default_factory=int)  # type: ignore
    starttime: datetime = field(default_factory=datetime.now)
    timestamp: datetime = field(default_factory=datetime.now)

    def __enter__(self) -> 'Progressor':
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.progress.done(self)

    def step(self, text: str = '', size: int = -1) -> None:
        ''' Step progression '''
        self.timestamp = datetime.now()
        self.text = text
        self.count += 1
        if size > 0:
            self.size += size
        self.progress.step()

    @property
    def percent(self) -> float:
        ''' Return the progress in % '''
        if self.total_size > 0:
            return 100. * self.size / self.total_size
        return -1.

    def get_text(self) -> str:
        ''' Return the current text string '''
        fmt = self.__dict__.copy()
        fmt.update({
            'percent': self.percent,
        })
        return self.line.format(**fmt)


class PrintProgress(ProgressABC):
    ''' Stderr-oriented progress handler '''

    def __init__(self, file: TextIO=sys.stdout, update_interval: int=1000,
                 update_delay: int=1000, show_progress: bool=True):
        super().__init__()
        self.file = file
        self.timestamp = datetime.now()
        self.updateinterval = timedelta(milliseconds=update_interval)
        self.updatedelay = timedelta(milliseconds=update_delay)
        self.show_progress = show_progress
        self.next_clear = False
        self.progressors: List[Progressor] = []

    def progress(self, *, text: str, count: int = -1, size: int = -1) -> Progressor:
        ''' Register a new progress and return a context '''
        progressor = Progressor('', 0, 0, text, count, size, progress=self)
        self.progressors.append(progressor)
        self.timestamp = datetime.now()
        return progressor

    def done(self, progressor: Progressor) -> None:
        ''' Remove a progressor '''
        self.progressors.remove(progressor)
        self.step(force=True)

    def step(self, force: bool = False) -> None:
        ''' Print a progress step '''

        if self.show_progress:
            stamp = datetime.now()

            if force or (stamp - self.timestamp) > self.updateinterval:

                text = "".join(
                    p.get_text()
                    for p in self.progressors
                    if (stamp - p.starttime) > self.updatedelay
                )

                self.timestamp = stamp
                print('\r' + text + '\x1b[K', end='', file=self.file)
                self.next_clear = True

    def print(self, *args: Any, **kwargs: Any) -> None:
        ''' Print a message '''

        if self.next_clear:
            # Go to start of line and erase rest of the line
            print('\r\x1b[K', end='', file=self.file)
            self.next_clear = False

        print(*args, file=self.file, **kwargs)
        self.step(force=True)
        self.file.flush()

    def close(self) -> None:
        ''' Close the progress '''

        if self.next_clear:
            print('\r\x1b[K', end='', file=self.file)

        self.file.flush()
