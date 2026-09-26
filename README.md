# XBGEARS

A collection of Python tools for converting between XBeach grid files (x.grd / y.grd / *.dep) and simple XYZ point files.

## Installation

```bash
pip install xbgears
```

## Features

- **xb2xyz**: Convert XBeach x.grd / y.grd / *.dep grid files into a *.xyz point file
- **xyz2xb**: Convert a *.xyz point file back into x.grd / y.grd / bed.dep files
- **xb2yz**: Convert a 1D XBeach x.grd / *.dep profile into a two-column *.yz file
- **yz2xb**: Convert a two-column *.yz profile file back into 1D x.grd / bed.dep files

## Usage

### Command-line

```bash
# List all available commands
xbgears-info

# Convert XBeach grid files to a *.xyz point file
xb2xyz --dep bed.dep --xgrd x.grd --ygrd y.grd --out 001.xyz

# Convert a *.xyz point file back to XBeach grid files
xyz2xb --xyz 001.xyz --outdir XBGRID

# Convert a 1D XBeach profile to a two-column *.yz file
xb2yz --dep bed.dep --xgrd x.grd --out bathy.yz

# Convert a *.yz profile back to 1D XBeach grid files
yz2xb --yz bathy.yz --outdir XBGRID
```

### Python API

```python
from xbgears import xb2xyz, xyz2xb, xb2yz, yz2xb

# Convert XBeach grid files to a *.xyz point file (written to XYZ/001.xyz)
xb2xyz.xb_to_xyz(dep="bed.dep", xgrd="x.grd", ygrd="y.grd", out="001.xyz")

# Convert a *.xyz point file back to XBeach grid files (written to XBGRID/)
xyz2xb.xyz_to_xb(xyz="001.xyz", outdir="XBGRID")

# Convert a 1D XBeach profile to a *.yz file (written to YZ/bathy.yz)
xb2yz.xb_to_yz(dep="bed.dep", xgrd="x.grd", out="bathy.yz")

# Convert a *.yz profile back to 1D XBeach grid files (written to XBGRID/)
yz2xb.yz_to_xb(yz="bathy.yz", outdir="XBGRID")
```

## Notes

- `xb2xyz` reads `xori`/`yori` from `params.txt` in the working directory (if present) and adds them to the x/y coordinates; grid rotation (`alfa`) is not applied.
- `xb2xyz` writes its output to the `XYZ/` directory by default; `xyz2xb` writes its output to the `XBGRID/` directory by default.
- `xb2yz` writes its output to the `YZ/` directory by default; `yz2xb` writes to `XBGRID/` and requires strictly increasing x values. Both use 3-decimal (`%.3f`) formatting.
