
echo "Loading $testfile: Scanfile tests"

all=(0301 0302 0303 0304 0305 0306 0307 0308 0309 0310 0311 0312 0313 0314\
     0315 0316 0317 0318 0319 0320 0321 0322 0323)


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
    dirscan -als scanfile.txt
}

test_0303 () {
    tsetup $FUNCNAME "Compare dir with scan file, left" \
        "- Shall list all as equal"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als scanfile.txt a
}

test_0304 () {
    tsetup $FUNCNAME "Compare dir with scan file, right" \
        "- Shall list all as equal"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als a scanfile.txt
}

test_0305 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir left" \
        "- Lists all equal, with d only in left"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -als scanfile.txt a
}

test_0306 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir left, traversed" \
        "- Lists all equal, with d and sub-objects only in left"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -alst scanfile.txt a
}

test_0307 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir right" \
        "- Lists all equal, with d only in right"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -als a scanfile.txt
}

test_0308 () {
    tsetup $FUNCNAME "Compare dir with scan file, changed dir right, traversed" \
        "- Lists all equal, with d and sub-objects only in right"
    mk_dir a

    dirscan a -o scanfile.txt
    rm -r a/d
    dirscan -alst a scanfile.txt
}

test_0309 () {
    tsetup $FUNCNAME "Compare scanfile with scanfile" \
        "- List all as equal"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als scanfile.txt scanfile.txt
}

test_0310 () {
    tsetup $FUNCNAME "Generate scanfile from scanfile" \
        "- diff shall show no difference"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als scanfile.txt -o scanfile2.txt
    tcmd diff scanfile.txt scanfile2.txt
}

test_0311 () {
    tsetup $FUNCNAME "Empty scan file"
    touch scanfile.txt

    dirscan -als scanfile.txt
}

test_0312 () {
    tsetup $FUNCNAME "Scan file with permission denied"
    touch scanfile.txt
    chmod 000 scanfile.txt

    dirscan -als scanfile.txt
}

test_0313 () {
    tsetup $FUNCNAME "Non-existing scan file"

    dirscan -als scanfile.txt
}

test_0314 () {
    tsetup $FUNCNAME "Corrupt scan file, missing header"
    cat <<EOF >scanfile.txt
Foobar
EOF

    dirscan -als scanfile.txt
}

test_0315 () {
    tsetup $FUNCNAME "Corrupt scan file, unknown version"
    cat <<EOF >scanfile.txt
#!ds:v7
EOF

    dirscan -als scanfile.txt
}

test_0316 () {
    tsetup $FUNCNAME "Test empty scan-file"
    cat <<EOF >scanfile.txt
#!ds:v1
EOF

    dirscan -als scanfile.txt
}

test_0317 () {
    tsetup $FUNCNAME "Incorrect top-level scanfile entry"
    cat <<EOF >scanfile.txt
#!ds:v1
d,,16877,1000,1000,1529323497,,foo
EOF

    dirscan -als scanfile.txt
}

test_0318 () {
    tsetup $FUNCNAME "Testing orphan in scanfile"
    cat <<EOF >scanfile.txt
#!ds:v1
d,,16877,1000,1000,1529323497,,./foo
EOF

    dirscan -als scanfile.txt
}

test_0319 () {
    tsetup $FUNCNAME "Testing incorrect file"
    cat <<EOF >scanfile.txt
#!ds:v1
d,,16877,1000,1000,1529323497
EOF

    dirscan -als scanfile.txt
}

test_0320 () {
    tsetup $FUNCNAME "Testing incorrect size"
    cat <<EOF >scanfile.txt
#!ds:v1
d,error,16877,1000,1000,1529323497,,.
EOF

    dirscan -als scanfile.txt
}

test_0321 () {
    tsetup $FUNCNAME "Testing incorrect mode"
    cat <<EOF >scanfile.txt
#!ds:v1
d,,,1000,1000,1529323497,,.
EOF

    dirscan -als scanfile.txt
}

test_0322 () {
    tsetup $FUNCNAME "Simple directory scan using prefix"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --prefix d scanfile.txt
}

test_0323 () {
    tsetup $FUNCNAME "Compare directory scan using prefix"
    mk_dir a

    dirscan a -o scanfile.txt
    dirscan -als --prefix d scanfile.txt a/d
}
