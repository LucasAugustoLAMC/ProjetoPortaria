"""Auditoria com filtro e inspeção do evento original."""
import tkinter as tk
from tkinter import ttk
from .theme import FONT, text


class AuditView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.p.bg)
        self.app, p = app, app.p
        text(self, p, 'Histórico de alterações', size=21, weight='bold', bg=p.bg).pack(anchor='w', padx=24, pady=(22, 4))
        text(self, p, 'Consulte edições e exclusões. A primeira saída não gera um evento de edição.',
             muted=True, bg=p.bg).pack(anchor='w', padx=24, pady=(0, 18))
        card = tk.Frame(self, bg=p.card, padx=20, pady=16, highlightbackground=p.border, highlightthickness=1)
        card.pack(fill='both', expand=True, padx=24, pady=(0, 18))
        self.filter = tk.StringVar(value='Todos')
        bar = tk.Frame(card, bg=p.card)
        bar.pack(fill='x', pady=(0, 12))
        text(bar, p, 'Mostrar', muted=True).pack(side='left', padx=(0, 10))
        box = ttk.Combobox(bar, textvariable=self.filter, values=['Todos', 'Edições', 'Exclusões', 'Gestão de usuários', 'Tipos de acesso'], state='readonly', width=17)
        box.pack(side='left')
        box.bind('<<ComboboxSelected>>', lambda *_: self.refresh())
        self.count = text(bar, p, '', muted=True)
        self.count.pack(side='right')
        area = tk.Frame(card, bg=p.card)
        area.pack(fill='both', expand=True)
        area.columnconfigure(0, weight=1)
        area.rowconfigure(0, weight=1)
        cols = ('Quando', 'Acao', 'Usuario', 'Nome', 'Campo', 'Anterior', 'Novo')
        self.table = ttk.Treeview(area, columns=cols, show='headings', selectmode='browse')
        for col, width in (('Quando',155), ('Acao',90), ('Usuario',130), ('Nome',140),
                           ('Campo',130), ('Anterior',200), ('Novo',200)):
            self.table.heading(col, text={'Quando':'Quando','Acao':'Ação','Usuario':'Responsável',
                'Nome':'Pessoa','Campo':'Campo','Anterior':'Valor anterior','Novo':'Novo valor'}[col])
            self.table.column(col, width=width, minwidth=80)
        self.table.grid(row=0, column=0, sticky='nsew')
        sy = ttk.Scrollbar(area, orient='vertical', command=self.table.yview)
        sy.grid(row=0, column=1, sticky='ns')
        sx = ttk.Scrollbar(area, orient='horizontal', command=self.table.xview)
        sx.grid(row=1, column=0, sticky='ew')
        self.table.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.table.bind('<<TreeviewSelect>>', self.inspect)
        self.detail = text(card, p, 'Selecione uma linha para consultar os valores completos.',
                           muted=True, wraplength=900, justify='left')
        self.detail.pack(fill='x', pady=(16, 0))
        self.events = []
        self.refresh()

    def refresh(self):
        self.table.delete(*self.table.get_children())
        events = list(reversed(self.app.service.auditoria))
        actions = {
            'Edições': {'EDIÇÃO'}, 'Exclusões': {'EXCLUSÃO'},
            'Gestão de usuários': {'USUÁRIO','PAPEL','DESBLOQUEIO','EXCLUSÃO DE USUÁRIO'},
            'Tipos de acesso': {'TIPO DE ACESSO'},
        }
        if self.filter.get() in actions:
            events = [e for e in events if e['Acao'] in actions[self.filter.get()]]
        self.events = events
        for i, e in enumerate(events):
            self.table.insert('', 'end', iid=str(i), values=tuple(e.get(c, '') for c in (
                'Quando', 'Acao', 'Usuario', 'Nome', 'Campo', 'Anterior', 'Novo')))
        self.count.configure(text=f'{len(events)} evento(s)')

    def inspect(self, *_):
        selected = self.table.selection()
        if not selected:
            return
        e = self.events[int(selected[0])]
        self.detail.configure(text=f"{e['Acao']}  |  {e['Quando']}  |  {e['Usuario']}\n"
                                   f"Campo: {e['Campo']}\nAntes: {e['Anterior']}\nDepois: {e['Novo']}")
