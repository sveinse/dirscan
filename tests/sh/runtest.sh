#!/bin/bash

ME="$(basename "$0")"
HERE="$(dirname "$0")"

cleanvenv=
runall=
ds="uv run dirscan"

# -- Helpers
log () {
    echo "$ME: $*"
}
quit () {
    err=$1
    shift
    [[ $# -gt 0 ]] && log "$@"
    exit $err
}

usage () {
    cat <<EOF
$ME -- Dirscan tester
(C) 2018 Svein Seldal

    Run dirscan tests

Usage: $ME [OPTION] TESTS...

Options:
    -h, --help         Print this help
    --all              Run all tests
EOF
}


main() {
    declare -A opts
    while [[ "$#" -gt 0 ]]
    do
        case "$1" in
            --all)
                runall=1
                ;;
            --debug)
                export PS4='   --->  $LINENO:  '
                set -x
                ;;
            -h|--help)
                usage
                exit 1
                ;;
            --)
                shift
                break
                ;;
            -*)
                quit 1 "Unknown argument '$1'"
                ;;
            *)
                args+=("$1")
                ;;
        esac
        shift
    done
    # Catch up any args after -- as well
    while [[ "$#" -gt 0 ]]; do
        args+=("$1")
        shift
    done

    # -- Check remaining arg count
    if [[ ${#args[@]} -lt 1 ]] && [[ -z "$runall" ]]; then
        usage
        quit 1 "Too few arguments"
    fi

    # -- Read all test files
    testfiles=(??-*.sh)
    alltests=()
    for testfile in "${testfiles[@]}"; do
        [[ ! -f "$testfile" ]] && continue
        source "$testfile"
        if [[ "$all" ]]; then
            alltests+=("${all[@]}")
        fi
    done

    # -- Execute the tests
    if [[ "$runall" ]]; then
        tests=("${alltests[@]}")
    else
        tests=("${args[@]}")
    fi

    for name in "${tests[@]}"; do
        test_${name}
        tclean
    done
}

# -- Test functions
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

# -- RUN
main "$@"
