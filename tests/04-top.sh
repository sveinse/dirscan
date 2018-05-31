
echo "Loading $testfile: Top-file tests"

all=(0401 0402 0403 0404)


test_0401 () {
    tsetup $FUNCNAME "Symlink top object"
    ln -s foo a

    dirscan a
}

test_0402 () {
    tsetup $FUNCNAME "Empty file top object"
    touch a

    dirscan a
}

test_0403 () {
    tsetup $FUNCNAME "Permission denied top-level dir"
    mkdir -p a
    touch a/file
    chmod 0000 a

    dirscan a

    chmod +rwx a
}

test_0404 () {
    tsetup $FUNCNAME "Random file top-level object"
    techo "file" a

    dirscan a
}
