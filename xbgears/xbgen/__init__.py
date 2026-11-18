#!/usr/bin/env python
"""
xbgen - Build, check and write XBeach params.txt files.

Every keyword XBeach reads from params.txt is known (from the XBeach manual tables),
grouped per topic, with default, range/options, units and description. A parameter set
is switched on/off per keyword; only switched-on keywords are written.

Without options `xbgen` starts the tkinter GUI. With --check or --write it runs
without a GUI.

Python API:
    from xbgears import xbgen
    data = xbgen.load('params.txt')          # or xbgen.load() for the built-in defaults
    xbgen.validate(data)                      # prints warnings, returns the count
    xbgen.write_params(data, outdir='run1', bat=True)
"""

import argparse
import os
import sys

from .keydb import KEYDB, KEYINFO, TABS, SPACEVARS, LIST_KEYS
from .core import (DEFAULT_NAME, EXE_DEFAULT, default_data, load, parse_params, read_params,
                   read_xlsx, write_xlsx, to_params_text, bat_text, active, validate,
                   check_files, grid_shape, write_params, run_file_names)

__all__ = [
    'KEYDB', 'KEYINFO', 'TABS', 'SPACEVARS', 'LIST_KEYS',
    'default_data', 'load', 'parse_params', 'read_params', 'read_xlsx', 'write_xlsx',
    'to_params_text', 'bat_text', 'active', 'validate', 'check_files', 'grid_shape',
    'write_params', 'gui', 'main',
]


def gui(source=None, outdir=None):
    """Start the tkinter GUI, optionally loading a params.txt / .xlsx file."""
    try:
        from .gui import run
    except ImportError as e:  # tkinter missing (e.g. minimal Linux Python)
        sys.exit(f"Error: the xbgen GUI needs tkinter ({e}). Use --check / --write without GUI.")
    run(source=source, outdir=outdir)


def main():
    parser = argparse.ArgumentParser(
        prog='xbgen',
        description='Build, check and write XBeach params.txt files '
                    '(starts the GUI unless --check or --write is given).',
    )
    parser.add_argument('source', nargs='?',
                        help='params.txt or .xlsx to load (default: built-in defaults)')
    parser.add_argument('--check', action='store_true',
                        help='check the parameter set and referenced files, no GUI')
    parser.add_argument('--write', action='store_true',
                        help='write <outdir>/<name>.txt from the parameter set, no GUI')
    parser.add_argument('--outdir', default=None,
                        help='output folder (default: folder of source, else current folder)')
    parser.add_argument('--name', default=DEFAULT_NAME,
                        help='params file name without .txt (default: params)')
    parser.add_argument('--title', default='XBeach model', help='title in the params.txt header')
    parser.add_argument('--write-disabled', action='store_true',
                        help='write switched-off keywords as %%comments')
    parser.add_argument('--bat', action='store_true', help='also write run.bat / run_<name>.bat')
    parser.add_argument('--exe', default=EXE_DEFAULT, help=f'XBeach executable for the .bat (default: {EXE_DEFAULT})')
    parser.add_argument('--force', action='store_true',
                        help='write even if checks give warnings / overwrite existing files')
    args = parser.parse_args()

    if not (args.check or args.write):
        gui(args.source, args.outdir)
        return

    if args.source and not os.path.isfile(args.source):
        sys.exit(f"Error: input file not found: {args.source}")
    try:
        data = load(args.source)
    except ImportError:
        sys.exit("Error: reading .xlsx needs pandas + openpyxl (pip install xbgears[xlsx])")
    outdir = args.outdir or (os.path.dirname(os.path.abspath(args.source)) if args.source else '.')

    n_warn = validate(data)
    if args.check:
        check_files(data, outdir)
    if not args.write:
        sys.exit(1 if n_warn else 0)

    if n_warn and not args.force:
        sys.exit(f"{n_warn} warning(s) - nothing written (use --force to write anyway).")
    targets = [os.path.join(outdir, f) for f in run_file_names(args.name)[:1 + args.bat]]
    existing = [p for p in targets if os.path.exists(p)]
    if existing and not args.force:
        sys.exit("Error: file(s) exist (use --force to overwrite): " + ', '.join(existing))
    for p in write_params(data, outdir, args.name, args.write_disabled, args.title,
                          bat=args.bat, exe=args.exe):
        print('Written:', os.path.abspath(p))
    check_files(data, outdir)


if __name__ == "__main__":
    main()
