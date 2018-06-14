
echo "Loading $testfile: Exclusions tests"

all=(0601 0602 0603 0604 0605 0606 0607 0608 0609 0610)


test_0601 () {
    tsetup $FUNCNAME "Foreign filesystem exclusion scan test" \
        "- a/tmp setup as foreign tmpfs" \
        "- Shall list a/tmp as excluded"
    mkdir -p a/tmp
    tcmd sudo mount -t tmpfs tmpfs a/tmp
    touch a/tmp/one

    dirscan -axs --format="{arrow}  {type}  {fullpath}" a

    tcmd sudo umount a/tmp
}

test_0602 () {
    tsetup $FUNCNAME "Foreign filesystem exclusion compare test" \
        "- Shall return 'directory only in right, left is excluded'"
    mkdir -p a/tmp b/tmp
    tcmd sudo mount -t tmpfs tmpfs a/tmp
    touch a/tmp/one b/tmp/one

    dirscan a b -axs

    tcmd sudo umount a/tmp
}

test_0603 () {
    tsetup $FUNCNAME "Foreign filesystem exclusion compare tes, traversed" \
        "- Shall return 'directory only in right, left is excluded'" \
        "  for all elements"
    mkdir -p a/tmp b/tmp
    tcmd sudo mount -t tmpfs tmpfs a/tmp
    touch a/tmp/one b/tmp/one

    dirscan a b -axst

    tcmd sudo umount a/tmp
}

test_0604 () {
    tsetup $FUNCNAME "Foreign filesystem exclusion compare test both sides" \
        "- Shall list ./tmp as excluded"
    mkdir -p a/tmp b/tmp
    tcmd sudo mount -t tmpfs tmpfs a/tmp
    tcmd sudo mount -t tmpfs tmpfs b/tmp
    touch a/tmp/one b/tmp/one

    dirscan a b -axs

    tcmd sudo umount a/tmp
    tcmd sudo umount b/tmp
}

test_0605 () {
    tsetup $FUNCNAME "Foreign filesystem mount test, foreign left, non-existing right" \
        "- Shall return 'Left excluded, not present in right'"
    mkdir -p a/tmp b
    tcmd sudo mount -t tmpfs tmpfs a/tmp
    touch a/tmp/one

    dirscan -axs a b

    tcmd sudo umount a/tmp
}

test_0606 () {
    tsetup $FUNCNAME "Foreign filesystem mount test, foreign right, non-existing left" \
        "- Shall return 'Right excluded, not present in left'"
    mkdir -p a/tmp b
    tcmd sudo mount -t tmpfs tmpfs a/tmp
    touch a/tmp/one

    dirscan -axs b a

    tcmd sudo umount a/tmp
}

test_0607 () {
    tsetup $FUNCNAME "Scan with exclusion path" \
        "- a/tmp shall be listed as excluded"
    mkdir -p a/tmp
    touch a/tmp/one

    dirscan -as -X tmp --format="{arrow}  {type}  {fullpath}" a
}

test_0608 () {
    tsetup $FUNCNAME "Compare with exclusion path" \
        "- a/tmp shall be listed as excluded"
    mkdir -p a/tmp b/tmp
    touch a/tmp/one b/tmp/one

    dirscan -as -X tmp a b
}

test_0609 () {
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

test_0610 () {
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
