#!/usr/bin/env python
"""
xyz2xb - Convert a simple *.xyz point file into x.grd / y.grd / bed.dep files.

Reverse of xb2xyz. The *.xyz file must contain whitespace-separated "x y z"
rows. Each line of the input file becomes one line in x.grd, y.grd and
bed.dep (same line order, same line count) - i.e. the three output files are
just the x, y and z columns of the *.xyz file split back out. Values are
written as "%16.7e", matching the formatting used in the original
x.grd/y.grd/bed.dep files.
"""

import argparse
import sys
from pathlib import Path

import numpy as np


def xyz_to_xb(
    xyz="001.xyz",
    dep="bed.dep",
    xgrd="x.grd",
    ygrd="y.grd",
    outdir="XBGRID",
    cwd=None,
) -> Path:
    """
    Convert a *.xyz point file into x.grd / y.grd / bed.dep files.

    Args:
        xyz (str): Input *.xyz file name
        dep (str): Output *.dep file name
        xgrd (str): Output x-grid file name
        ygrd (str): Output y-grid file name
        outdir (str): Output folder name
        cwd (Path): Working directory to resolve relative paths against
            (defaults to the current directory)

    Returns:
        Path: Path to the output folder containing x.grd, y.grd and bed.dep
    """
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    xyz_path = cwd / xyz

    if not xyz_path.is_file():
        sys.exit(f"Error: input file not found: {xyz_path}")

    xyz_data = np.loadtxt(xyz_path)
    if xyz_data.ndim != 2 or xyz_data.shape[1] != 3:
        sys.exit(f"Error: expected 3 columns (x y z) in {xyz}, got shape {xyz_data.shape}")

    x = xyz_data[:, 0]
    y = xyz_data[:, 1]
    z = xyz_data[:, 2]

    outdir_path = cwd / outdir
    outdir_path.mkdir(parents=True, exist_ok=True)

    np.savetxt(outdir_path / xgrd, x, fmt="%16.7e")
    np.savetxt(outdir_path / ygrd, y, fmt="%16.7e")
    np.savetxt(outdir_path / dep, z, fmt="%16.7e")

    print(f"Wrote {xgrd}, {ygrd}, {dep} ({x.shape[0]} lines) to {outdir_path}")
    return outdir_path


def main():
    parser = argparse.ArgumentParser(
        prog="xyz2xb",
        description="Convert a *.xyz point file into x.grd / y.grd / bed.dep files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  xyz2xb                                     # Use defaults (001.xyz -> XBGRID/{x.grd,y.grd,bed.dep})
  xyz2xb --xyz 001.xyz --outdir XBGRID       # Explicit file names
        """,
    )
    parser.add_argument("--xyz", default="001.xyz", help="Input *.xyz file name (default: 001.xyz)")
    parser.add_argument("--dep", default="bed.dep", help="Output *.dep file name (default: bed.dep)")
    parser.add_argument("--xgrd", default="x.grd", help="Output x-grid file name (default: x.grd)")
    parser.add_argument("--ygrd", default="y.grd", help="Output y-grid file name (default: y.grd)")
    parser.add_argument("--outdir", default="XBGRID", help="Output folder name (default: XBGRID)")
    args = parser.parse_args()

    xyz_to_xb(
        xyz=args.xyz,
        dep=args.dep,
        xgrd=args.xgrd,
        ygrd=args.ygrd,
        outdir=args.outdir,
    )


if __name__ == "__main__":
    main()
