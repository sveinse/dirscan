
echo "Loading $testfile: Encoding error tests"

all=(0701 0702 0703 0704)


mk_encerr () {
    while [[ $# -gt 0 ]]; do
        mkdir -p $1
        tar -C $1 -xf ../data/07-encoding-error.tgz
        shift
    done
}


test_0701 () {
    tsetup $FUNCNAME "List filename with encoding errors"
    mk_encerr a

    dirscan a
}

test_0702 () {
    tsetup $FUNCNAME "Scanfile with filename encoding errors"
    mk_encerr a

    dirscan -o scanfile.txt a
    cat scanfile.txt
}

test_0703 () {
    tsetup $FUNCNAME "Read scanfile with filename encoding errors"
    mk_encerr a

    dirscan -o scanfile.txt a
    dirscan scanfile.txt
}

test_0704 () {
    tsetup $FUNCNAME "Compare scanfile with filename encoding errors"
    mk_encerr a

    dirscan -o scanfile.txt a
    dirscan -a scanfile.txt a
}
