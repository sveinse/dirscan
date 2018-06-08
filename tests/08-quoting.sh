
echo "Loading $testfile: Filename quoting tests"

all=(0801 0802 0803 0804)


mk_chars () {
    d=$1
    mkdir -p $d
    touchi() {
        h="$(printf %02x $1)"
        touch "$(printf $d/c$h.%b. "\\x$h")"
    }
    for ((i=1; i<=255; i++)); do touchi $i; done
    touch a/z.æ.
    touch a/z.ø.
    touch a/z.å.
}

test_0801 () {
    tsetup $FUNCNAME "Character files"
    mk_chars a

    dirscan a
}

test_0802 () {
    tsetup $FUNCNAME "Scanfile with character files"
    mk_chars a

    dirscan -o scanfile.txt a
    cat scanfile.txt
}

test_0803 () {
    tsetup $FUNCNAME "Scanfile with character files"
    mk_chars a

    dirscan -o scanfile.txt a
    dirscan --input scanfile.txt
}

test_0804 () {
    tsetup $FUNCNAME "Compare scanfile with filename with character files"
    mk_chars a

    dirscan -o scanfile.txt a
    dirscan -a --input scanfile.txt a
}
