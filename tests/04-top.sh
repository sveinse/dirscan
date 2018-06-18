
echo "Loading $testfile: Top-file tests"

all=(0401 0402 0403 0404 0405 0406 0407 0408 0409 0410 0411 0412 0413 0414 0415 \
     0416)


test_0401 () {
    tsetup $FUNCNAME "Symlink top object" \
        "- Shall fail with: No such file or directory: 'a'"
    ln -s foo a

    dirscan a
}

test_0402 () {
    tsetup $FUNCNAME "Empty file top object" \
        "- Shall fail with: Not a directory: 'a'"
    touch a

    dirscan a
}

test_0403 () {
    tsetup $FUNCNAME "Permission denied top-level dir" \
        "- Shall fail with: Permission denied: 'a'"
    mkdir -p a
    touch a/file
    chmod 0000 a

    dirscan a

    chmod +rwx a
}

test_0404 () {
    tsetup $FUNCNAME "File top-level object" \
        "- Shall fail with: Invalid scanfile"
    techo "file" a

    dirscan a
}

test_0405 () {
    tsetup $FUNCNAME "Top-level scan with symlink reference"
    mkdir -p b
    touch b/file
    ln -s b a

    dirscan a
}

test_0406 () {
    tsetup $FUNCNAME "Test top-level dir compare with two symlinks" \
        "- Shall list files as equal"
    mkdir -p b
    touch b/file
    ln -s b a

    dirscan -a a a
}

test_0407 () {
    tsetup $FUNCNAME "Test top-level dir compare with slash left" \
        "- A bug where files missed slash, e.g. '.file' (WRONG)"
    mkdir -p a
    touch a/file

    dirscan -a a/ a
}

test_0408 () {
    tsetup $FUNCNAME "Test top-level dir compare with slash right" \
        "- A bug where files missed slash, e.g. '.file' (WRONG)"
    mkdir -p a
    touch a/file

    dirscan -a a a/
}

test_0409 () {
    tsetup $FUNCNAME "Test top-level dir compare with slash both" \
        "- A bug where files missed slash, e.g. '.file' (WRONG)"
    mkdir -p a
    touch a/file

    dirscan -a a/ a/
}

test_0410 () {
    tsetup $FUNCNAME "Test top-level dir compare with abs path left" \
        "- A bug where files missed slash, e.g. './/file' (WRONG)"
    mkdir -p a
    touch a/file

    dirscan -a $PWD/a a
}

test_0411 () {
    tsetup $FUNCNAME "Test top-level dir compare with abs path right" \
        "- A bug where files missed slash, e.g. './/file' (WRONG)"
    mkdir -p a
    touch a/file

    dirscan -a a $PWD/a
}

test_0412 () {
    tsetup $FUNCNAME "Test top-level dir compare with abs path both" \
        "- A bug where files missed slash, e.g. './/file' (WRONG)"
    mkdir -p a
    touch a/file

    dirscan -a $PWD/a $PWD/a
}

# FIXME: This isn't pretty
xdirs="-X bin -X usr -X lib -X var -X opt -X tmp -X sbin -X etc -X snap -X boot -X root"

test_0413 () {
    tsetup $FUNCNAME "Scan root path" \
        "- A bug where files had incorrect slash, e.g. '.file' (WRONG)"

    dirscan -x / $xdirs
}

test_0414 () {
    tsetup $FUNCNAME "Scan root path to scan-file"

    dirscan -o scanfile.txt -x / $xdirs
    tcmd cat scanfile.txt
}

test_0415 () {
    tsetup $FUNCNAME "Scan root path to scan-file, read back"

    dirscan -o scanfile.txt -x / $xdirs
    dirscan -als scanfile.txt
}

test_0416 () {
    tsetup $FUNCNAME "Scan root path to scan-file, compare with root"

    dirscan -o scanfile.txt -x / $xdirs
    dirscan -ax scanfile.txt / $xdirs
}
