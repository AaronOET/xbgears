"""xbgen GUI: tkinter params.txt builder for XBeach.

Every keyword XBeach reads from params.txt is listed, one tab per topic and a
sub-heading per keyword group of the XBeach manual. Checked keywords are written as
'key = value'; unchecked ones are left out (or written as '%key = value' comments).
"""
import os
import contextlib
import io
from collections import OrderedDict

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from .keydb import KEYDB, KEYINFO, ACTIVE, SPACEVARS, SPACEVARS_L, LIST_KEYS
from .core import (DEFAULT_XLSX, DEFAULT_NAME, EXE_DEFAULT, parse_range, is_switch, is_file,
                   default_data, read_params, read_xlsx, write_xlsx, to_params_text, bat_text,
                   active, _f, validate, check_files, grid_shape, run_file_names)


class ScrollFrame(ttk.Frame):
    """Frame with vertical + horizontal scrollbars; put widgets in .inner."""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        hsb = ttk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.inner = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>', self._update_region)
        self.canvas.bind('<Configure>', self._update_region)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas.bind('<Enter>', lambda e: self.canvas.bind_all('<MouseWheel>', self._wheel))
        self.canvas.bind('<Leave>', lambda e: self.canvas.unbind_all('<MouseWheel>'))

    def _update_region(self, _=None):
        w = max(self.inner.winfo_reqwidth(), self.canvas.winfo_width())
        h = max(self.inner.winfo_reqheight(), self.canvas.winfo_height())
        self.canvas.configure(scrollregion=(0, 0, w, h))
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            self.canvas.yview_moveto(0)

    def _wheel(self, e):
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return
        self.canvas.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), 'units')


class ParamTabs:
    """One notebook page per tab; each keyword row: On | Keyword | Value | Units | Default | Range | Description."""
    W_KEY, W_VAL = 18, 26

    def __init__(self, notebook, out_dir_var, show_adv_var):
        self.nb = notebook
        self.out_dir = out_dir_var
        self.show_adv = show_adv_var
        self.rows = OrderedDict()        # tab -> list of dict(vars, widgets, sub, adv)
        self.frames = {}                 # tab -> ScrollFrame
        self.lists = None

    # ---- widgets ----
    def _browse_file(self, var):
        start = self.out_dir.get().strip() or '.'
        p = filedialog.askopenfilename(initialdir=start)
        if p:
            try:
                rel = os.path.relpath(p, os.path.abspath(start))
            except ValueError:
                rel = p
            var.set(rel.replace('\\', '/'))

    def _row(self, parent, tab, vals, r):
        on, key, val, sub = (list(vals) + [False, '', '', ''])[:4]
        info = KEYINFO.get(str(key).lower(), {})
        v_on, v_key, v_val = tk.BooleanVar(value=bool(on)), tk.StringVar(value=str(key)), \
            tk.StringVar(value=str(val))
        w = []
        w.append(ttk.Checkbutton(parent, variable=v_on))
        w[-1].grid(row=r, column=0, padx=(4, 2))
        if info:
            w.append(ttk.Label(parent, text=info['key'], width=self.W_KEY,
                               foreground='gray40' if info['adv'] else ''))
        else:
            w.append(ttk.Entry(parent, textvariable=v_key, width=self.W_KEY))
        w[-1].grid(row=r, column=1, sticky='w', padx=1)
        rng = parse_range(info.get('range', ''))
        if info and is_switch(info):
            ent = ttk.Combobox(parent, textvariable=v_val, values=['0', '1'], width=self.W_VAL - 2)
        elif rng[0] == 'opts':
            ent = ttk.Combobox(parent, textvariable=v_val, values=rng[1], width=self.W_VAL - 2)
        else:
            ent = ttk.Entry(parent, textvariable=v_val, width=self.W_VAL)
        ent.grid(row=r, column=2, sticky='w', padx=1, pady=1)
        w.append(ent)
        # typing a value switches the keyword on
        v_val.trace_add('write', lambda *_: v_on.set(True))
        if is_file(str(key)):
            w.append(ttk.Button(parent, text='...', width=3, command=lambda v=v_val: self._browse_file(v)))
            w[-1].grid(row=r, column=3, padx=1)
        if info:
            for c, txt, wd in ((4, info['units'], 7), (5, info['default'], 12), (6, info['range'], 30)):
                w.append(ttk.Label(parent, text=txt, width=wd, foreground='gray30'))
                w[-1].grid(row=r, column=c, sticky='w', padx=2)
            w.append(ttk.Label(parent, text=('[adv] ' if info['adv'] else '') + info['desc']))
            w[-1].grid(row=r, column=7, sticky='w', padx=2)
        return dict(vars=(v_on, v_key, v_val), sub=sub, widgets=w, entry=ent,
                    adv=bool(info.get('adv')), row=r)

    def _page(self, tab, rows):
        page = ttk.Frame(self.nb)
        sf = ScrollFrame(page)
        sf.pack(fill='both', expand=True)
        body = sf.inner
        for c, t in ((0, 'On'), (1, 'Keyword'), (2, 'Value'), (4, 'Units'), (5, 'Default'),
                     (6, 'Range / options'), (7, 'Description (manual, not written)')):
            ttk.Label(body, text=t, font=('', 9, 'bold')).grid(row=0, column=c, sticky='w', pady=(4, 2))
        out, r, cur = [], 1, None
        for vals in rows:
            sub = vals[3]
            if sub != cur:
                ttk.Label(body, text=sub, font=('', 9, 'bold italic'), foreground='navy').grid(
                    row=r, column=0, columnspan=4, sticky='w', pady=(8, 1), padx=4)
                r, cur = r + 1, sub
            out.append(self._row(body, tab, vals, r))
            r += 1
        self.rows[tab] = out
        self.frames[tab] = sf

        def _add():
            n = body.grid_size()[1]
            self.rows[tab].append(self._row(body, tab, [True, '', '', 'User keywords'], n))
            btn.grid_configure(row=n + 1)
            sf.canvas.update_idletasks()
            sf.canvas.yview_moveto(1.0)

        btn = ttk.Button(body, text='+ add row', command=_add)
        btn.grid(row=r, column=0, columnspan=2, sticky='w', pady=4)
        return page

    def _lists_page(self, lists):
        page = ttk.Frame(self.nb)
        self.lists = OrderedDict()
        ttk.Label(page, text='Output variables (Ctrl/Shift-click to select) and output locations. '
                             'The count line (nglobalvar = n, ...) is written from the selection.',
                  font=('', 9, 'italic')).grid(row=0, column=0, columnspan=5, sticky='w', padx=4, pady=4)
        for c, name in enumerate(('global', 'mean', 'point')):
            on, items = lists[name]
            f = ttk.LabelFrame(page, text=LIST_KEYS[name])
            f.grid(row=1, column=c, sticky='nsew', padx=4, pady=2)
            v_on = tk.BooleanVar(value=on)
            ttk.Checkbutton(f, text='write', variable=v_on).pack(anchor='w')
            flt = tk.StringVar()
            ttk.Entry(f, textvariable=flt, width=24).pack(fill='x')
            lb = tk.Listbox(f, selectmode='extended', height=22, exportselection=False, width=26)
            lb.pack(fill='both', expand=True)
            sel = set(items)
            extra = [s for s in items if s.lower() not in SPACEVARS_L]
            allv = list(SPACEVARS) + extra
            cnt = ttk.Label(f, text='')
            cnt.pack(anchor='w')
            st = dict(on=v_on, lb=lb, sel=sel, all=allv, flt=flt, cnt=cnt)
            self.lists[name] = st
            self._fill_list(st)
            flt.trace_add('write', lambda *_, s=st: self._fill_list(s))
            lb.bind('<<ListboxSelect>>', lambda e, s=st: self._sync_sel(s))
            page.columnconfigure(c, weight=1)
        for c, name, hint in ((3, 'points', 'x y   (one per line)'), (4, 'rugauge', 'x y   (one per line)')):
            on, items = lists[name]
            f = ttk.LabelFrame(page, text=LIST_KEYS[name])
            f.grid(row=1, column=c, sticky='nsew', padx=4, pady=2)
            v_on = tk.BooleanVar(value=on)
            ttk.Checkbutton(f, text='write', variable=v_on).pack(anchor='w')
            ttk.Label(f, text=hint).pack(anchor='w')
            txt = tk.Text(f, width=26, height=22, font=('Consolas', 9))
            txt.pack(fill='both', expand=True)
            txt.insert('1.0', '\n'.join(items))
            self.lists[name] = dict(on=v_on, txt=txt)
            page.columnconfigure(c, weight=1)
        page.rowconfigure(1, weight=1)
        return page

    def _fill_list(self, st):
        lb, f = st['lb'], st['flt'].get().strip().lower()
        lb.delete(0, 'end')
        shown = [v for v in st['all'] if f in v.lower()] if f else st['all']
        shown = [v for v in shown if v in st['sel']] + [v for v in shown if v not in st['sel']]
        for v in shown:                         # selected ones first
            lb.insert('end', v)
            if v in st['sel']:
                lb.selection_set('end')
        st['cnt'].config(text='%d selected' % len(st['sel']))

    def _sync_sel(self, st):
        lb = st['lb']
        shown = set(lb.get(0, 'end'))
        cur = {lb.get(i) for i in lb.curselection()}
        st['sel'] = (st['sel'] - shown) | cur
        st['cnt'].config(text='%d selected' % len(st['sel']))

    # ---- data in / out ----
    def set_data(self, data, keep_tab=False):
        idx = self.nb.index('current') if (keep_tab and self.nb.tabs()) else 0
        for t in self.nb.tabs():
            self.nb.forget(t)
        self.rows, self.frames = OrderedDict(), {}
        for tab, rows in data.items():
            if tab == 'lists':
                continue
            self.nb.add(self._page(tab, rows), text=tab)
        self.nb.add(self._lists_page(data['lists']), text='output lists')
        self.apply_adv_filter()
        if self.nb.tabs():
            self.nb.select(min(idx, len(self.nb.tabs()) - 1))

    def get_data(self):
        data = OrderedDict()
        for tab, rows in self.rows.items():
            data[tab] = [[r['vars'][0].get(), r['vars'][1].get().strip(), r['vars'][2].get(), r['sub']]
                         for r in rows]
        lists = OrderedDict()
        for name, st in self.lists.items():
            if 'lb' in st:
                order = {v: i for i, v in enumerate(st['all'])}
                items = sorted(st['sel'], key=lambda v: order.get(v, 1e9))
            else:
                items = [s.strip() for s in st['txt'].get('1.0', 'end').splitlines() if s.strip()]
            lists[name] = [st['on'].get(), items]
        data['lists'] = lists
        return data

    def apply_adv_filter(self):
        show = self.show_adv.get()
        for rows in self.rows.values():
            for r in rows:
                vis = show or not r['adv'] or r['vars'][0].get()
                for w in r['widgets']:
                    (w.grid if vis else w.grid_remove)()

    def find(self, text):
        text = text.strip().lower()
        if not text:
            return None
        hits = [(t, r) for t, rows in self.rows.items() for r in rows
                if r['vars'][1].get().lower() == text]
        hits = hits or [(t, r) for t, rows in self.rows.items() for r in rows
                        if text in r['vars'][1].get().lower()]
        if not hits:
            return None
        tab, r = hits[0]
        if not self.show_adv.get() and r['adv']:
            self.show_adv.set(True)
            self.apply_adv_filter()
        self.nb.select(list(self.rows).index(tab))
        sf = self.frames[tab]
        sf.update_idletasks()
        y = r['entry'].winfo_y()
        h = max(sf.inner.winfo_reqheight(), 1)
        sf.canvas.yview_moveto(max(0, (y - 60) / h))
        r['entry'].focus_set()
        return tab, r['vars'][1].get(), len(hits)


class App(tk.Tk):
    def __init__(self, source=None, outdir=None):
        super().__init__()
        self.title('xbgen - XBeach params.txt builder')
        self.geometry('1350x860')
        pad = dict(padx=4, pady=2)

        # ---- top: load / save / find ----
        top = ttk.Frame(self)
        top.pack(fill='x', **pad)
        self.src_path = tk.StringVar(value=DEFAULT_XLSX)
        self.save_path = tk.StringVar(value='params_custom.xlsx')
        self.title_var = tk.StringVar(value='XBeach model')
        self.find_var = tk.StringVar()
        self.show_adv = tk.BooleanVar(value=True)
        ttk.Label(top, text='Load from').grid(row=0, column=0, sticky='w')
        ttk.Entry(top, textvariable=self.src_path, width=70).grid(row=0, column=1, sticky='ew', **pad)
        ttk.Button(top, text='...', width=3, command=self.browse_src).grid(row=0, column=2)
        ttk.Button(top, text='Load', command=self.on_load).grid(row=0, column=3, **pad)
        ttk.Button(top, text='Load params.txt...', command=self.on_load_params).grid(row=0, column=4, **pad)
        ttk.Button(top, text='Built-in defaults', command=self.on_reset).grid(row=0, column=5, **pad)
        ttk.Label(top, text='Save as').grid(row=1, column=0, sticky='w')
        ttk.Entry(top, textvariable=self.save_path, width=70).grid(row=1, column=1, sticky='ew', **pad)
        ttk.Button(top, text='...', width=3, command=self.browse_save).grid(row=1, column=2)
        ttk.Button(top, text='Save xlsx', command=self.on_save).grid(row=1, column=3, **pad)
        ttk.Label(top, text='Title').grid(row=2, column=0, sticky='w')
        ttk.Entry(top, textvariable=self.title_var, width=70).grid(row=2, column=1, sticky='ew', **pad)
        fr = ttk.Frame(top)
        fr.grid(row=2, column=3, columnspan=4, sticky='w')
        ttk.Label(fr, text='Find keyword').pack(side='left')
        e = ttk.Entry(fr, textvariable=self.find_var, width=16)
        e.pack(side='left', padx=4)
        e.bind('<Return>', lambda _: self.on_find())
        ttk.Button(fr, text='Find', command=self.on_find).pack(side='left')
        ttk.Checkbutton(fr, text='Show advanced keywords', variable=self.show_adv,
                        command=lambda: self.gui.apply_adv_filter()).pack(side='left', padx=12)
        top.columnconfigure(1, weight=1)

        # ---- output vars ----
        self.out_dir = tk.StringVar(value='.')
        self.out_name = tk.StringVar(value=DEFAULT_NAME)
        self.exe = tk.StringVar(value=EXE_DEFAULT)
        self.write_bat = tk.BooleanVar(value=True)
        self.write_disabled = tk.BooleanVar(value=False)

        # ---- tabs ----
        pw = ttk.PanedWindow(self, orient='vertical')
        pw.pack(fill='both', expand=True, **pad)
        nb = ttk.Notebook(pw)
        self.gui = ParamTabs(nb, self.out_dir, self.show_adv)
        pw.add(nb, weight=4)

        # ---- output options + log ----
        bottom = ttk.Frame(pw)
        pw.add(bottom, weight=1)
        opt = ttk.LabelFrame(bottom, text='Output')
        opt.pack(fill='x')
        ttk.Label(opt, text='Output dir').grid(row=0, column=0, sticky='w', **pad)
        ttk.Entry(opt, textvariable=self.out_dir, width=55).grid(row=0, column=1, sticky='ew', **pad)
        ttk.Button(opt, text='...', width=3, command=self.browse_dir).grid(row=0, column=2)
        ttk.Label(opt, text='File name').grid(row=0, column=3, sticky='w', **pad)
        ttk.Entry(opt, textvariable=self.out_name, width=30).grid(row=0, column=4, sticky='w', **pad)
        ttk.Label(opt, text='(.txt added)').grid(row=0, column=5, sticky='w')
        ttk.Label(opt, text='Executable').grid(row=1, column=0, sticky='w', **pad)
        ttk.Entry(opt, textvariable=self.exe, width=55).grid(row=1, column=1, sticky='ew', **pad)
        ttk.Button(opt, text='...', width=3, command=self.browse_exe).grid(row=1, column=2)
        ttk.Checkbutton(opt, text='Also write run_<name>.bat', variable=self.write_bat).grid(
            row=1, column=3, columnspan=3, sticky='w', **pad)
        chk = ttk.Frame(opt)
        chk.grid(row=2, column=0, columnspan=6, sticky='w', **pad)
        ttk.Checkbutton(chk, text='Write disabled lines as %comments',
                        variable=self.write_disabled).pack(side='left', padx=(0, 12))
        btns = ttk.Frame(opt)
        btns.grid(row=3, column=0, columnspan=6, sticky='w', **pad)
        for txt, cmd in (('Preview', self.on_preview), ('Check', self.on_check),
                         ('Generate params.txt', self.on_generate), ('nx / ny from xfile', self.on_nxny),
                         ('Write JONSWAP table...', self.on_jonswap)):
            ttk.Button(btns, text=txt, command=cmd).pack(side='left', padx=(0, 6))
        opt.columnconfigure(1, weight=1)

        self.log = ScrolledText(bottom, height=10, font=('Consolas', 9), wrap='none')
        self.log.pack(fill='both', expand=True, pady=(4, 0))

        # ---- initial values ----
        with self.logging(clear=True):
            data = None
            if os.path.exists(DEFAULT_XLSX):
                try:
                    data = read_xlsx(DEFAULT_XLSX)
                    print('Loaded defaults from ' + os.path.abspath(DEFAULT_XLSX))
                except Exception as e:
                    print('Could not read', DEFAULT_XLSX, '->', e, '- using built-in defaults.')
            if data is None:
                data = default_data()
                print('%d XBeach keywords loaded (built-in defaults, %d switched on).'
                      % (len(KEYDB), sum(1 for t in KEYDB if t[2].lower() in {k.lower() for k in ACTIVE})))
            self.gui.set_data(data)
        if outdir:
            self.out_dir.set(outdir)
        if source:
            self.src_path.set(source)
            self.on_load()

    @contextlib.contextmanager
    def logging(self, clear=True):
        if clear:
            self.log.delete('1.0', 'end')
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                yield
        except Exception as e:
            buf.write('ERROR: %s\n' % e)
        finally:
            self.log.insert('end', buf.getvalue())
            self.log.see('end' if not clear else '1.0')

    # ---- dialogs ----
    def browse_src(self):
        p = filedialog.askopenfilename(filetypes=[('xlsx / txt', ('*.xlsx', '*.txt')), ('Excel', '*.xlsx'),
                                                  ('params', '*.txt'), ('All files', '*.*')])
        if p:
            self.src_path.set(p)

    def browse_save(self):
        p = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel', '*.xlsx')])
        if p:
            self.save_path.set(p)

    def browse_dir(self):
        p = filedialog.askdirectory()
        if p:
            self.out_dir.set(p)

    def browse_exe(self):
        p = filedialog.askopenfilename(filetypes=[('Executable', '*.exe'), ('All files', '*.*')])
        if p:
            self.exe.set(p)

    # ---- actions ----
    def on_find(self):
        res = self.gui.find(self.find_var.get())
        with self.logging():
            if res:
                print('Found "%s" in tab "%s"%s' % (res[1], res[0], ' (%d matches)' % res[2] if res[2] > 1 else ''))
            else:
                print('Keyword "%s" not found.' % self.find_var.get())

    def on_load(self):
        with self.logging():
            p = self.src_path.get().strip()
            is_x = p.lower().endswith(('.xlsx', '.xlsm', '.xls'))
            try:
                data = read_xlsx(p) if is_x else read_params(p)
            except Exception as e:
                print('Could not load', p, '->', e)
                return
            self.gui.set_data(data)
            if not is_x:
                self.out_dir.set(os.path.dirname(os.path.abspath(p)))
                self.out_name.set(os.path.splitext(os.path.basename(p))[0])
            n_on = sum(1 for t, rows in data.items() if t != 'lists' for r in rows if r[0])
            print('Loaded', os.path.abspath(p), '- %d keywords switched on' % n_on)
            if data.get('other'):
                print('Keywords not in the manual put in tab "other":', ', '.join(r[1] for r in data['other']))

    def on_load_params(self):
        p = filedialog.askopenfilename(title='Load params.txt',
                                       filetypes=[('XBeach params', '*.txt'), ('All files', '*.*')])
        if p:
            self.src_path.set(p)
            self.on_load()

    def on_reset(self):
        with self.logging():
            self.gui.set_data(default_data())
            self.out_name.set(DEFAULT_NAME)
            print('Reset to built-in defaults.')

    def on_save(self):
        with self.logging():
            p = self.save_path.get().strip()
            try:
                write_xlsx(self.gui.get_data(), p)
                print('Saved', os.path.abspath(p))
            except ImportError:
                print('Saving xlsx needs pandas + openpyxl (pip install pandas openpyxl).')
            except Exception as e:
                print('Could not save ->', e)

    def on_preview(self):
        with self.logging():
            data = self.gui.get_data()
            validate(data)
            print('-' * 60)
            print(to_params_text(data, self.write_disabled.get(), self.title_var.get()))

    def on_check(self):
        with self.logging():
            data = self.gui.get_data()
            validate(data)
            check_files(data, self.out_dir.get().strip() or '.')

    def on_generate(self):
        with self.logging():
            par_name, bat_name = run_file_names(self.out_name.get())
            d = self.out_dir.get().strip() or '.'
            data = self.gui.get_data()
            n = validate(data)
            if n and not messagebox.askyesno('xbgen', '%d warning(s) - see log.\nWrite anyway?' % n):
                print('Cancelled - nothing written.')
                return
            os.makedirs(d, exist_ok=True)
            par_file = os.path.join(d, par_name)
            if os.path.exists(par_file) and not messagebox.askyesno(
                    'xbgen', '%s exists.\nOverwrite?' % os.path.abspath(par_file)):
                print('Cancelled - nothing written.')
                return
            with open(par_file, 'wt', encoding='utf-8', newline='\n') as f:
                f.write(to_params_text(data, self.write_disabled.get(), self.title_var.get()))
            print('Writing params file done ->', os.path.abspath(par_file))
            if self.write_bat.get():
                bat_file = os.path.join(d, bat_name)
                if os.path.exists(bat_file) and not messagebox.askyesno(
                        'xbgen', '%s exists.\nOverwrite?' % os.path.abspath(bat_file)):
                    print('Run script kept as is.')
                else:
                    with open(bat_file, 'wt', encoding='utf-8', newline='') as f:
                        f.write(bat_text(par_name, self.exe.get().strip()))
                    print('Run script ->', os.path.abspath(bat_file))
            check_files(data, d)

    def _set_value(self, key, value):
        for rows in self.gui.rows.values():
            for r in rows:
                if r['vars'][1].get().lower() == key.lower():
                    r['vars'][2].set(value)
                    r['vars'][0].set(True)
                    return

    def on_nxny(self):
        with self.logging():
            start = self.out_dir.get().strip() or '.'
            p = filedialog.askopenfilename(title='Select xfile (x.grd)', initialdir=start)
            if not p:
                return
            nrow, ncol = grid_shape(p)
            self._set_value('nx', str(ncol - 1))
            self._set_value('ny', str(nrow - 1))
            try:
                rel = os.path.relpath(p, os.path.abspath(start)).replace('\\', '/')
            except ValueError:
                rel = p
            self._set_value('xfile', rel)
            self._set_value('vardx', '1')
            print('%s: %d x %d -> nx = %d, ny = %d, vardx = 1' % (rel, nrow, ncol, ncol - 1, nrow - 1))

    def on_jonswap(self):
        a = active(self.gui.get_data())
        win = tk.Toplevel(self)
        win.title('JONSWAP table (wbctype = jonstable)')
        ttk.Label(win, text='One row per condition: Hm0 Tp mainang gammajsp s duration dtbc   '
                            '(mainang nautical, 270 = shore-normal for alfa = 0)').grid(
            row=0, column=0, columnspan=7, sticky='w', padx=4, pady=4)
        dur = '%g' % (_f(a, 'tstop', 3600) - _f(a, 'tstart', 0))
        vs = {}
        for c, (k, dflt) in enumerate((('Hm0', '2'), ('Tp', '10'), ('mainang', '270'), ('gammajsp', '3.3'),
                                       ('s', '20'), ('duration', dur), ('dtbc', '1'))):
            ttk.Label(win, text=k).grid(row=1, column=c)
            vs[k] = tk.StringVar(value=dflt)
            ttk.Entry(win, textvariable=vs[k], width=9).grid(row=2, column=c, padx=2)
        append = tk.BooleanVar(value=False)
        ttk.Checkbutton(win, text='Append row to existing file', variable=append).grid(
            row=3, column=0, columnspan=3, sticky='w', padx=4, pady=4)

        def _write():
            d = self.out_dir.get().strip() or '.'
            p = filedialog.asksaveasfilename(parent=win, initialdir=d, defaultextension='.txt',
                                             initialfile=a.get('bcfile', 'jonswap.txt'))
            if not p:
                return
            row = ' '.join(vs[k].get().strip() for k in vs)
            with open(p, 'a' if append.get() else 'w', newline='\n') as f:
                f.write(row + '\n')
            try:
                rel = os.path.relpath(p, os.path.abspath(d)).replace('\\', '/')
            except ValueError:
                rel = p
            self._set_value('bcfile', rel)
            self._set_value('wbctype', 'jonstable')
            with self.logging():
                print('%s %s: %s  (bcfile = %s, wbctype = jonstable)'
                      % ('Appended to' if append.get() else 'Wrote', p, row, rel))
            win.destroy()

        ttk.Button(win, text='Write...', command=_write).grid(row=3, column=5, columnspan=2, pady=4)


def run(source=None, outdir=None):
    """Start the GUI, optionally loading a params.txt / .xlsx file."""
    App(source=source, outdir=outdir).mainloop()
