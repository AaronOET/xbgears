"""xbgen core: read / write / check XBeach params.txt files (no GUI dependencies).

A parameter set ("data") is an OrderedDict
    tab -> list of rows [on, keyword, value, sub-heading]
plus data['lists'] -> OrderedDict(name -> [on, items]) for the output lists
(global / mean / point variables, output points and runup gauges).

Switched-on rows are written as 'key = value'; switched-off rows are left out, or
written as '%key = value' with write_disabled=True (XBeach ignores those lines).
"""
import os
import re
from collections import OrderedDict
from datetime import datetime

from .keydb import (KEYDB, SPACEVARS_L, TABS, KEYINFO, ACTIVE, DEFAULT_LISTS,
                    LIST_KEYS, KEY_LIST, OUTPUT_FILES, DEPRECATED)

DEFAULT_XLSX = 'params_prep.xlsx'       # auto-loaded by the GUI at start if it exists
DEFAULT_NAME = 'params'                 # -> params.txt
EXE_DEFAULT = r'C:\XBeach\xbeach.exe'
KEY_WIDTH = 13                          # column width of the keyword in params.txt

# ---------------------------------------------------------------------------
#  helpers
# ---------------------------------------------------------------------------
_NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def parse_range(rng):
    """-> ('num', lo, hi) | ('opts', [..]) | ('expr', text) | (None,)"""
    rng = (rng or '').strip()
    if not rng:
        return (None,)
    m = re.fullmatch(r'(%s)\s+-\s+(%s)' % (_NUM, _NUM), rng)
    if m:
        return ('num', float(m.group(1)), float(m.group(2)))
    if ' - ' in rng or 'par%' in rng:
        return ('expr', rng)
    return ('opts', [o.strip() for o in rng.split(',') if o.strip()])


def is_switch(info):
    r = parse_range(info['range'])
    return r[0] == 'num' and r[1] == 0 and r[2] == 1 and '.' not in info['default']


def is_file(key):
    info = KEYINFO.get(key.lower())
    return (info and info['units'] == '<file>') or key.lower().endswith('file')


def default_data():
    """tab -> rows [on, key, value, sub]; plus 'lists'."""
    data = OrderedDict((t, []) for t in TABS)
    active = {k.lower(): v for k, v in ACTIVE.items()}
    for tab, sub, key, default, *_ in KEYDB:
        on = key.lower() in active
        data[tab].append([on, key, active.get(key.lower(), default), sub])
    data['lists'] = OrderedDict((k, [on, list(v)]) for k, (on, v) in DEFAULT_LISTS.items())
    return data


def _copy(data):
    out = OrderedDict((t, [list(r) for r in rows]) for t, rows in data.items() if t != 'lists')
    out['lists'] = OrderedDict((k, [on, list(v)]) for k, (on, v) in data['lists'].items())
    return out


def _clean(x):
    if x is None:
        return ''
    try:
        import pandas as pd
        if pd.isna(x):
            return ''
    except (ImportError, TypeError, ValueError):
        pass
    return str(x)


# ---------------------------------------------------------------------------
#  params.txt read / write
# ---------------------------------------------------------------------------
def parse_params(text):
    """Parse params.txt text. Known keywords go to their tab, unknown ones to 'other';
    keywords of the database not in the file are kept, switched off, with the manual default."""
    found = OrderedDict()                       # key_lower -> [on, key, val]
    lists = OrderedDict((k, [False, []]) for k in LIST_KEYS)
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if not s:
            continue
        on = not s.startswith('%') and not s.startswith('#')
        body = s.lstrip('%#').strip() if not on else s.split('%')[0].strip()
        if '=' not in body:
            continue
        key, val = [x.strip() for x in body.split('=', 1)]
        if not key or ' ' in key:
            continue
        kl = key.lower()
        if kl in KEY_LIST:
            name = KEY_LIST[kl]
            try:
                n = int(float(val))
            except ValueError:
                n = 0
            items = []
            while len(items) < n and i < len(lines):
                t = lines[i].split('%')[0].strip()
                i += 1
                if t:
                    items.append(t)
            if on or not lists[name][1]:
                lists[name] = [on and n > 0, items]
            continue
        if kl in found and found[kl][0] and not on:
            continue                            # active line wins over a commented one
        found[kl] = [on, key, val]

    data = OrderedDict((t, []) for t in TABS)
    for tab, sub, key, default, *_ in KEYDB:
        kl = key.lower()
        if kl in found:
            on, _k, v = found.pop(kl)
            data[tab].append([on, key, v, sub])
        else:
            data[tab].append([False, key, default, sub])
    for kl, (on, k, v) in found.items():
        data['other'].append([on, k, v, 'Not in the XBeach manual'])
    data['lists'] = lists
    return data


def read_params(path):
    for enc in ('utf-8-sig', 'cp950', 'latin-1'):
        try:
            with open(path, encoding=enc) as f:
                return parse_params(f.read())
        except UnicodeDecodeError:
            continue


def to_params_text(data, write_disabled=False, title='', info_lines=()):
    bar = '%' * 78
    out = [bar, '%%% XBeach parameter settings input file',
           '%%% ' + (title or 'XBeach model')]
    out += ['%%% ' + s for s in info_lines if s.strip()]
    out += ['%%% generated by xbgears xbgen  ' + datetime.now().strftime('%Y-%m-%d %H:%M'),
            bar, '']
    seen = {}
    for tab, rows in data.items():
        if tab == 'lists':
            continue
        cur_sub, block = None, []
        for on, key, val, sub in rows:
            key = str(key).strip()
            if not key or (not on and not write_disabled):
                continue
            if on:
                kl = key.lower()
                if kl in seen:
                    print('WARNING: keyword "%s" active twice (tabs %s and %s); XBeach uses the first.'
                          % (key, seen[kl], tab))
                seen.setdefault(kl, tab)
            if sub != cur_sub:
                if block:
                    out += block + ['']
                block = ['%%% ' + sub + ' ' + '%' * max(3, 73 - len(sub)), '']
                cur_sub = sub
            block.append('{0}{1:<{w}} = {2}'.format('' if on else '%', key, str(val).strip(), w=KEY_WIDTH))
        if block:
            out += block + ['']

    lists = data['lists']
    if any(on and items for on, items in lists.values()):
        out += ['%%% Output variables / locations ' + '%' * 45, '']
        for name, key in LIST_KEYS.items():
            on, items = lists[name]
            items = [s.strip() for s in items if s.strip()]
            if on and items:
                out.append('{0:<{w}} = {1}'.format(key, len(items), w=KEY_WIDTH))
                out += items
                out.append('')
            elif write_disabled and items:
                out.append('%{0:<{w}} = {1}'.format(key, len(items), w=KEY_WIDTH))
                out += ['%' + s for s in items]
                out.append('')
    return '\n'.join(out).rstrip() + '\n'


def bat_text(par_name, exe):
    s = ['@echo off', 'REM generated by xbgears xbgen', 'cd /d "%~dp0"']
    if par_name.lower() != 'params.txt':
        s.append('REM XBeach reads params.txt -> copy this variant first')
        s.append('copy /Y "{0}" params.txt'.format(par_name))
    s += ['set XBEACH_EXE={0}'.format(exe), '"%XBEACH_EXE%"', 'pause']
    return '\r\n'.join(s) + '\r\n'


# ---------------------------------------------------------------------------
#  xlsx (one sheet per tab, like inp_prep.xlsx of sfincsGen)
# ---------------------------------------------------------------------------
def write_xlsx(data, path):
    import pandas as pd
    with pd.ExcelWriter(path, engine='openpyxl') as xw:
        for tab, rows in data.items():
            if tab == 'lists':
                recs = [[name, 1 if on else 0, s] for name, (on, items) in rows.items() for s in (items or [''])]
                df = pd.DataFrame(recs, columns=['list', 'use', 'item'])
            else:
                df = pd.DataFrame([[1 if on else 0, k, v, sub,
                                    KEYINFO.get(str(k).lower(), {}).get('desc', '')] for on, k, v, sub in rows],
                                  columns=['use', 'parameter', 'value', 'group', 'description'])
            df.to_excel(xw, sheet_name=('output lists' if tab == 'lists' else tab)[:31], index=False)


def read_xlsx(path):
    import pandas as pd
    xf = pd.ExcelFile(path)
    found, lists = OrderedDict(), OrderedDict((k, [False, []]) for k in LIST_KEYS)
    for sht in xf.sheet_names:
        df = pd.read_excel(xf, sheet_name=sht, dtype=object)
        if sht == 'output lists':
            for r in df.itertuples(index=False):
                name = _clean(r[0]).strip()
                if name in lists:
                    lists[name][0] = lists[name][0] or str(_clean(r[1])).strip() in ('1', '1.0', 'True')
                    item = _clean(r[2]).strip()
                    if item:
                        lists[name][1].append(item)
            continue
        for r in df.itertuples(index=False):
            r = list(r) + [None] * 4
            key = _clean(r[1]).strip()
            if not key:
                continue
            on = _clean(r[0]).strip() in ('1', '1.0', 'True')
            found[key.lower()] = [on, key, _clean(r[2]).strip()]
    data = OrderedDict((t, []) for t in TABS)
    for tab, sub, key, default, *_ in KEYDB:
        if key.lower() in found:
            on, _k, v = found.pop(key.lower())
            data[tab].append([on, key, v, sub])
        else:
            data[tab].append([False, key, default, sub])
    for kl, (on, k, v) in found.items():
        data['other'].append([on, k, v, 'Not in the XBeach manual'])
    data['lists'] = lists
    return data


# ---------------------------------------------------------------------------
#  checks
# ---------------------------------------------------------------------------
def active(data):
    """key_lower -> value of the switched-on rows (first one wins)."""
    out = {}
    for tab, rows in data.items():
        if tab == 'lists':
            continue
        for on, key, val, _ in rows:
            k = str(key).strip().lower()
            if on and k and k not in out:
                out[k] = str(val).strip()
    return out


def _f(a, k, default=None):
    try:
        return float(a[k]) if k in a else default
    except ValueError:
        return default


def validate(data):
    """Print warnings; return number of problems."""
    a, n = active(data), 0

    def warn(msg):
        nonlocal n
        n += 1
        print('WARNING:', msg)

    for k, v in a.items():
        info = KEYINFO.get(k)
        if k in DEPRECATED:
            print('NOTE: %s - %s' % (k, DEPRECATED[k]))
        if not info:
            print('NOTE: "%s" is not in the XBeach manual tables - check spelling.' % k)
            continue
        if v == '':
            warn('%s is switched on but has no value' % info['key'])
            continue
        r = parse_range(info['range'])
        if r[0] == 'num':
            for tok in v.split():
                try:
                    x = float(tok)
                except ValueError:
                    warn('%s = "%s" is not a number' % (info['key'], v))
                    break
                if not (r[1] <= x <= r[2]):
                    warn('%s = %s outside the manual range %s' % (info['key'], tok, info['range']))
        elif r[0] == 'opts' and v.lower() not in [o.lower() for o in r[1]]:
            warn('%s = %s not one of: %s' % (info['key'], v, info['range']))

    # dependencies
    for k in ('nx', 'ny', 'depfile', 'tstop'):
        if k not in a:
            warn('%s is required but switched off' % k)
    vardx = _f(a, 'vardx', 0)
    ny = _f(a, 'ny', 2)
    if vardx == 1:
        if 'xfile' not in a:
            warn('vardx = 1 needs xfile')
        if ny and ny > 0 and 'yfile' not in a:
            warn('vardx = 1 with ny > 0 needs yfile')
    elif a.get('gridform', 'xbeach') == 'xbeach' and 'dx' not in a:
        warn('vardx = 0 needs dx (and dy for ny > 0)')
    if _f(a, 'thetamax', 90) <= _f(a, 'thetamin', -90):
        warn('thetamax must be greater than thetamin')
    t0, t1 = _f(a, 'tstart', 0.0), _f(a, 'tstop', 2000.0)
    if t1 is not None and t0 is not None:
        if t1 <= t0:
            warn('tstop must be greater than tstart')
        dur = t1 - t0
        for k in ('tintg', 'tintm', 'tintp'):
            v = _f(a, k)
            if v is not None and v > dur:
                warn('%s = %g > tstop - tstart = %g' % (k, v, dur))
        ms = _f(a, 'morstart')
        if ms is not None and ms > t1:
            warn('morstart must be <= tstop')
        print('Run: tstart = %g s, tstop = %g s -> %g s (%.2f h) of output time' % (t0, t1, dur, dur / 3600.))
    if 'instat' in a and 'wbctype' in a:
        warn('instat and wbctype are both on - use only wbctype')
    wbc = a.get('wbctype', a.get('instat', 'jonstable' if 'instat' not in a else ''))
    if wbc in ('jonstable', 'parametric', 'swan', 'vardens', 'jons', 'jons_table', 'stat_table') \
            and 'bcfile' not in a:
        warn('wbctype = %s reads bcfile, which is switched off' % wbc)
    if wbc in ('params', 'stat', 'bichrom') and not ({'hrms', 'trep'} & set(a)):
        print('NOTE: wbctype = %s uses Hrms / Trep / dir0 (manual defaults 1 m / 10 s / 270 deg)' % wbc)
    if 'zs0file' in a and _f(a, 'tideloc', 2) == 0:
        warn('zs0file is set but tideloc = 0')
    if _f(a, 'tideloc', 0) and _f(a, 'tideloc', 0) > 0 and 'zs0file' in a and 'zs0' in a:
        print('NOTE: zs0 is ignored for the boundary when zs0file is used (still sets initial level)')
    if ny == 0:
        for k in ('front', 'back'):
            if a.get(k) == 'abs_2d':
                print('NOTE: %s = abs_2d reduces to abs_1d in 1D mode (ny = 0)' % k)
    if a.get('wavemodel') == 'nonh' and a.get('front') not in (None, 'nonh_1d', 'abs_1d'):
        print('NOTE: wavemodel = nonh usually runs with front = nonh_1d')
    if a.get('outputformat', 'fortran') != 'netcdf' and 'ncfilename' in a:
        print('NOTE: ncfilename only used with outputformat = netcdf')
    for name in ('global', 'mean', 'point'):
        on, items = data['lists'][name]
        bad = [s for s in items if s.lower() not in SPACEVARS_L]
        if on and bad:
            warn('%s output variable(s) not known to XBeach: %s' % (name, ', '.join(bad)))
    if data['lists']['point'][0] and not (data['lists']['points'][0] or data['lists']['rugauge'][0]):
        warn('npointvar set but no output points / runup gauges')
    lst = data['lists']['mean']
    if lst[0] and lst[1] and 'tintm' not in a:
        print('NOTE: tintm off -> XBeach averages over the whole run')
    if not n:
        print('Checks passed.')
    return n


def check_files(data, folder):
    """Warn about active file entries that are missing; compare nx/ny with xfile / depfile."""
    a, n_bad = active(data), 0
    for k, v in a.items():
        if is_file(k) and k not in OUTPUT_FILES and v and v.lower() not in ('none',):
            p = os.path.join(folder, v)
            if not os.path.exists(p):
                print('WARNING: {0} = {1} not found in {2}'.format(KEYINFO.get(k, {}).get('key', k), v,
                                                                  os.path.abspath(folder)))
                n_bad += 1
    if not n_bad:
        print('All referenced files exist.')
    try:
        nx, ny = int(float(a['nx'])), int(float(a['ny']))
    except (KeyError, ValueError):
        return
    for k in ('xfile', 'depfile', 'yfile'):
        if k in a and (k != 'xfile' or _f(a, 'vardx', 0) == 1):
            p = os.path.join(folder, a[k])
            if os.path.exists(p):
                try:
                    shape = grid_shape(p)
                except Exception as e:
                    print('NOTE: could not read %s -> %s' % (a[k], e))
                    continue
                want = (ny + 1, nx + 1)
                flag = 'OK' if shape == want else 'MISMATCH'
                print('%s: %s is %d x %d (rows x cols), params expects %d x %d -> %s'
                      % (k, a[k], shape[0], shape[1], want[0], want[1], flag))


def grid_shape(path):
    with open(path) as f:
        rows = [ln.split() for ln in f if ln.strip()]
    return len(rows), len(rows[0])



def load(path=None):
    """Load a parameter set from params.txt / .xlsx, or the built-in defaults when path is None."""
    if path is None:
        return default_data()
    if str(path).lower().endswith(('.xlsx', '.xlsm', '.xls')):
        return read_xlsx(path)
    return read_params(path)


def run_file_names(name=DEFAULT_NAME):
    """-> (params file name, run .bat file name) for a params name with or without '.txt'."""
    name = (name or DEFAULT_NAME).strip()
    if name.lower().endswith('.txt'):
        name = name[:-4]
    bat = 'run.bat' if name.lower() == 'params' else 'run_' + name + '.bat'
    return name + '.txt', bat


def write_params(data, outdir='.', name=DEFAULT_NAME, write_disabled=False, title='',
                 bat=False, exe=EXE_DEFAULT):
    """Write <outdir>/<name>.txt (and optionally the run .bat). Returns the list of written paths."""
    os.makedirs(outdir, exist_ok=True)
    par_name, bat_name = run_file_names(name)
    par_file = os.path.join(outdir, par_name)
    with open(par_file, 'wt', encoding='utf-8', newline='\n') as f:
        f.write(to_params_text(data, write_disabled, title))
    written = [par_file]
    if bat:
        bat_file = os.path.join(outdir, bat_name)
        with open(bat_file, 'wt', encoding='utf-8', newline='') as f:
            f.write(bat_text(par_name, exe))
        written.append(bat_file)
    return written
