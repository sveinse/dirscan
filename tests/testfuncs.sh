
ds="$(realpath ../venv3/bin/dirscan)"

tsetup() {
    t="$1"

    echo "********************************************************************"
    echo "***  TEST $t"
    echo "***  $2"
    echo "********************************************************************"

    rm -rf "$t"
    mkdir -p $t
    cd $t
}

tclean() {
    cd ..
    rm -rf $t
    echo "********************************************************************"
    echo
    echo
}

trun() {
    ( export PS4='++>  '
      set -x
      $ds "$@"
      status_code=$?
    )
}

techo() {
    text="$1"
    shift
    for f in "$@"; do
        echo "$text" >$f
    done
}
