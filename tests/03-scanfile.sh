
echo "Loading $testfile: Scanfile tests"

all=(0301 0302 0303 0304 0305 0306 0307 0308 0309 0310 0311 0312)


test_0301 () {
    tsetup $FUNCNAME "Save scan file" \
        "- See test 0101/0102"
    mk_dir a

    dirscan a -o scanfile.txt
    tcmd cat scanfile.txt
}

test_0302 () {
    tsetup $FUNCNAME "Read from scan file" \
        "- See test 0301, 0101"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --input scanfile.txt
}

test_0303 () {
    tsetup $FUNCNAME "Compare dir with scan file, left"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --input scanfile.txt a
}

test_0312 () {
    tsetup $FUNCNAME "Compare dir with scan file, right"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --right a scanfile.txt
}

test_0304 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -als --input scanfile.txt a
}

test_0305 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir, traversed"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -alst --input scanfile.txt a
}

test_0306 () {
    tsetup $FUNCNAME "Compare scanfile with scanfile"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --input --right scanfile.txt scanfile.txt
}

test_0307 () {
    tsetup $FUNCNAME "Generate scanfile from scanfile"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --input scanfile.txt -o scanfile2.txt
    tcmd diff scanfile.txt scanfile2.txt
}

test_0308 () {
    tsetup $FUNCNAME "Scan file with excluded fs" \
        "- ./tmp should not be listed in scanfile"
    mkdir -p a/tmp
    techo "file" a/file
    tcmd sudo mount -t tmpfs tmpfs a/tmp
    mkdir a/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file

    dirscan -x -o scanfile.txt a
    tcmd cat scanfile.txt

    tcmd sudo umount a/tmp
}

test_0309 () {
    tsetup $FUNCNAME "Scan file comparison with excluded fs" \
        "- ./tmp should not be listed as excluded, only right"
    mkdir -p a/tmp
    techo "file" a/file
    tcmd sudo mount -t tmpfs tmpfs a/tmp
    mkdir a/tmp/three
    touch a/tmp/one a/tmp/a a/tmp/three/file

    dirscan -x -o scanfile.txt a
    dirscan -alsx --input scanfile.txt a

    tcmd sudo umount a/tmp
}

test_0310 () {
    tsetup $FUNCNAME "Permission denied in file" \
        "- scanfile should be missing ./file"
    mkdir -p a
    echo "file" >a/file
    chmod 0000 a/file

    dirscan a -o scanfile.txt
    tcmd cat scanfile.txt

    chmod +rwx a/one a/file
}

test_0311 () {
    tsetup $FUNCNAME "Permission denied in directory" \
        "- scanfile contains ./one, but is otherwise empty due to "\
        "  permission denied"
    mkdir -p a/one
    touch a/one/file
    chmod 0000 a/one

    dirscan a -o scanfile.txt
    tcmd cat scanfile.txt

    chmod +rwx a/one
}

# test_0312 used above
