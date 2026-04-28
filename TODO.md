## sveinse 2018-05-20:

- Scan-files might not be properly parsed given the change in DirObj()

- Automatic script for uploading PyPi?

      python -m pip install --upgrade setuptools wheel
      python setup.py sdist bdist_wheel
      python -m pip install twine
      twine upload --repository-url https://test.pypi.org/legacy/ dist/*
      twine upload -r pypi --repository-url https://upload.pypi.org/legacy/ dist/*

## sveinse 2018-05-19:

- `--summary` eats the given argument, which is not good


## sveinse 2018-05-18:

- Separate metric in scandirs() for errors? Problem is how to count
  the histograms when there is an partial error in only one of the trees.
  Should it count the whole compare as error, or the non-errored object?


## sveinse 2018-05-16:

- Perhaps file arguments given to dirscan should not be interpreted as scan
  files. It is hard to differentiate between incorrect usage vs the actual
  wanted scanfile usage
