
echo "Loading $testfile: Comparing tests"

all=(0201 0202 0203 0204 0205)


test_0201 () {
    tsetup $FUNCNAME "Compare test, changed link"
    mkdir a b
    ln -s foo a/link
    ln -s bar b/link

    dirscan a b
}

test_0202 () {
    tsetup $FUNCNAME "Compare test, changed file type"
    mkdir a b
    touch a/file
    ln -s foo b/file

    dirscan a b
}

test_0203 () {
    tsetup $FUNCNAME "Compare test, only left"
    mkdir a b
    touch a/file

    dirscan a b
}

test_0204 () {
    tsetup $FUNCNAME "Compare test, only right"
    mkdir a b
    touch b/file

    dirscan a b
}

test_0205 () {
    tsetup $FUNCNAME "Compare test, file changed"
    mkdir a b
    techo "one" a/file
    techo "two" b/file

    dirscan a b
}
