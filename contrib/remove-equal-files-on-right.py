"""Tool to move files on the right that are equal to files on the left."""
from pathlib import Path
import argparse
import dirscan

parser = argparse.ArgumentParser(
    description="""
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
opts = parser.parse_args()

ldb = dirscan.open_dir_or_scanfile(opts.left)
rdb = dirscan.open_dir_or_scanfile(opts.right)

for path, objs in dirscan.walkdirs((ldb, rdb)):
    change, text = dirscan.obj_compare2(objs, ignores="tugp")

    if not isinstance(objs[0], dirscan.FileObj) or change != "equal":
        print(f"   {objs[0].objtype}  {path}")
        continue

    fullpath = Path(opts.path) / path if opts.path else path
    if not fullpath.is_file():
        print(f"?  {path}")
        continue

    dest_path = Path(opts.dest) / path
    if opts.go:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        fullpath.rename(dest_path)
    print(f"M  {path}  ->  {dest_path}")
