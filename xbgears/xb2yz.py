#!/usr/bin/env python
"""
xb2yz - Convert a 1D XBeach x.grd / *.dep profile into a two-column *.yz file.

x.grd and the *.dep file must contain the same number of values (a 1D XBeach
grid, typically written on a single row). The output file has two
whitespace-separated columns (cross-shore distance, bed level), one point per
line and no header.
"""

import argparse
import sys
from pathlib import Path

import numpy as np


def xb_to_yz(
    dep="bed.dep",
    out="bathy.yz",
    xgrd="x.grd",
    outdir="YZ",
    cwd=None,
) -> Path:
    """
    Convert a 1D XBeach x.grd / *.dep profile into a two-column *.yz file.

    Args:
        dep (str): Input *.dep file name
        out (str): Output *.yz file name
        xgrd (str): Input x-grid file name
        outdir (str): Output folder name
        cwd (Path): Working directory to resolve relative paths against
            (defaults to the current directory)

    Returns:
        Path: Path to the written *.yz file
    """
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    xgrd_path = cwd / xgrd
    dep_path = cwd / dep

    for p in (xgrd_path, dep_path):
        if not p.is_file():
            sys.exit(f"Error: required input file not found: {p}")

    x = np.loadtxt(xgrd_path).ravel()
    z = np.loadtxt(dep_path).ravel()

    if x.size != z.size:
        sys.exit(
            f"Error: size mismatch - {xgrd} has {x.size} values, "
            f"{dep} has {z.size} values."
        )

    outdir_path = cwd / outdir
    outdir_path.mkdir(parents=True, exist_ok=True)
    out_path = outdir_path / out

    # Pass an open file handle: np.savetxt would compress a path ending in
    # e.g. ".gz" / ".xz", so avoid relying on the file name.
    with open(out_path, "w") as f:
        np.savetxt(f, np.column_stack((x, z)), fmt="%.3f")

    print(f"Wrote {x.size} points to {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        prog="xb2yz",
        description="Convert a 1D XBeach x.grd / *.dep profile into a two-column *.yz file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  xb2yz                                      # Use defaults (x.grd, bed.dep -> YZ/bathy.yz)
  xb2yz --dep bed.dep --out bathy.yz         # Explicit file names
        """,
    )
    parser.add_argument("--dep", default="bed.dep", help="Input *.dep file name (default: bed.dep)")
    parser.add_argument("--out", default="bathy.yz", help="Output *.yz file name (default: bathy.yz)")
    parser.add_argument("--xgrd", default="x.grd", help="Input x-grid file name (default: x.grd)")
    parser.add_argument("--outdir", default="YZ", help="Output folder name (default: YZ)")
    args = parser.parse_args()

    xb_to_yz(
        dep=args.dep,
        out=args.out,
        xgrd=args.xgrd,
        outdir=args.outdir,
    )


if __name__ == "__main__":
    main()
