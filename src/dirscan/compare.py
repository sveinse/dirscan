'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2022 Svein Seldal
This code is licensed under MIT license (see LICENSE for details)
URL: https://github.com/sveinse/dirscan
'''

from typing import List
from dirscan.dirscan import DirscanObj, FileObj, NonExistingObj
from dirscan.formatfields import COMPARE_TYPES_ALL


# pylint: disable=unused-argument
def dir_compare1(objs: List[DirscanObj], ignores='', comparetypes='',
                 compare_time=False, shadb=None):
    ''' Object comparator for one object. The only thing this function tests
        for is if the object is excluded. Returns tuple with (change, text)
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


def dir_compare2(objs: List[DirscanObj], ignores='', comparetypes=COMPARE_TYPES_ALL,
                 compare_time=False, shadb=None):
    ''' Object comparator for two objects. Returns a tuple with (change, text)
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
            shalist = shadb.get(sha, [])
            other = None
            for i, o in shalist:
                if i == 0:  # This ensures that only left sources are used
                    other = o
            if other:
                text = "renamed, in left %s" %(other.fullpath)
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
            shalist = shadb.get(sha, [])
            other = None
            for i, o in shalist:
                if i == 1:  # This ensures that only right sources are used
                    other = o
            if other:
                text = "renamed, in right %s" %(other.fullpath)
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
    needcompare = set('cLRe')
    if not needcompare.intersection(comparetypes):
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
                if len(differences) == 1 and not compare_time:
                    continue
                if 't' in ignores:
                    continue
                change = 'left is newer'
                change_type = 'left_newer'
            elif 'older' in change:
                if len(differences) == 1 and not compare_time:
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
