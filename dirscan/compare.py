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



#pylint: disable=unused-argument
def dir_compare1(objs, ignores='', comparetypes='', compare_dates=False):
    ''' Object comparator for 1 dir. Returns tuple with (change, text) '''

    # Comparison matrix for 1 dir
    # ---------------------------
    #    x    excluded  Excluded
    #    *    scan      Scan

    if objs[0].excluded:
        # File EXCLUDED
        # =============
        return ('excluded', 'excluded')

    return ('scan', 'scan')



def dir_compare2(objs, ignores='', comparetypes='', compare_dates=False):
    ''' Object comparator for two dirs. Returns a tuple with (change, text) '''

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
        if objs[0].objtype == '-':
            return ('excluded', 'Right excluded, not present in left')
        if objs[1].objtype == '-':
            return ('excluded', 'Left excluded, not present in right')
        return ('excluded', 'excluded')

    if objs[0].objtype == '-' or objs[0].excluded:
        # File present RIGHT only
        # =======================
        text = "%s only in right" %(objs[1].objname,)
        if objs[1].excluded:
            return ('excluded', 'excluded, only in right')
        if objs[0].excluded:
            text += ", left is excluded"
        return ('right_only', text)

    if objs[1].objtype == '-' or objs[1].excluded:
        # File present LEFT only
        # ======================
        text = "%s only in left" %(objs[0].objname,)
        if objs[0].excluded:
            return ('excluded', 'excluded, only in left')
        if objs[1].excluded:
            text += ", right is excluded"
        return ('left_only', text)

    if len(set(o.objtype for o in objs)) > 1:
        # File type DIFFERENT
        # ===================
        text = "Different type, %s in left and %s in right" %(
            objs[0].objname, objs[1].objname)
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
    changes = objs[0].compare(objs[1])
    if changes:
        # Make a new list and filter out the ignored differences
        filtered_changes = []
        change_type = 'changed'
        for change in changes:
            if 'newer' in change:
                if len(changes) == 1 and not compare_dates:
                    continue
                if 't' in ignores:
                    continue
                change = 'left is newer'
                change_type = 'left_newer'
            elif 'older' in change:
                if len(changes) == 1 and not compare_dates:
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

        if filtered_changes:  # else from this test indicates file changed,
                              # but all changes have been masked with
                              # ignore settings

            # File contents CHANGED
            # =====================
            text = "%s changed: %s" %(objs[0].objname, ", ".join(filtered_changes))
            return (change_type, text)

        # Compares with changes may fall through here because of
        # ignore settings

    # File contents EQUAL
    # ===================
    return ('equal', 'equal')
