
echo "Loading $testfile: Basic tests"

all=(0101 0102 0103 0104 0105 0106 0107 0108 0109)


mk_dir () {
    while [[ $# -gt 0 ]]; do
        mkdir -p $1 $1/d $1/f
        touch $1/a $1/d/a $1/d/b $1/e $1/f/a $1/f/b
        echo "foo" >$1/b
        ln -s b $1/c
        shift
    done
}


test_0101 () {
    tsetup $FUNCNAME "Simple directory scan" \
        "- List all files plainly"
    mk_dir a

    dirscan a
}

test_0102 () {
    tsetup $FUNCNAME "Simple directory scan, verbose" \
        "- List all file contents including sha and print summary"
    mk_dir a

    dirscan a -als
}

test_0103 () {
    tsetup $FUNCNAME "Simple equal directory comparison" \
        "- Shall print no difference"
    mk_dir a b

    dirscan a b
}

test_0104 () {
    tsetup $FUNCNAME "Simple equal directory comparison, verbose" \
        "- Shall list entries as equal"
    mk_dir a b

    dirscan a b -als
}

test_0105 () {
    tsetup $FUNCNAME "Basic compare difference" \
        "- Shall show d only in right"
    mk_dir a b
    rm -rf a/d

    dirscan a b
}

test_0106 () {
    tsetup $FUNCNAME "Basic compare difference, verbose" \
        "- Shall list all and show d only in right"
    mk_dir a b
    rm -rf a/d

    dirscan a b -als
}

test_0107 () {
    tsetup $FUNCNAME "Basic directory difference, traversed" \
        "- Shall show d only in right including sub-elements"
    mk_dir a b
    rm -rf a/d

    dirscan a b -t
}

test_0108 () {
    tsetup $FUNCNAME "Basic directory difference, traversed, verbose" \
        "- Shall list all and show d and sub elements of d only in right"
    mk_dir a b
    rm -rf a/d

    dirscan a b -alst
}

test_0109 () {
    tsetup $FUNCNAME "Simple directory scan, descending" \
        "- List all files in reverse" \
        "- Ref test 0101"
    mk_dir a

    dirscan a --reverse
}
