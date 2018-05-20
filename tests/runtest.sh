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

    trun a -al -cEs --summary
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

    trun a b -al -celrcLRtEx --summary
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

    trun a b -al -celrcLRtEx --summary
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

    trun a b -al -celrcLRtEx --summary -t
    tclean
}

test_05 () {
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

    trun a -al -cEs --summary
    trun b -al -cEs --summary
    trun a b -al -celrcLRtEx -X exclude -X l_exclude -X r_exclude --summary
    tclean
}


#=============================================================================
# Order tests
#=============================================================================

test_o01 () {
    tsetup $FUNCNAME "Basic directory scan"
    mk_dir a

    trun a
    tclean
}
test_o02 () {
    tsetup $FUNCNAME "Basic directory scan, reverse"
    mk_dir a

    trun a --reverse
    tclean
}


#=============================================================================
# Top-level tests
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

    trun a -al -cEs --summary

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

    trun a   -al -cEs --summary
    trun b   -al -cEs --summary
    trun a b -al -celrcLRtEx --summary

    chmod +rwx a/one a/file
    tclean
}

test_p04 () {
    tsetup $FUNCNAME "Dual permission denied in comparison"
    mkdir -p a/one b/one
    techo "file" a/one/file b/one/file
    techo "file" a/file b/file
    chmod 0000 a/one b/one a/file b/file

    trun a   -al -cEs --summary
    trun b   -al -cEs --summary
    trun a b -al -celrcLRtEx --summary

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

    trun -alx -cEsx --format="{arrow}  {mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {type}  {fullpath}" a --summary

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

    trun a   -al -cEs --summary
    trun b   -al -cEs --summary
    trun a b -al -x -celrcLRtEx --summary
    trun a b -al -x -t -celrcLRtEx --summary

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

    trun a   -al -cEs --summary
    trun b   -al -cEs --summary
    trun a b -al -x -celrcLRtEx --summary
    trun a b -al -x -t -celrcLRtEx --summary

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

    trun a   -al -cEs --summary
    trun b   -al -cEs --summary
    trun a b -al -x -celrcLRtEx --summary

    (set -x; sudo umount a/tmp)
    tclean
}

test_x05 () {
    tsetup $FUNCNAME "Scan with exclusion"
    mkdir -p a/tmp
    techo "file" a/file
    mkdir a/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file

    trun -al -X tmp -cEsx --format="{arrow}  {mode_t}  {uid:5} {gid:5}  {size:>10}  {mtime}  {type}  {fullpath}" a --summary

    tclean
}

test_x06 () {
    tsetup $FUNCNAME "Compare with exclusion"
    mkdir -p a/tmp b/tmp
    techo "file" a/file b/file
    mkdir a/tmp/three b/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file b/tmp/one b/tmp/b b/tmp/three/file

    #trun a   -al -cEs --summary
    #trun b   -al -cEs --summary
    trun a b -al -X tmp -celrcLRtEx --summary

    tclean
}

#=============================================================================



# Basic tests
tests="$tests 01 01b 02 02b 03 03b 04 04b 05"

# Ordering tests
tests="$tests o01 o02"

# Top-level tests
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
