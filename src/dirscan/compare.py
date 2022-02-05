'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2022 Svein Seldal
This code is licensed under MIT license (see LICENSE for details)
URL: https://github.com/sveinse/dirscan
'''

from dirscan.dirscan import NonExistingObj


# pylint: disable=unused-argument
def dir_compare1(objs, ignores='', comparetypes='', compare_time=False):
    ''' Object comparator for one object. The only thing this function tests
        for is if the object is excluded. Returns tuple with (change, text)
    '''

    # Comparison matrix for 1 dir
    # ---------------------------
    #    x    excluded  Excluded
    #    *    scan      Scan

    if objs[0].excluded:
        # File EXCLUDED
        # =============
        return ('excluded', 'excluded')

    return ('scan', 'scan')


def dir_compare2(objs, ignores='', comparetypes='', compare_time=False):
    ''' Object comparator for two objects. Returns a tuple with (change, text)
    '''

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

    if all(o.excluded for o in objs):
        # File EXCLUDED
        # =============
        if isinstance(objs[0], NonExistingObj):
            return ('excluded', 'Right excluded, not present in left')
        if isinstance(objs[1], NonExistingObj):
            return ('excluded', 'Left excluded, not present in right')
        return ('excluded', 'excluded')

    if isinstance(objs[0], NonExistingObj) or objs[0].excluded:
        # File present RIGHT only
        # =======================
        text = f"{objs[1].objname} only in right"
        if objs[1].excluded:
            return ('excluded', 'excluded, only in right')
        if objs[0].excluded:
            text += ", left is excluded"
        return ('right_only', text)

    if isinstance(objs[1], NonExistingObj) or objs[1].excluded:
        # File present LEFT only
        # ======================
        text = f"{objs[0].objname} only in left"
        if objs[0].excluded:
            return ('excluded', 'excluded, only in left')
        if objs[1].excluded:
            text += ", right is excluded"
        return ('left_only', text)

    if len(set(type(o) for o in objs)) > 1:
        # File type DIFFERENT
        # ===================
        text = (f"Different type, "
                f"{objs[0].objname} in left and {objs[1].objname} in right")
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
    differences = tuple(objs[0].compare(objs[1]))
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
            text = f"{objs[0].objname} changed: {', '.join(filtered_changes)}"
            return (change_type, text)

        # Compares with changes may fall through here because of
        # ignore settings

    # File contents EQUAL
    # ===================
    return ('equal', 'equal')
