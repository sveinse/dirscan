"""Tool to move files on the right that are equal to files on the left."""
from pathlib import Path
import argparse
import dirscan

parser = argparse.ArgumentParser(description="""
Move files on the right that are equal to files on the left. It compares
left and right directories or scanfiles, and for files that are equal, it
moves the file from the right directory to a destination directory,
keeping the same relative path. Use --path to specify the base path for the
right files, and --dest to specify the destination base path for the moved
files. Use --go to actually perform the move; otherwise, it will just print
what would be done.
"""
)
parser.add_argument("left", help="Left directory")
parser.add_argument("right", help="Right directory")
parser.add_argument("--path", required=True, help="Specific path to right files")
parser.add_argument("--dest", required=True, help="Destination directory for removed files")
parser.add_argument("--go", action="store_true", help="Actually perform the move")
parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
opts = parser.parse_args()


def move_file(fullpath: Path, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    fullpath.rename(dest_path)


leftroot = dirscan.open_dir_or_scanfile(opts.left)
rightroot = dirscan.open_dir_or_scanfile(opts.right)

shadb = dirscan.scan_shadb([leftroot, rightroot])

for path, (left, right) in dirscan.walkdirs([leftroot, rightroot]):
    srcpath = Path(opts.path) / path
    dstpath = Path(opts.dest) / path

    # Ignore all non-files and missing files
    if not isinstance(right, dirscan.FileObj) or not srcpath.is_file():
        continue

    # Find equal files placed in the same place left and right
    change, text = dirscan.obj_compare2((left, right), ignores="tugp")
    if change == "equal":
        if opts.go:
            move_file(srcpath, dstpath)
        print(f"M  {path}")
        continue

    # Check for files with same hashsum in shadb
    sha_files = shadb.get(right.hashsum, [])
    if len(sha_files) > 1:         
        is_in_left = any(index == 0 for index, _ in sha_files)
        c = ' '
        if opts.go and is_in_left:
            c = 'H'
            move_file(srcpath, dstpath)
        if opts.verbose or (opts.go and is_in_left):
            print(f"{c}  {path}")
        if opts.verbose:
            for index, sha_file in sha_files:
                location = "<<<" if index == 0 else ">>>"
                print(f"       {location} {sha_file.fullpath}")
        continue

    # Remaining files
    if opts.verbose:
        print(f"   {path}")
