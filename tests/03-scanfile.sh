
echo "Loading $testfile: Scanfile tests"

all=(0301 0302 0303 0304 0305 0306 0307 0308 0309 0310)


test_0301 () {
    tsetup $FUNCNAME "Save scan file" \
        "- See test 0101/0102"
    mk_dir a

    dirscan a -o scanfile.txt
    tcmd cat scanfile.txt
}

test_0302 () {
    tsetup $FUNCNAME "List files from scan file"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --input scanfile.txt
}

test_0303 () {
    tsetup $FUNCNAME "Compare dir with scan file, left" \
        "- Shall list all as equal"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --input scanfile.txt a
}

test_0304 () {
    tsetup $FUNCNAME "Compare dir with scan file, right" \
        "- Shall list all as equal"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --right a scanfile.txt
}

test_0305 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir left" \
        "- Lists all equal, with d only in left"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -als --input scanfile.txt a
}

test_0306 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir left, traversed" \
        "- Lists all equal, with d and sub-objects only in left"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -alst --input scanfile.txt a
}

test_0307 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir right" \
        "- Lists all equal, with d only in right"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -als --right a scanfile.txt
}

test_0308 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir right, traversed" \
        "- Lists all equal, with d and sub-objects only in right"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -alst --right a scanfile.txt
}

test_0309 () {
    tsetup $FUNCNAME "Compare scanfile with scanfile" \
        "- List all as equal"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --input --right scanfile.txt scanfile.txt
}

test_0310 () {
    tsetup $FUNCNAME "Generate scanfile from scanfile" \
        "- diff shall show no difference"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --input scanfile.txt -o scanfile2.txt
    tcmd diff scanfile.txt scanfile2.txt
}
