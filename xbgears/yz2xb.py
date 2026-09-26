#!/usr/bin/env python
"""
yz2xb - Convert a two-column *.yz profile file into 1D XBeach x.grd / bed.dep files.

Reverse of xb2yz. The *.yz file must contain whitespace-separated
"x z" rows (cross-shore distance, bed level; no header), with x strictly
increasing. x.grd and bed.dep are written as a 1D XBeach grid: all values
on a single row.
"""

import argparse
import sys
from pathlib import Path

import numpy as np


def yz_to_xb(
    yz="bathy.yz",
    dep="bed.dep",
    xgrd="x.grd",
    outdir="XBGRID",
    cwd=None,
) -> Path:
    """
    Convert a two-column *.yz profile file into 1D XBeach x.grd / bed.dep files.

    Args:
        yz (str): Input *.yz file name
        dep (str): Output *.dep file name
        xgrd (str): Output x-grid file name
        outdir (str): Output folder name
        cwd (Path): Working directory to resolve relative paths against
            (defaults to the current directory)

    Returns:
        Path: Path to the output folder containing x.grd and bed.dep
    """
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    yz_path = cwd / yz

    if not yz_path.is_file():
        sys.exit(f"Error: input file not found: {yz_path}")

    yz_data = np.loadtxt(yz_path, ndmin=2)
    if yz_data.shape[1] != 2:
        sys.exit(f"Error: expected 2 columns (x z) in {yz}, got shape {yz_data.shape}")

    x = yz_data[:, 0]
    z = yz_data[:, 1]

    if np.any(np.diff(x) <= 0):
        sys.exit(f"Error: x values in {yz} must be strictly increasing")

    outdir_path = cwd / outdir
    outdir_path.mkdir(parents=True, exist_ok=True)

    # XBeach 1D grid: all values on a single row
    for name, values in ((xgrd, x), (dep, z)):
        with open(outdir_path / name, "w") as f:
            f.write(" ".join(f"{v:.3f}" for v in values) + "\n")

    print(f"Wrote {xgrd}, {dep} ({x.size} points) to {outdir_path}")
    return outdir_path


def main():
    parser = argparse.ArgumentParser(
        prog="yz2xb",
        description="Convert a two-column *.yz profile file into 1D XBeach x.grd / bed.dep files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  yz2xb                                      # Use defaults (bathy.yz -> XBGRID/{x.grd,bed.dep})
  yz2xb --yz bathy.yz --outdir XBGRID        # Explicit file names
        """,
    )
    parser.add_argument("--yz", default="bathy.yz", help="Input *.yz file name (default: bathy.yz)")
    parser.add_argument("--dep", default="bed.dep", help="Output *.dep file name (default: bed.dep)")
    parser.add_argument("--xgrd", default="x.grd", help="Output x-grid file name (default: x.grd)")
    parser.add_argument("--outdir", default="XBGRID", help="Output folder name (default: XBGRID)")
    args = parser.parse_args()

    yz_to_xb(
        yz=args.yz,
        dep=args.dep,
        xgrd=args.xgrd,
        outdir=args.outdir,
    )


if __name__ == "__main__":
    main()
