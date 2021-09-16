#import os
from pytest import raises
#from pprint import pprint

import dirscan as ds

# pylint: disable-all


def test_no_arguments():
    ''' Test scanning a dir with no access '''

    with raises(SystemExit) as exc:
        ds.main([])
    assert int(exc.value.code) == 2


def test_too_many_arguments():

    with raises(SystemExit) as exc:
        ds.main(["a", "b", "c"])
    assert int(exc.value.code) == 2


def test_args_help():

    with raises(SystemExit) as exc:
        ds.main(["--help"])
    assert int(exc.value.code) == 0


def test_args_format_help():

    with raises(SystemExit) as exc:
        ds.main(["--format-help"])
    assert int(exc.value.code) == 1


def test_args_version(capsys):

    with raises(SystemExit) as exc:
        ds.main(["--version"])
    assert int(exc.value.code) == 0
    captured = capsys.readouterr()
    assert captured.out == "dirscan " + ds.__version__ + "\n"
