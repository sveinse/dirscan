"""Convert old scanfile format to new format."""
#
# Copyright (C) 2010-2026 Svein Seldal
# This code is licensed under MIT license (see LICENSE for details)
# URL: https://github.com/sveinse/dirscan
#
# This script reads a scanfile in the old format and writes it out
# in the new format.

import argparse

from dirscan.scanfile import file_quote, file_unquote, check_header


parser = argparse.ArgumentParser(
    description="Convert old scanfile format to new format."
)
parser.add_argument("input_file", type=str, help="Path to the old scanfile")
parser.add_argument("output_file", type=str, help="Path to the new scanfile")

opts = parser.parse_args()

filename = opts.input_file

# First pass reading entire file into memory
with (
    open(filename, 'r', encoding='utf-8', errors='surrogateescape') as infile,
    open(opts.output_file, 'w', encoding='utf-8', errors='surrogateescape') as outfile,
):

    # Check the scanfile header
    firstline = infile.readline()
    check_header(firstline, filename)
    outfile.write(firstline)

    lineno = 1
    for line in infile:
        lineno += 1

        # Ignore empty line and lines with comments
        if not line.rstrip() or line[0] == '#':
            outfile.write(line)
            continue

        # Parse the line record
        args = [file_unquote(e) for e in line.rstrip().split(',', maxsplit=8)]
        if len(args) != 8:
            raise ValueError("{filename}:{lineno}: Missing or excess file fields "
                             f"(got {len(args)}, want 8)")

        try:
            # File mode. Ocal in new format, decimal in old format
            args[2] = f"{int(args[2], 10):o}"

            # Modification time. Hex in new format, float in old format
            args[5] = f"{int(float(args[5])):x}"

        except ValueError as e:
            raise ValueError(f"{filename}:{lineno}: Invalid field value: {e}") from e

        out = ",".join([file_quote(e) for e in args]) + "\n"
        outfile.write(out)
