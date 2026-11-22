
echo "Loading $testfile: Permission tests"

all=(0501 0502 0503 0504 0505 0506 0507 0508 0509)


test_0501 () {
    tsetup $FUNCNAME "Permission denied top-level dir test" \
        "- Shall return 1, PermissionError: [Errno 13] Permission denied: 'a'"
    mkdir -p a
    touch a/file
    chmod 0000 a

    dirscan a -al

    chmod +rwx a
}

test_0502 () {
    tsetup $FUNCNAME "Permission denied in file" \
        "- Shall return 1 and 1 ERROR in output"
    mkdir -p a
    techo "file" a/file
    chmod 0000 a/file

    dirscan a -als

    chmod +rwx a/file
}

test_0503 () {
    tsetup $FUNCNAME "Permission denied in directory" \
        "- Shall return 1 and 1 error reading a directory"
    mkdir -p a/one
    touch a/one/file
    chmod 0000 a/one

    dirscan a -als

    chmod +rwx a/one
}

test_0504 () {
    tsetup $FUNCNAME "Permission denied in comparisons, file compare" \
        "- Shall return 1 and 1 ERROR in file compare"
    mkdir -p a b
    techo "file" a/file b/file
    chmod 0000 a/file

    dirscan -als a b

    chmod +rwx a/file
}

test_0505 () {
    tsetup $FUNCNAME "Permission denied in comparisons, file compare, both sides" \
        "- Shall return 1 and 1 ERROR in file compare"
    mkdir -p a b
    techo "file" a/file b/file
    chmod 0000 a/file b/file

    dirscan -als a b

    chmod +rwx a/file
}

test_0506 () {
    tsetup $FUNCNAME "Permission denied in comparisons, dir compare" \
        "- Will result in changed dir and permission denied"
    mkdir -p a/one b/one
    chmod 0000 a/one

    dirscan -als a b

    chmod +rwx a/one
}

test_0507 () {
    tsetup $FUNCNAME "Permission denied in comparisons, dir compare, both sides" \
        "- Directories are compared equal, with 2 permission denied"
    mkdir -p a/one b/one
    chmod 0000 a/one b/one

    dirscan -als a b

    chmod +rwx a/one b/one
}

test_0508 () {
    tsetup $FUNCNAME "Permission denied in file" \
        "- scanfile should be missing ./file"
    mkdir -p a
    echo "file" >a/file
    chmod 0000 a/file

    dirscan a -o scanfile.txt
    tcmd cat scanfile.txt

    chmod +rwx a/file
}

test_0509 () {
    tsetup $FUNCNAME "Permission denied in directory" \
        "- scanfile contains ./one, and missing ./one/file due to "\
        "  permission denied in its parent directory"
    mkdir -p a/one
    touch a/one/file
    chmod 0000 a/one

    dirscan a -o scanfile.txt
    tcmd cat scanfile.txt

    chmod +rwx a/one
}
