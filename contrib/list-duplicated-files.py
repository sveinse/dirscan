"""Tool to list duplicated files in a directory or scanfile."""
import argparse
import dirscan

parser = argparse.ArgumentParser(description="""
Tool to list duplicated files in a directory or scanfile. It scans the specified
directory or scanfile and identifies files with identical content based on
their SHA hashes. The output lists each SHA hash followed by the relative paths
of the duplicated files.
"""
)
parser.add_argument("dir", help="Directory or scanfile to check for duplicated files")
parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
opts = parser.parse_args()


root = dirscan.open_dir_or_scanfile(opts.dir)

shadb = dirscan.scan_shadb([root])

for sha, shafiles in shadb.items():
    if len(shafiles) <= 1:
        continue

    if len(shafiles) > 1:
        print(f"{sha.hex()}")
        for _, shafile in shafiles:
            relpath = shafile.fullpath.relative_to(root.fullpath)
            print(f"    {relpath}")
        continue
