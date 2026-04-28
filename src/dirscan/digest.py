"""Functions for compare and digesting filedata."""
#
# Copyright (C) 2010-2025 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

from __future__ import annotations

import concurrent.futures
import hashlib
from pathlib import Path
from typing import Callable

from dirscan.progress import getprogress

# Typings
TPath = str | Path

# Select hash algorthm to use
HASHALGORITHM = hashlib.sha256

# Number of bytes to read per round in the hash reader
HASHCHUNKSIZE = 1024 * 1024
CHUNKSIZE = 1024 * 1024
DIRECT_READ = 16 * 1024 * 1024


def hashsum1(filename: TPath, size: int = -1) -> bytes:
    """Return the hashsum of the fileobj."""
    # Global scoped progress indicator
    with (
        # Global scoped progress indicator
        getprogress().progress(
            prefix="  [{percent:3.1f}% done]",
            total_size=size,
        ) as progress,
        open(filename, "rb") as fileobj,
    ):
        hash = HASHALGORITHM()
        while True:
            data = fileobj.read(HASHCHUNKSIZE)
            progress.update(add_size=len(data))
            if not data:
                break
            hash.update(data)
        return hash.digest()


def hashsum2(filename: TPath, size: int = -1) -> bytes:
    """Return the hashsum of the file."""
    with open(filename, "rb") as fileobj:
        return hashlib.file_digest(fileobj, HASHALGORITHM).digest()


def hashsum3(filename: TPath, size: int = -1) -> bytes:
    """Return the hashsum of the file."""
    with (
        # Global scoped progress indicator
        getprogress().progress(
            prefix="  [{percent:3.1f}% done]",
            total_size=size,
        ) as progress,
        open(filename, "rb") as fileobj,
    ):
        buf = bytearray(HASHCHUNKSIZE)
        view = memoryview(buf)
        shahash = HASHALGORITHM()
        while True:
            size = fileobj.readinto(buf)
            if size == 0:
                break
            shahash.update(view[:size])
            progress.update(add_size=size)
        return shahash.digest()


def hashsum4(filename: TPath, size: int = -1) -> bytes:
    """Return the hashsum of the file."""
    with (
        # Global scoped progress indicator
        getprogress().progress(
            prefix="  [{percent:3.1f}% done]",
            total_size=size,
        ) as progress,
        open(filename, "rb") as fileobj,
    ):
        executor = getprogress().executor
        future = executor.submit(hashlib.file_digest, fileobj, HASHALGORITHM)
        while True:
            try:
                progress.update(size=fileobj.tell())
                result = future.result(timeout=0.2)
                return result.digest()
            except concurrent.futures.TimeoutError:
                pass


def hashsum5(filename: TPath, size: int = -1) -> bytes:
    """Return the hashsum of the file."""
    with open(filename, "rb") as fileobj:
        if size < DIRECT_READ:
            return hashlib.file_digest(fileobj, HASHALGORITHM).digest()
        else:
            with (
                # Global scoped progress indicator
                getprogress().progress(
                    prefix="  [{percent:3.1f}% done]",
                    total_size=size,
                ) as progress,
            ):
                executor = getprogress().executor
                future = executor.submit(hashlib.file_digest, fileobj, HASHALGORITHM)
                while True:
                    try:
                        progress.update(size=fileobj.tell())
                        result = future.result(timeout=0.2)
                        return result.digest()
                    except concurrent.futures.TimeoutError:
                        pass


def compare1(file1: TPath, file2: TPath, size: int = -1) -> bool:
    """Compare two files."""
    with (
        # Global scoped progress indicator
        getprogress().progress(
            prefix="  [{percent:3.1f}% done]",
            total_size=size,
        ) as progress,
        open(file1, "rb") as fileobj1,
        open(file2, "rb") as fileobj2,
    ):
        while True:
            d1 = fileobj1.read(CHUNKSIZE)
            d2 = fileobj2.read(CHUNKSIZE)
            if not d1 and not d2:
                break
            if d1 != d2:
                return False
            progress.update(add_size=len(d1))
    return True


def compare2(file1: TPath, file2: TPath, size: int = -1) -> bool:
    """Compare two files."""
    with (
        # Global scoped progress indicator
        getprogress().progress(
            prefix="  [{percent:3.1f}% done]",
            total_size=size,
        ) as progress,
        open(file1, "rb") as fileobj1,
        open(file2, "rb") as fileobj2,
    ):
        buf1 = bytearray(CHUNKSIZE)
        buf2 = bytearray(CHUNKSIZE)
        view1 = memoryview(buf1)
        view2 = memoryview(buf2)
        while True:
            size1 = fileobj1.readinto(buf1)
            size2 = fileobj2.readinto(buf2)
            if size1 == 0 and size2 == 0:
                break
            if size1 != size2:
                return False
            if view1[:size1] != view2[:size2]:
                return False
            progress.update(add_size=size1 or size2)
    return True


DIGEST_FN: Callable[[TPath, int], bytes] = hashsum3
COMPARE_FN: Callable[[TPath, TPath, int], bool] = compare2
