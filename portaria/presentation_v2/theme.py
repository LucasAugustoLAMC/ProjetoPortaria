"""Design system com tokens para alternância de temas sem acoplamento ao negócio."""
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    card: str
    sidebar: str
    field: str
    text: str
    muted: str
    border: str
    primary: str
    primary_hover: str
    on_primary: str
    danger: str
    warning: str
    success: str
    selection: str
    pill: str


THEMES = {
    'Claro': Palette('Claro', '#F4F7FB', '#FFFFFF', '#102238', '#F8FAFD', '#152A42', '#657589', '#DCE5EF', '#2772DB', '#195CB7', '#FFFFFF', '#B53443', '#9A630B', '#187650', '#E8F1FF', '#E6F1ED'),
    'Escuro': Palette('Escuro', '#101722', '#192433', '#142132', '#233247', '#ECF3FA', '#ACBBD0', '#36475C', '#68A8FF', '#448FEF', '#102036', '#FF798A', '#F7BE64', '#5AD5A5', '#304966', '#203B40'),
    'Floresta': Palette('Floresta', '#EFF4F0', '#FFFFFF', '#18352A', '#F6F9F5', '#1C342B', '#61766C', '#D7E5DA', '#287D59', '#1B6345', '#FFFFFF', '#B1434E', '#9E651C', '#227852', '#E3F2E8', '#E5F3E9'),
}

FONT = 'Segoe UI'


def setup_ttk(root: tk.Tk, p: Palette):
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('Treeview', background=p.card, foreground=p.text, fieldbackground=p.card,
                    bordercolor=p.border, borderwidth=0, rowheight=38, font=(FONT, 10))
    style.configure('Treeview.Heading', background=p.field, foreground=p.muted, relief='flat',
                    padding=(10, 12), font=(FONT, 10, 'bold'))
    style.map('Treeview', background=[('selected', p.selection)], foreground=[('selected', p.text)])
    style.map('Treeview.Heading', background=[('active', p.selection)])
    style.configure('TCombobox', background=p.card, fieldbackground=p.field, foreground=p.text,
                    padding=7, bordercolor=p.border, arrowcolor=p.text, selectbackground=p.selection)
    style.map('TCombobox', fieldbackground=[('readonly', p.field)], foreground=[('readonly', p.text)])
    style.configure('TScrollbar', gripcount=0, background=p.border, troughcolor=p.bg,
                    borderwidth=0, arrowsize=11)
    root.option_add('*Font', f'{{{FONT}}} 10')


def frame(parent, p, *, card=False, **kwargs):
    return tk.Frame(parent, bg=p.card if card else p.bg, **kwargs)


def text(parent, p, value, *, size=10, weight='normal', muted=False, bg=None, **kwargs):
    return tk.Label(parent, text=value, bg=bg or p.card,
                    fg=p.muted if muted else p.text, font=(FONT, size, weight),
                    anchor='w', **kwargs)


def button(parent, p, title, command, *, kind='primary', **kwargs):
    styles = {
        'primary': (p.primary, p.on_primary, p.primary_hover),
        'secondary': (p.field, p.text, p.selection),
        'danger': (p.danger, '#FFFFFF', p.danger),
        'sidebar': (p.sidebar, '#E6EDF7', p.primary),
        'link': (p.card, p.primary, p.selection),
    }
    bg, fg, hover = styles[kind]
    options = dict(text=title, command=command, bg=bg, fg=fg,
                   activebackground=hover, activeforeground=fg, relief='flat', borderwidth=0,
                   padx=16, pady=10, cursor='hand2', highlightthickness=0,
                   font=(FONT, 10, 'bold'))
    options.update(kwargs)
    btn = tk.Button(parent, **options)
    btn.bind('<Enter>', lambda _e: btn.configure(bg=hover) if btn['state'] == 'normal' else None)
    btn.bind('<Leave>', lambda _e: btn.configure(bg=bg))
    return btn


def entry(parent, p, *, show=None, limit=None, **kwargs):
    if limit is not None:
        cmd = parent.register(lambda candidate: len(candidate) <= limit)
        kwargs.update(validate='key', validatecommand=(cmd, '%P'))
    return tk.Entry(parent, relief='flat', borderwidth=0,
                    bg=p.field, fg=p.text, insertbackground=p.text, highlightthickness=1,
                    highlightcolor=p.primary, highlightbackground=p.border,
                    font=(FONT, 11), show=show or '', **kwargs)


def field(parent, p, label, *, show=None, limit=None, row=None, column=0, sticky='ew'):
    box = tk.Frame(parent, bg=p.card)
    text(box, p, label, muted=True, size=9, bg=p.card).pack(anchor='w', pady=(0, 5))
    ent = entry(box, p, show=show, limit=limit)
    ent.pack(fill='x', ipady=8)
    if row is not None:
        box.grid(row=row, column=column, sticky=sticky, padx=6, pady=6)
    return ent
