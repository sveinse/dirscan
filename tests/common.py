import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dirscan.dirscan import DirscanObj

ExpectedT = tuple[str, *tuple[type[DirscanObj] | dict[str, Any], ...]]
"""Type for testing expected directory scan results.

The first element of the tuple is the path as a string. The remaining elements
are either types of DirscanObj or dictionaries specifying the expected
attributes of the objects.
"""


@dataclass
class Tempdir:
    """Utility class for managing temporary directories and files."""

    path: Path

    @staticmethod
    def wrdata(f: str | Path, d: str | None) -> None:
        """Write data to a file."""
        with open(f, "w", encoding="utf-8") as fd:
            if d:
                fd.write(d)
            fd.flush()

    @staticmethod
    def chmod(*args: Any, **kwargs: Any) -> None:
        """Change the mode of a file."""
        os.chmod(*args, **kwargs)

    @staticmethod
    def makedirs(*args: Any, **kwargs: Any) -> None:
        """Create directories recursively."""
        os.makedirs(*args, **kwargs)

    @staticmethod
    def maketree(base: str, tree: Iterable[tuple[str, str, str | None]]) -> None:
        """Create a directory tree based on the given structure."""
        os.makedirs(base, exist_ok=True)
        for path, typ, content in tree:
            full_path = Path(base, path)
            if typ == "d":
                os.makedirs(full_path, exist_ok=True)
            elif typ == "f":
                os.makedirs(full_path.parent, exist_ok=True)
                Tempdir.wrdata(full_path, content)

    @staticmethod
    def compare(
        tree: Iterable[tuple[Path, tuple[DirscanObj, ...]]],
        expected: Iterable[ExpectedT],
    ) -> None:
        """Compare the actual directory scan tree with the expected structure."""
        walks = tuple(tree)
        base = [o.fullpath for o in walks[0][1]]

        for (ap, aobjs), (bp, *bobjs) in zip(walks, expected, strict=True):
            assert ap == Path(bp), f"Expected path {bp}, got {ap!r}"

            # For each of the objects...
            for i, (ao, bo) in enumerate(zip(aobjs, bobjs, strict=True)):
                fp = Path(base[i], bp)

                # NOTE: This logic is needed because the top-level object looks like this:
                #   DirObj(path="a", name="")  # fullpath "a"  <-- This is the special case for the top-level object
                #   Dirobj(path="a", name="b")  # fullpath "a/b"
                #   DirObj(path="a/b", name="c")  # fullpath "a/b/c"
                exp: dict[str, Any] = {
                    "path": base[i] if fp == base[i] else fp.parent,
                    "name": "" if fp == base[i] else fp.name,
                    "fullpath": fp,
                }

                # Get the expected object class
                if isinstance(bo, dict):
                    exp.update(bo)
                else:
                    exp["obj"] = bo
                assert type(ao) is exp["obj"], f"Expected type {exp['obj']}, got {type(ao)}"

                # Check the attributes
                if isinstance(exp, dict):
                    for k, v in exp.items():
                        if k == "obj":
                            continue
                        assert getattr(ao, k) == v, f"Expected {k}={v}, got {getattr(ao, k)}"
