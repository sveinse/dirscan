''' Dirscan - directory comparison functions '''
#
# Copyright (C) 2010-2023 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan

from typing import Any, Container, Generator, List, Optional, Sequence, Tuple, Dict, Collection, Callable, Union

import itertools
from pathlib import Path

from dirscan.dirscan import DirscanObj, FileObj, NonExistingObj, create_from_fs
from dirscan.progress import PrintProgress
from dirscan.log import debug

# Typings
from dirscan.dirscan import TPath

TCompare = Tuple[str, str]
TShadb = Dict[bytes, List[Tuple[int, DirscanObj]]]


def walkdirs(dirs: Collection[Union[DirscanObj, TPath]],
             *,
             excludes: Optional[Collection[TPath]]=None,
             exception_fn: Optional[Callable[[Exception], bool]]=None,
             reverse: bool=False,
             onefs: bool=False,
             traverse_oneside: bool=True,
             close_during: bool=True,
             sequential: bool=False,
             ) -> Generator[Tuple[Path, Tuple[DirscanObj, ...]], None, None]:
    '''
    Generator function that recursively traverses the given directories and
    yields the found files as it traverses the tree(s). The directories will
    be traversed in parallel, which can be utilized to in-line compare the
    directory trees.

    Args:
     ``dirs``
        Directories to traverse. The elements must either be a path to a
        physical directory or a previously parsed :py:class:`DirscanObj` object.
        The objects must support children, such as with :py:class:`DirObj`.

     ``excludes``
        Optional collection of excluded paths, relative to the base of the
        tree. ``'.'`` indicates top-level root of the tree, while e.g. ``'b'``
        refers to the named object immediately below the root. Globbing is
        supported, see :py:meth:`DirscanObj.exclude_files()` for more details.

     ``exception_fn``
        Exception handler callback. It will be called if any scanning exceptions
        occur during traversal, typically file system access errors. The
        callback is called with ``exception_fn(exception)`` and expects a
        ``bool`` return value. If the function is not set or returns a falsy
        value, the exception will be raised and traversal stops.

     ``reverse``
        Reverses the scanning order

     ``onefs``
        Scan file objects belonging to the same file system only

     ``traverse_oneside``
        When traversing the directory trees, setting this to ``True`` will
        traverse into all directories even when they only exists in one of
        the directory trees. Setting it to ``False`` will skip
        traversal into directories that only exists in one of the directory
        trees.

     ``close_during``
        will call :py:meth:`DirscanObj.close()` after objects have been
        yielded to the caller. This allows freeing up parsed objects to
        conserve memory while parsing very large trees. Note that this tears
        down the in-memory references to children, making it impossible to
        retraverse the tree after this function is complete.

     ``sequential``
        If ``True``, the directories will be traversed in parallel
        simulaneously. If ``False``, each of the directories will be scanned
        in turn.

    Yields:
      Tuples containing ``(path, objs)`` for each file object it finds.
      ``path`` represents the common file path. ``objs`` is a tuple of file
      objects representing the respective file object corresponding the
      ``dirs`` directory tree. The objects returned are inherited types from
      the base class :py:class:`DirscanObj`, such as :py:class:`FileObj` and
      :py:class:`DirObj`. If a file is only present in one of the dirs but
      not the others, the object will be :py:class:`NonExistingObj`.
    '''

    if sequential:
        for obj in dirs:
            yield from walkdirs((obj,), reverse=reverse, excludes=excludes,
                                onefs=onefs, traverse_oneside=traverse_oneside,
                                exception_fn=exception_fn,
                                close_during=close_during,
                                sequential=False)
        return

    # Ensure the exclusion list is a list
    if excludes is None:
        excludes = []

    # When scanning a single directory 'False' will not work due to the
    # selection logic below.
    if len(dirs) < 2:
        traverse_oneside = True

    # Check list of dirs indeed are dirs and create initial object list to
    # start from
    base = []
    for obj in dirs:

        # If we're not handed a FileObj-instance
        if not isinstance(obj, DirscanObj):
            obj = create_from_fs('', obj)

        # The object must be a object that supports children
        if not obj.support_children():
            raise NotADirectoryError()

        base.append(obj)

    # Start the queue
    queue: List[Tuple[Path, Tuple[DirscanObj, ...]]] = [(Path('.'), tuple(base))]

    debug(2, "")

    # Traverse the queue
    while queue:

        # Get the next set of objects
        path, objs = queue.pop(-1)

        debug(2, ">>>>  OBJECT {}:  {}", path, objs)

        # Parse the objects, getting object metadata
        for obj, baseobj in zip(objs, base):
            try:
                # Test for exclusions
                obj.set_exclude(excludes, base=baseobj, onefs=onefs)

            # Parsing the object failed
            except OSError as err:
                # Call the user exception callback, raise if not
                if not exception_fn or not exception_fn(err):
                    raise

        # How many objects are present?
        present = sum(not isinstance(obj, NonExistingObj) and not obj.excluded
                      for obj in objs)

        # Send back object list to caller
        yield (path, objs)

        # Create a list of unique children names seen across all objects, where
        # excluded objects are removed from parsing
        childobjs = []
        for obj in objs:
            children = {}
            try:
                # Skip the children if the parent...

                # ...doesnt support children
                if not obj.support_children():
                    continue

                # ...is excluded
                if obj.excluded:
                    continue

                # ...is the only one
                if not traverse_oneside and present == 1:
                    continue

                # Get and append the children names
                children = {obj.name: obj for obj in obj.children()}
                debug(4, "      Children of {} is {}", obj, children)

            # Getting the children failed
            except OSError as err:
                # Call the user exception callback, raise if not
                if not exception_fn or not exception_fn(err):
                    raise

            finally:
                # Append the children collected so far
                childobjs.append(children)

        # Merge all found objects into a single list of unique, sorted,
        # children names and iterate over it
        for name in sorted(set(itertools.chain.from_iterable(childobjs)),
                           reverse=not reverse):

            # Get the child if it exists for each of the dirs being traversed
            child = tuple(
                children.get(name) or NonExistingObj(name, path=parent.fullpath)
                for parent, children in zip(objs, childobjs)
            )

            # Append the newly discovered objects to the queue
            queue.append((Path(path, name), child))

        # Close objects to conserve memory
        if close_during:
            for obj in objs:
                obj.close()


def scan_shadb(dirs: Collection[DirscanObj],
               *,
               exception_fn: Optional[Callable[[Exception], bool]]=None,
               progress: Optional[PrintProgress]=None,
               **kwargs: Any,
               ) -> TShadb:
    '''
    Traverse through the directory tree(s) and build a database of shasum
    entries. This can be used to find identical files duplicated multiple
    times or verify unique entries.

    Args:
        dirs: Directories to traverse.
        exception_fn: Exception handler callback. It will be called if any
            exceptions occur during traversal, typically file system errors.
            See ``exception_fn`` argument of :py:func:`walkdirs()`.
        progress: UI helper to show progress.
        kwargs: Additional options passed to :py:func:`walkdirs()`

    Returns:
        A dict indexed by the encountered sha hashsum in the directory
        tree(s). The value is a list of the file entries for that sha
        entry. Each element of the list consists of ``(index, obj)``, where
        index corresponds to which tree the match was found, indexed by the
        ``dirs`` argument. ``obj`` is a :py:class:`FileObj` object.
    '''

    # -- Build the sha database
    shadb: TShadb = {}

    # Prepare progress values
    count = 0

    for i, sdir in enumerate(dirs):
        for (_, objs) in walkdirs(
                [sdir],
                exception_fn=exception_fn,
                close_during=False,
                **kwargs):

            # Progress printing
            count += 1
            if progress:
                progress.progress(f"Scanning {count} files:  {objs[0].fullpath}")

            # Evaluate the hashsum for each of the objects and store in
            # sha database
            for obj in objs:
                if not isinstance(obj, FileObj) or obj.excluded:
                    continue

                try:
                    # Get the hashsum and store it to the shadb list
                    shadb.setdefault(obj.hashsum, []).append((i, obj))
                except IOError as err:
                    if not exception_fn or not exception_fn(err):
                        raise

    return shadb


# pylint: disable=unused-argument
def obj_compare1(objs: Sequence[DirscanObj],
                 ignores: Container[str]='',
                 no_compare: bool=False,
                 ignore_time: bool=True,
                 shadb: Optional[TShadb]=None
                 ) -> TCompare:
    '''
    Object comparator for one-length objects. Since there is nothing to
    compare against, it will simply check if the object is excluded. If
    ``shadb`` is included, it will check for duplicated entries.

    Args:
        objs: 1-item list of objects
        ignores: Argument unused
        no_compare: Argument unused
        ignore_time: Argument unused
        shadb: Optional sha database generated with :py:func:`scan_shadb()`.
            When the compare object is found in the database with more than one
            entry, it will be labled as a ``duplicated`` change.

    Returns:
        Tuple containing ``(change, description)`` for the comparison results
        between the objects. ``change``  describes the type of change and
        ``description`` gives a more detailed explaination of the change.
    '''
    assert len(objs) == 1
    obj = objs[0]

    # Comparison matrix for 1 dir
    # ---------------------------
    #    x    excluded  Excluded
    #    *    scan      Scan

    # File EXCLUDED
    # =============
    if obj.excluded:
        return ('excluded', 'excluded')

    # File DUPLICATED
    # ===============
    if shadb and isinstance(obj, FileObj):
        sha = obj.hashsum
        if sha in shadb and len(shadb[sha]) > 1:
            return ('duplicated', 'Duplicated entry')

    return ('scan', 'scan')


def obj_compare2(objs: Sequence[DirscanObj],
                 ignores: Container[str]='',
                 no_compare: bool=False,
                 ignore_time: bool=True,
                 shadb: Optional[TShadb]=None
                 ) -> TCompare:
    '''
    Object comparator for two-length objects.

    Args:
        objs: 2 length item list of objects to compare
        ignores: Ignore certain types of comparisons. ``t`` ignore time
            differences, ``u`` ignores UID differences, ``g`` ignores GID
            differences, ``p`` ignores permission differences.
        no_compare: When ``True`` it will skip comparing the object if they
            are both present and of the same type. The function will then
            return ``('skipped`,...)``.
        ignore_time: If ``True`` it will ignore differences in timestamp on
            files which are otherwise equal.
        shadb: Optional sha database generated with :py:func:`scan_shadb()`.
            When comparing with supplied sha database, it is able to track
            renames of files.

    Returns:
        Tuple containing ``(change, description)`` for the comparison results
        between the objects. ``change``  describes the type of change and
        ``description`` gives a more detailed explaination of the change.
    '''
    assert len(objs) == 2
    left, right = objs

    # Comparison matrix for 2 dirs
    # -----------------------------
    #    xx   excluded        Excluded
    #    x-   excluded        Left excluded, not present in right
    #    x*   excluded        Only in right, left is excluded
    #    a-   left_only       Only in left
    #    -a   right_only      Only in right
    #    ab   different_type  Different type: %a in left, %b in right
    #    ab   changed         %t changed: ...
    #         left_newer
    #         right_newer
    #    aa   Equal

    # File EXCLUDED
    # =============
    if all(o.excluded for o in objs):
        if isinstance(left, NonExistingObj):
            return ('excluded', 'Right excluded')
        if isinstance(right, NonExistingObj):
            return ('excluded', 'Left excluded')
        return ('excluded', 'excluded')

    if left.excluded and isinstance(right, NonExistingObj):
        return ('excluded', 'excluded, only in left')
    if right.excluded and isinstance(left, NonExistingObj):
        return ('excluded', 'excluded, only in right')

    # File present RIGHT only
    # =======================
    if isinstance(left, NonExistingObj) or left.excluded:
        text = f"{right.objname} only in right"
        if left.excluded:
            text += ", left is excluded"
        elif shadb and isinstance(right, FileObj):
            sha = right.hashsum
            if sha:
                shalist = shadb.get(sha, [])
                other = None
                for i, obj in shalist:
                    if i == 0:  # This ensures that only left sources are used
                        other = obj
                if other:
                    text = f"renamed, in left {other.fullpath}"
                    return ('right_renamed', text)
        return ('right_only', text)

    # File present LEFT only
    # ======================
    if isinstance(right, NonExistingObj) or right.excluded:
        text = f"{left.objname} only in left"
        if right.excluded:
            text += ", right is excluded"
        elif shadb and isinstance(left, FileObj):
            sha = left.hashsum
            if sha:
                shalist = shadb.get(sha, [])
                other = None
                for i, obj in shalist:
                    if i == 1:  # This ensures that only right sources are used
                        other = obj
                if other:
                    text = f"renamed, in right {other.fullpath}"
                    return ('left_renamed', text)
        return ('left_only', text)

    # File type DIFFERENT
    # ===================
    if len(set(type(o) for o in objs)) > 1:
        text = (f"Different type, "
                f"{left.objname} in left and {right.objname} in right")
        return ('different_type', text)

    # File type EQUAL
    # ===============

    # Unless we're not intersted in these comparetypes, then we don't have
    # to spend time on making the compare (which can be time consuming)
    if no_compare:
        return ('skipped', 'compare skipped')

    # compare returns a list of differences. If None, they are equal
    # This might fail, so be prepared to catch any errors
    differences = tuple(left.compare(right))
    if differences:
        # Make a new list and filter out the ignored differences
        filtered_changes = []
        change_type = 'changed'
        for change in differences:
            if 'newer' in change:
                if len(differences) == 1 and ignore_time:
                    continue
                if 't' in ignores:
                    continue
                change = 'left is newer'
                change_type = 'left_newer'
            elif 'older' in change:
                if len(differences) == 1 and ignore_time:
                    continue
                if 't' in ignores:
                    continue
                change = 'right is newer'
                change_type = 'right_newer'
            elif 'u' in ignores and 'UID differs' in change:
                continue
            elif 'g' in ignores and 'GID differs' in change:
                continue
            elif 'p' in ignores and 'permissions differs' in change:
                continue
            filtered_changes.append(change)

        # else from the following test indicates file changed, but all changes
        # have been masked with ignore settings
        if filtered_changes:

            # File contents CHANGED
            # =====================

            # FIXME: Need to check either side for being renamed

            text = f"{left.objname} changed: {', '.join(filtered_changes)}"
            return (change_type, text)

        # Compares with changes may fall through here because of
        # ignore settings

    # File contents EQUAL
    # ===================
    return ('equal', 'equal')
