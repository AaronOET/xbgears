#!/usr/bin/env python
"""
Command-line utility to display descriptions of xbgears functionality.
"""

import argparse
import sys
from textwrap import dedent

TOOL_DESCRIPTIONS = {
    'xb2xyz': """
        Convert XBeach x.grd / y.grd / *.dep grid files into a *.xyz point file.

        x.grd and y.grd must have the same shape as the *.dep file (rows =
        ny+1, columns = nx+1, whitespace-separated floats, XBeach grid
        format). If params.txt exists in the working directory, xori/yori
        are read from it and added to the x/y coordinates.

        Examples:
            xb2xyz                                # Use defaults, write XYZ/001.xyz
            xb2xyz --dep bed.dep --out 001.xyz     # Explicit file names
    """,
    'xyz2xb': """
        Convert a *.xyz point file into x.grd / y.grd / bed.dep files.

        Reverse of xb2xyz. The *.xyz file must contain whitespace-separated
        "x y z" rows; each row becomes one line in x.grd, y.grd and bed.dep.

        Examples:
            xyz2xb                                     # Use defaults, write XBGRID/{x.grd,y.grd,bed.dep}
            xyz2xb --xyz 001.xyz --outdir XBGRID        # Explicit file names
    """,
}


def main():
    parser = argparse.ArgumentParser(
        prog='xbgears-info',
        description='Display descriptions of xbgears commands',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'tool',
        nargs='?',
        choices=list(TOOL_DESCRIPTIONS.keys()),
        help='Tool name to describe (omit to list all tools)',
    )
    args = parser.parse_args()

    if args.tool:
        print(f"\n--- {args.tool} ---")
        print(dedent(TOOL_DESCRIPTIONS[args.tool]))
    else:
        print("\nXBGEARS — XBeach grid / XYZ point file conversion commands\n")
        for tool, desc in TOOL_DESCRIPTIONS.items():
            first_line = dedent(desc).strip().splitlines()[0]
            print(f"  {tool:<14} {first_line}")
        print("\nRun 'xbgears-info <tool>' for details on a specific command.")


if __name__ == "__main__":
    main()
