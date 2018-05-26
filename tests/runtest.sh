#!/bin/bash

source testfuncs.sh


#=============================================================================
# Basic tests
#=============================================================================

mk_dir () {
    mkdir -p $1 $1/d $1/f
    touch $1/a $1/d/a $1/d/b $1/e $1/f/a $1/f/b
    echo "foo" >$1/b
    ln -s b $1/c
}

test_01 () {
    tsetup $FUNCNAME "Simple directory scan"
    mk_dir a

    trun a
    tclean
}

test_01b () {
    tsetup $FUNCNAME "Simple directory scan, verbose"
    mk_dir a

    trun a -als
    tclean
}

test_02 () {
    tsetup $FUNCNAME "Simple directory comparison"
    mk_dir a
    mk_dir b

    trun a b
    tclean
}

test_02b () {
    tsetup $FUNCNAME "Simple directory comparison, verbose"
    mk_dir a
    mk_dir b

    trun a b -als
    tclean
}


test_03 () {
    tsetup $FUNCNAME "Basic compare difference"
    mk_dir a
    mk_dir b
    rm -rf a/d

    trun a b
    tclean
}

test_03b () {
    tsetup $FUNCNAME "Basic compare difference, verbose"
    mk_dir a
    mk_dir b
    rm -rf a/d

    trun a b -als
    tclean
}

test_04 () {
    tsetup $FUNCNAME "Basic directory difference, traversed"
    mk_dir a
    mk_dir b
    rm -rf a/d

    trun a b -t
    tclean
}

test_04b () {
    tsetup $FUNCNAME "Basic directory difference, traversed, verbose"
    mk_dir a
    mk_dir b
    rm -rf a/d

    trun a b -alst
    tclean
}


#=============================================================================
# Coverage tests
#=============================================================================

test_c01 () {   # FIXME: Not done yet
    tsetup $FUNCNAME "All compare difference"
    mkdir -p a b
    touch a/empty b/empty
    techo "file" a/file b/file
    ln -s dead a/link
    ln -s dead b/link
    touch a/left b/right
    mkdir -p a/l_dir b/r_dir
    touch a/l_dir/a b/r_dir/a
    mkdir -p a/exclude b/exclude a/l_exclude b/r_exclude
    touch a/type
    ln -s bar b/type
    techo "left" a/change
    techo "right" b/change

    trun a -als
    trun b -als
    trun a b -als -X exclude -X l_exclude -X r_exclude
    tclean
}


#=============================================================================
# Scan-file tests
#=============================================================================

test_s01 () {
    tsetup $FUNCNAME "Save scan file"
    mk_dir a

    trun a -o scanfile.txt -s
    cat scanfile.txt
    tclean
}

test_s02 () {
    tsetup $FUNCNAME "Read from scan file"
    mk_dir a

    trun -als a
    trun a -o scanfile.txt
    trun -als --input scanfile.txt
    tclean
}

test_s03 () {
    tsetup $FUNCNAME "Compare with scan file"
    mk_dir a

    trun -als a
    trun a -o scanfile.txt
    trun -als --input scanfile.txt a
    tclean
}

test_s04 () {
    tsetup $FUNCNAME "Generate scanfile from scanfile"
    mk_dir a

    trun -als a
    trun a -o scanfile.txt
    trun -als --input scanfile.txt -o scanfile2.txt
    (set -x; diff scanfile.txt scanfile2.txt)
    tclean
}

test_s05 () {
    tsetup $FUNCNAME "Compare scanfile with scanfile"
    mk_dir a

    trun -als a
    trun a -o scanfile.txt
    trun -als --input --right scanfile.txt scanfile.txt
    tclean
}

test_s06 () {
    tsetup $FUNCNAME "Scan file comparison with excluded fs"
    mkdir -p a/tmp
    techo "file" a/file
    (set -x; sudo mount -t tmpfs tmpfs a/tmp)
    mkdir a/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file

    trun a -x -o scanfile.txt
    cat scanfile.txt
    trun -alsx --input scanfile.txt a

    (set -x; sudo umount a/tmp)
    tclean

}

test_s07 () {  # Similar to p02
    tsetup $FUNCNAME "Permission denied in scan test"
    mkdir -p a/one a/two
    touch a/one/file a/two/file
    echo "file" >a/file
    chmod 0000 a/one a/file

    trun a -o scanfile.txt
    cat scanfile.txt

    chmod +rwx a/one a/file
    tclean
}

test_s08 () {
    tsetup $FUNCNAME "Permission denied in two scan files"
    mkdir -p a/one
    techo "file" a/one/file
    techo "file" a/file
    chmod 0000 a/one a/file

    trun a -o scanfile.txt
    cat scanfile.txt
    trun -als --right a scanfile.txt

    chmod +rwx a/one a/file
    tclean
}


#=============================================================================
# Ordering tests
#=============================================================================

test_o01 () {
    tsetup $FUNCNAME "Directory scan, ascending"
    mk_dir a

    trun a
    tclean
}

test_o02 () {
    tsetup $FUNCNAME "Directory scan, descending"
    mk_dir a

    trun a --reverse
    tclean
}


#=============================================================================
# Top-level type tests
#=============================================================================

test_t01 () {
    tsetup $FUNCNAME "Symlink top object"
    ln -s foo a

    trun a -al

    tclean
}

test_t02 () {
    tsetup $FUNCNAME "Empty file top object"
    touch a

    trun a -al

    tclean
}

test_t03 () {
    tsetup $FUNCNAME "Permission denied top-level dir"
    mkdir -p a
    touch a/file
    chmod 0000 a

    trun a -al

    chmod +rwx a
    tclean
}

test_t04 () {
    tsetup $FUNCNAME "Random file top-level object"
    techo "file" a

    trun a -al

    tclean
}


#=============================================================================
# Permission tests
#=============================================================================
test_p01 () {
    tsetup $FUNCNAME "Permission denied top-level dir test"
    # Shall return PermissionError: [Errno 13] Permission denied: 'a'
    mkdir -p a
    touch a/file
    chmod 0000 a

    trun a -al

    chmod +rwx a
    tclean
}

test_p02 () {
    tsetup $FUNCNAME "Permission denied in scan test"
    mkdir -p a/one a/two
    touch a/one/file a/two/file
    echo "file" >a/file
    chmod 0000 a/one a/file

    trun a -als

    chmod +rwx a/one a/file
    tclean
}

test_p03 () {
    tsetup $FUNCNAME "Permission denied in comparisons test"
    mkdir -p a/one b/one
    touch a/one/file b/one/file
    techo "file" a/file b/file
    touch a/empty b/empty
    chmod 0000 a/one a/file

    trun a   -als
    trun b   -als
    trun a b -als

    chmod +rwx a/one a/file
    tclean
}

test_p04 () {
    tsetup $FUNCNAME "Dual permission denied in comparison"
    mkdir -p a/one b/one
    techo "file" a/one/file b/one/file
    techo "file" a/file b/file
    chmod 0000 a/one b/one a/file b/file

    trun a   -als
    trun b   -als
    trun a b -als

    chmod +rwx a/one b/one a/file b/file
    tclean
}


#=============================================================================
# Exclusion tests
#=============================================================================

test_x01 () {
    tsetup $FUNCNAME "Foreign filesystem scan"
    mkdir -p a/tmp
    techo "file" a/file
    (set -x; sudo mount -t tmpfs tmpfs a/tmp)
    mkdir a/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file

    trun -alxs --format="{arrow}  {mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {type}  {fullpath}" a

    (set -x; sudo umount a/tmp)
    tclean
}

test_x02 () {
    tsetup $FUNCNAME "Foreign filesystem mount test"
    mkdir -p a/tmp b/tmp
    techo "file" a/file b/file
    (set -x; sudo mount -t tmpfs tmpfs a/tmp)
    mkdir a/tmp/three b/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file b/tmp/one b/tmp/b b/tmp/three/file

    trun a   -als
    trun b   -als
    trun a b -alxs
    trun a b -alxts

    (set -x; sudo umount a/tmp)
    tclean
}

test_x03 () {
    tsetup $FUNCNAME "Dual foreign filesystem mount test"
    mkdir -p a/tmp b/tmp
    techo "file" a/file b/file
    (set -x; sudo mount -t tmpfs tmpfs a/tmp)
    (set -x; sudo mount -t tmpfs tmpfs b/tmp)
    mkdir a/tmp/three b/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file b/tmp/one b/tmp/b b/tmp/three/file

    trun a   -als
    trun b   -als
    trun a b -alxs
    trun a b -alxts

    (set -x; sudo umount a/tmp)
    (set -x; sudo umount b/tmp)
    tclean
}

test_x04 () {
    tsetup $FUNCNAME "Foreign filesystem mount test, non-existing right"
    mkdir -p a/tmp b
    techo "file" a/file b/file
    (set -x; sudo mount -t tmpfs tmpfs a/tmp)
    mkdir a/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file

    trun a   -als
    trun b   -als
    trun a b -alxs

    (set -x; sudo umount a/tmp)
    tclean
}

test_x05 () {
    tsetup $FUNCNAME "Scan with exclusion"
    mkdir -p a/tmp
    techo "file" a/file
    mkdir a/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file

    trun -als -X tmp --format="{arrow}  {mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {type}  {fullpath}" a

    tclean
}

test_x06 () {
    tsetup $FUNCNAME "Compare with exclusion"
    mkdir -p a/tmp b/tmp
    techo "file" a/file b/file
    mkdir a/tmp/three b/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file b/tmp/one b/tmp/b b/tmp/three/file

    #trun a   -als
    #trun b   -als
    trun a b -als -X tmp

    tclean
}

#=============================================================================



# Basic tests
tests="$tests 01 01b 02 02b 03 03b 04 04b"

# Coverage tests
tests="$tests c01"

# Scan-file tests
tests="$tests s01 s02 s03 s04 s05 s06 s07 s08"

# Ordering tests
tests="$tests o01 o02"

# Top-level type tests
tests="$tests t01 t02 t03 t04"

# Permission tests
tests="$tests p01 p02 p03 p04"

# Exclusion tests
tests="$tests x01 x02 x03 x04 x05 x06"


if [[ $# -gt 0 ]]; then
    for t in "$@"; do
        test_${t}
    done
else
    # Execute the tests
    for t in $tests; do
        test_${t}
    done
fi
