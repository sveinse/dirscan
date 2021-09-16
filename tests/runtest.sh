#!/bin/bash

ME="$(basename "$0")"
HERE="$(dirname "$0")"

cleanvenv=
py3=1
runall=

bin=bin
py2=python
py3=python3
if [[ "$(uname -o)" = "Msys" ]]; then
    bin=Scripts
    py2=py -2
    py3=py -3
fi

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
(C) 2018 Svein Seldal <sveinse@seldal.com>

  Run dirscan tests

Usage: $ME [OPTION] TESTS...

Options:
  -h, --help         Print this help
  -2, --py2          Test using python2
  -3, --py3          Test using python3
  --clean            Clean previous venvs
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
            --clean)
                cleanvenv=1
                ;;
            --debug)
                export PS4='   --->  $LINENO:  '
                set -x
                ;;
            -h|--help)
                usage
                exit 1
                ;;
            -2|--py2)
                py3=
                ;;
            -3|--py3)
                py3=1
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


    # -- Setup the testing venvs
    if [[ "$py3" ]]; then
        venv="$(pwd)/venv3"
        [[ "$cleanvenv" ]] && rm -rf $venv
        if [[ ! -d "$venv" ]]; then
            log "Setting up py3 virtual environment in $venv"
            (set -ex;
            $py3 -m venv $venv
            cd $HERE/..
            $venv/$bin/pip install -e .
            ) || exit 1
        fi
    else
        venv="$(pwd)/venv2"
        [[ "$cleanvenv" ]] && rm -rf $venv
        if [[ ! -d "$venv" ]]; then
            log "Setting up py2 virtual environment in $venv"
            (set -ex;
            $py2 -m virtualenv $venv
            cd $HERE/..
            $venv/$bin/pip install -e .
            ) || exit 1
        fi
    fi
    ds="$venv/$bin/dirscan"


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
