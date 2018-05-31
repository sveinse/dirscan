#!/bin/bash

ds="$(realpath ../venv3/bin/dirscan)"


tsetup() {
    dstest="$1"
    shift

    echo "********************************************************************"
    echo "***  TEST $dstest"
    for l in "$@"; do
        echo "***  $l"
    done
    echo "********************************************************************"

    rm -rf "$dstest"
    mkdir -p $dstest
    cd $dstest
}

tclean() {
    if [[ "$dstest" ]]; then
        cd ..
        rm -rf $dstest
        echo "********************************************************************"
        echo
        echo
    fi
}

tcmd() {
    ( export PS4='++>  '
      set -x
      "$@"
    )
}

trun() {
    tcmd "$@"
    echo "++>  STATUS CODE: $?"
}

dirscan() {
    trun $ds "$@"
}

techo() {
    text="$1"
    shift
    for f in "$@"; do
        echo "$text" >$f
    done
}


testfiles=(??-*.sh)
alltests=()
for testfile in "${testfiles[@]}"; do
    [[ ! -f "$testfile" ]] && continue
    source "$testfile"
    if [[ "$all" ]]; then
        alltests+=("${all[@]}")
    fi
done



if [[ $# -gt 0 ]]; then
    for name in "$@"; do
        test_${name}
        tclean
    done
else
    # Execute all tests
    for name in "${alltests[@]}"; do
        test_${name}
        tclean
    done
fi
