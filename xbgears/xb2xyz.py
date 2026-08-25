#!/usr/bin/env python
"""
xb2xyz - Convert XBeach x.grd / y.grd / *.dep grid files into a simple *.xyz point file.

x.grd and y.grd must have the same shape as the *.dep file (rows = ny+1,
columns = nx+1, whitespace-separated floats, XBeach grid format).

If params.txt exists in the current folder, xori and yori are read from it
and added to the x/y coordinates. Otherwise xori = yori = 0.
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np


def read_params(params_path: Path) -> tuple[float, float]:
    """Return (xori, yori) from params.txt, defaulting to (0, 0) if absent."""
    xori, yori = 0.0, 0.0
    if not params_path.is_file():
        print(f"No params.txt found at {params_path}; assuming xori=0, yori=0.")
        return xori, yori

    text = params_path.read_text(errors="ignore")
    xori_match = re.search(r"^\s*xori\s*=\s*([-\d.eE+]+)", text, re.MULTILINE)
    yori_match = re.search(r"^\s*yori\s*=\s*([-\d.eE+]+)", text, re.MULTILINE)

    if xori_match:
        xori = float(xori_match.group(1))
    else:
        print(f"xori not found in {params_path}; assuming xori=0.")

    if yori_match:
        yori = float(yori_match.group(1))
    else:
        print(f"yori not found in {params_path}; assuming yori=0.")

    alfa_match = re.search(r"^\s*alfa\s*=\s*([-\d.eE+]+)", text, re.MULTILINE)
    if alfa_match and float(alfa_match.group(1)) != 0:
        print(
            f"Warning: params.txt has alfa={alfa_match.group(1)} (grid rotation). "
            "This tool only applies the xori/yori translation, not the rotation."
        )

    return xori, yori


def xb_to_xyz(
    dep="bed.dep",
    out="001.xyz",
    xgrd="x.grd",
    ygrd="y.grd",
    outdir="XYZ",
    params="params.txt",
    cwd=None,
) -> Path:
    """
    Convert XBeach x.grd / y.grd / *.dep grid files into a *.xyz point file.

    Args:
        dep (str): Input *.dep file name
        out (str): Output *.xyz file name
        xgrd (str): Input x-grid file name
        ygrd (str): Input y-grid file name
        outdir (str): Output folder name
        params (str): params.txt file name (used to read xori/yori)
        cwd (Path): Working directory to resolve relative paths against
            (defaults to the current directory)

    Returns:
        Path: Path to the written *.xyz file
    """
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    xgrd_path = cwd / xgrd
    ygrd_path = cwd / ygrd
    dep_path = cwd / dep
    params_path = cwd / params

    for p in (xgrd_path, ygrd_path, dep_path):
        if not p.is_file():
            sys.exit(f"Error: required input file not found: {p}")

    x = np.loadtxt(xgrd_path)
    y = np.loadtxt(ygrd_path)
    z = np.loadtxt(dep_path)

    if not (x.shape == y.shape == z.shape):
        sys.exit(
            f"Error: shape mismatch - x.grd {x.shape}, y.grd {y.shape}, "
            f"{dep} {z.shape} must all match."
        )

    xori, yori = read_params(params_path)

    x_out = x + xori
    y_out = y + yori

    outdir_path = cwd / outdir
    outdir_path.mkdir(parents=True, exist_ok=True)
    out_path = outdir_path / out

    xyz = np.column_stack((x_out.ravel(), y_out.ravel(), z.ravel()))
    np.savetxt(out_path, xyz, fmt="%.6f %.6f %.6f")

    print(f"Wrote {xyz.shape[0]} points to {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        prog="xb2xyz",
        description="Convert XBeach x.grd / y.grd / *.dep grid files into a *.xyz point file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  xb2xyz                                     # Use defaults (bed.dep, x.grd, y.grd -> XYZ/001.xyz)
  xb2xyz --dep bed.dep --out 001.xyz         # Explicit file names
        """,
    )
    parser.add_argument("--dep", default="bed.dep", help="Input *.dep file name (default: bed.dep)")
    parser.add_argument("--out", default="001.xyz", help="Output *.xyz file name (default: 001.xyz)")
    parser.add_argument("--xgrd", default="x.grd", help="Input x-grid file name (default: x.grd)")
    parser.add_argument("--ygrd", default="y.grd", help="Input y-grid file name (default: y.grd)")
    parser.add_argument("--outdir", default="XYZ", help="Output folder name (default: XYZ)")
    parser.add_argument("--params", default="params.txt", help="params.txt file name (default: params.txt)")
    args = parser.parse_args()

    xb_to_xyz(
        dep=args.dep,
        out=args.out,
        xgrd=args.xgrd,
        ygrd=args.ygrd,
        outdir=args.outdir,
        params=args.params,
    )


if __name__ == "__main__":
    main()
