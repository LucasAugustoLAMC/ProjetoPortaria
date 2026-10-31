"""Controle de portaria: cadastro, pesquisa, saída e edição em lote validada."""
from datetime import datetime
from uuid import uuid4
import tkinter as tk
from tkinter import ttk, messagebox

from .theme import FONT, button, entry, text
from .fields import DateTimeInput
from ..config import TIPOS_ACESSO
from ..domain.validation import normalizar, ValidationError


class RecordDialog(tk.Toplevel):
    def __init__(self, parent, p, record, types, *, checkout_only=False):
        super().__init__(parent)
        self.title('Registrar saída' if checkout_only else 'Editar registro')
        self.configure(bg=p.card)
        self.result = None
        self.resizable(True, False)
        self.minsize(620, 350 if checkout_only else 470)
        body = tk.Frame(self, bg=p.card, padx=25, pady=22)
        body.pack(fill='both', expand=True)
        text(body, p, 'Registrar saída' if checkout_only else 'Editar registro', size=19, weight='bold').pack(anchor='w')
        text(body, p, record['Nome'] + '  •  ' + record['Tipo'], muted=True).pack(anchor='w', pady=(3, 18))
        self.name = entry(body, p, limit=100)
        self.name.insert(0, record['Nome'])
        self.type = ttk.Combobox(body, values=types, state='readonly')
        self.type.set(record['Tipo'])
        if not checkout_only:
            text(body, p, 'Nome completo', muted=True).pack(anchor='w')
            self.name.pack(fill='x', ipady=8, pady=(3, 12))
            text(body, p, 'Tipo de acesso', muted=True).pack(anchor='w')
            self.type.pack(fill='x', pady=(3, 12))
            text(body, p, 'Entrada', muted=True).pack(anchor='w')
            self.in_date = DateTimeInput(body, p, initial=record['Entrada'])
            self.in_date.pack(fill='x', pady=(3, 12))
        else:
            self.in_date = None
            text(body, p, 'Entrada registrada: ' + record['Entrada'], muted=True).pack(anchor='w', pady=(0, 12))
        text(body, p, 'Saída (deixe vazia se ainda estiver presente)', muted=True).pack(anchor='w')
        self.out_date = DateTimeInput(body, p, initial=record['Saida'], optional=True)
        self.out_date.pack(fill='x', pady=(4, 18))
        if checkout_only and not record['Saida']:
            self.out_date.set_now()
        actions = tk.Frame(body, bg=p.card)
        actions.pack(fill='x')
        button(actions, p, 'Cancelar', self.destroy, kind='secondary').pack(side='right', padx=(8, 0))
        button(actions, p, 'Salvar alteração', self.confirm).pack(side='right')
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.wait_window()

    def confirm(self):
        self.result = {'Saida': self.out_date.get()}
        if self.in_date:
            self.result.update({'Nome': self.name.get().strip(), 'Tipo': self.type.get(),
                                'Entrada': self.in_date.get()})
        self.destroy()


class RecordsView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.p.bg)
        self.app, self.s, self.p = app, app.service, app.p
        self.operation_id = str(uuid4())
        self.pending = tk.BooleanVar(value=False)
        self.search = tk.StringVar()
        self._narrow = None
        self._mobile_page = 'records'
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._header()
        self.body = tk.Frame(self, bg=self.p.bg)
        self.body.grid(row=1, column=0, sticky='nsew', padx=23, pady=(0, 15))
        self.form_holder = tk.Frame(self.body, bg=self.p.bg)
        self.form_holder.columnconfigure(0, weight=1)
        self.form_holder.rowconfigure(0, weight=1)
        self.form_canvas = tk.Canvas(self.form_holder, bg=self.p.bg, highlightthickness=0)
        self.form_canvas.grid(row=0, column=0, sticky='nsew')
        self.form_scroll = ttk.Scrollbar(self.form_holder, orient='vertical', command=self.form_canvas.yview)
        self.form_scroll.grid(row=0, column=1, sticky='ns')
        self.form_canvas.configure(yscrollcommand=self.form_scroll.set)
        self.form_card = tk.Frame(self.form_canvas, bg=self.p.card, padx=20, pady=19,
                                  highlightbackground=self.p.border, highlightthickness=1)
        self.form_window = self.form_canvas.create_window(0, 0, window=self.form_card, anchor='nw')
        self.form_card.bind('<Configure>', lambda _e: self.form_canvas.configure(
            scrollregion=self.form_canvas.bbox('all')))
        self.form_canvas.bind('<Configure>', lambda e: self.form_canvas.itemconfigure(
            self.form_window, width=e.width - 1))
        self._build_form()
        self.list_card = tk.Frame(self.body, bg=self.p.card, padx=18, pady=17,
                                  highlightbackground=self.p.border, highlightthickness=1)
        self._build_list()
        self.body.bind('<Configure>', self._layout)
        self.refresh()

    def _header(self):
        header = tk.Frame(self, bg=self.p.bg)
        header.grid(row=0, column=0, sticky='ew', padx=24, pady=(18, 14))
        text(header, self.p, 'Controle de acessos', bg=self.p.bg, size=21, weight='bold').pack(anchor='w')
        text(header, self.p, 'Registre entradas, acompanhe quem está presente e finalize saídas.',
             bg=self.p.bg, muted=True).pack(anchor='w', pady=(3, 0))
        self.counts = text(header, self.p, '', bg=self.p.bg, muted=True)
        self.counts.pack(anchor='w', pady=(9, 0))
        self.mobile_controls = tk.Frame(header, bg=self.p.bg)
        button(self.mobile_controls, self.p, 'Ver histórico', lambda: self._select_mobile('records'),
               kind='secondary').pack(side='left', padx=(0, 8))
        button(self.mobile_controls, self.p, '+ Nova entrada', lambda: self._select_mobile('form')).pack(side='left')

    def _build_form(self):
        p, f = self.p, self.form_card
        text(f, p, 'Nova entrada', size=16, weight='bold').pack(anchor='w')
        text(f, p, 'Dados obrigatórios marcados com *', muted=True).pack(anchor='w', pady=(3, 16))
        text(f, p, 'Nome da pessoa *', muted=True).pack(anchor='w')
        self.name = entry(f, p, limit=100)
        self.name.pack(fill='x', ipady=8, pady=(4, 10))
        text(f, p, 'Tipo de acesso *', muted=True).pack(anchor='w')
        type_box = tk.Frame(f, bg=p.card)
        type_box.pack(fill='x', pady=(4, 12))
        type_box.columnconfigure(0, weight=1)
        self.type = ttk.Combobox(type_box, values=(), state='readonly')
        self.type.grid(row=0, column=0, sticky='ew')
        button(type_box, p, '+ Tipo', self.add_type, kind='secondary', padx=8).grid(row=0, column=1, padx=(7, 0))
        text(f, p, 'Data e hora de entrada *', muted=True).pack(anchor='w')
        self.in_date = DateTimeInput(f, p)
        self.in_date.pack(fill='x', pady=(4, 5))
        button(f, p, 'Usar data e hora atuais', self.in_date.set_now, kind='link',
               anchor='w', padx=2, pady=5).pack(anchor='w', pady=(0, 8))
        text(f, p, 'Data e hora de saída (opcional)', muted=True).pack(anchor='w')
        self.out_date = DateTimeInput(f, p, optional=True)
        self.out_date.pack(fill='x', pady=(4, 18))
        self.submit = button(f, p, 'Cadastrar entrada', self.create)
        self.submit.pack(fill='x')
        button(f, p, 'Limpar formulário', self.clear, kind='secondary').pack(fill='x', pady=(8, 0))
        self.in_date.set_now()
        self.load_types()

    def load_types(self):
        types = TIPOS_ACESSO + self.s.tipos_temporarios_ativos()
        current = self.type.get()
        self.type['values'] = types
        self.type.set(current if current in types else types[0])

    def add_type(self):
        from tkinter import simpledialog
        name = simpledialog.askstring('Tipo de acesso', 'Nome do novo tipo temporário (24 horas):', parent=self)
        if name is None:
            return
        def work():
            result = self.s.criar_tipo_temporario(name)
            self.load_types()
            self.type.set(result)
            self.app.toast('Tipo temporário disponível por 24 horas.')
        self.app.execute(work)

    def _build_list(self):
        p, f = self.p, self.list_card
        title_line = tk.Frame(f, bg=p.card)
        title_line.pack(fill='x')
        text(title_line, p, 'Histórico de acessos', size=16, weight='bold').pack(side='left')
        self.total_text = text(title_line, p, '', muted=True)
        self.total_text.pack(side='right')
        search_row = tk.Frame(f, bg=p.card)
        search_row.pack(fill='x', pady=(15, 10))
        self.search_entry = entry(search_row, p, textvariable=self.search)
        self.search_entry.pack(side='left', fill='x', expand=True, ipady=8)
        self.search_entry.insert(0, '')
        self.search.trace_add('write', lambda *_: self.refresh())
        tk.Checkbutton(f, text='Apenas pessoas sem saída', variable=self.pending,
                       bg=p.card, fg=p.text, activebackground=p.card,
                       selectcolor=p.card, command=self.refresh,
                       font=(FONT, 10)).pack(anchor='w', pady=(0, 10))
        grid = tk.Frame(f, bg=p.card)
        grid.pack(fill='both', expand=True)
        grid.columnconfigure(0, weight=1)
        grid.rowconfigure(0, weight=1)
        cols = ('Nome', 'Tipo', 'Entrada', 'Saida')
        self.table = ttk.Treeview(grid, columns=cols, show='headings', selectmode='extended', height=3)
        for col, width in (('Nome', 180), ('Tipo', 120), ('Entrada', 148), ('Saida', 148)):
            self.table.heading(col, text=col if col != 'Saida' else 'Saída')
            self.table.column(col, width=width, minwidth=90, anchor='w', stretch=True)
        self.table.grid(row=0, column=0, sticky='nsew')
        vert = ttk.Scrollbar(grid, orient='vertical', command=self.table.yview)
        vert.grid(row=0, column=1, sticky='ns')
        horiz = ttk.Scrollbar(grid, orient='horizontal', command=self.table.xview)
        horiz.grid(row=1, column=0, sticky='ew')
        self.table.configure(yscrollcommand=vert.set, xscrollcommand=horiz.set)
        self.table.tag_configure('pending', background=p.pill)
        self.table.bind('<Double-1>', lambda _e: self.edit())
        action_row = tk.Frame(f, bg=p.card)
        action_row.pack(fill='x', pady=(14, 0))
        self.checkout_btn = button(action_row, p, 'Registrar saída', self.checkout)
        self.checkout_btn.pack(side='left')
        if self.s.pode('editar'):
            button(action_row, p, 'Editar', self.edit, kind='secondary').pack(side='left', padx=7)
        if self.s.pode('excluir'):
            button(action_row, p, 'Excluir', self.remove, kind='danger').pack(side='right')

    def _select_mobile(self, page):
        self._mobile_page = page
        if self._narrow:
            self.form_holder.grid_forget()
            self.list_card.grid_forget()
            if page == 'form':
                self.form_holder.grid(row=0, column=0, sticky='nsew')
            else:
                self.list_card.grid(row=0, column=0, sticky='nsew')

    def _layout(self, event):
        narrow = event.width < 925
        if narrow == self._narrow:
            return
        self._narrow = narrow
        self.form_holder.grid_forget()
        self.list_card.grid_forget()
        if narrow:
            self.mobile_controls.pack(anchor='w', pady=(9, 0))
            self.body.columnconfigure(0, weight=1, minsize=0)
            self.body.columnconfigure(1, weight=0, minsize=0)
            self.body.rowconfigure(0, weight=1)
            self._select_mobile(self._mobile_page)
        else:
            self.mobile_controls.pack_forget()
            self.body.columnconfigure(0, weight=0, minsize=370)
            self.body.columnconfigure(1, weight=1)
            self.body.rowconfigure(0, weight=1)
            self.form_holder.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
            self.list_card.grid(row=0, column=1, sticky='nsew')

    def refresh(self):
        if not hasattr(self, 'table'):
            return
        selected = set(self.table.selection())
        self.table.delete(*self.table.get_children())
        terms = normalizar(self.search.get()).split()
        shown = 0
        for reg in reversed(self.s.registros):
            if self.pending.get() and reg['Saida']:
                continue
            combined = normalizar(' '.join([reg['Nome'], reg['Tipo'], reg['Entrada'], reg['Saida']]))
            if not all(t in combined for t in terms):
                continue
            self.table.insert('', 'end', iid=reg['Id'], values=(reg['Nome'],
                reg['Tipo'] + (' · temporário' if reg['Tipo'] not in TIPOS_ACESSO else ''),
                reg['Entrada'], reg['Saida'] or 'Em aberto'), tags=('pending',) if not reg['Saida'] else ())
            shown += 1
        for key in selected:
            if self.table.exists(key):
                self.table.selection_add(key)
        pending = sum(not r['Saida'] for r in self.s.registros)
        self.counts.configure(text=f'{len(self.s.registros)} entradas registradas  ·  {pending} pessoas sem saída')
        self.total_text.configure(text=f'{shown} exibido(s)')

    def clear(self):
        self.name.delete(0, 'end')
        self.type.set(TIPOS_ACESSO[0])
        self.in_date.set_now()
        self.out_date.set('')
        self.operation_id = str(uuid4())
        self.name.focus_set()

    def create(self):
        def work():
            self.s.cadastrar(self.name.get(), self.type.get(), self.in_date.get(),
                             self.out_date.get(), operation_id=self.operation_id)
            self.clear()
            self._select_mobile('records')
            self.refresh()
            self.app.toast('Entrada cadastrada com sucesso.')
        self.app.execute(work, controls=[self.submit])

    def one_record(self):
        selected = self.table.selection()
        if len(selected) != 1:
            messagebox.showwarning('Seleção necessária', 'Selecione exatamente um registro.', parent=self)
            return None
        return self.s.buscar_registro(selected[0])

    def checkout(self):
        reg = self.one_record()
        if not reg:
            return
        if reg['Saida']:
            messagebox.showinfo('Saída já registrada', 'Este registro já possui saída. Use Editar para corrigir.', parent=self)
            return
        dialog = RecordDialog(self, self.p, reg, [], checkout_only=True)
        if dialog.result:
            self.app.execute(lambda: (self.s.editar(reg['Id'], 'Saida', dialog.result['Saida']),
                                      self.refresh(), self.app.toast('Saída registrada.')))

    def edit(self):
        reg = self.one_record()
        if not reg:
            return
        only_checkout = not self.s.pode('editar') and not reg['Saida']
        if not self.s.pode('editar') and not only_checkout:
            messagebox.showwarning('Sem permissão', 'Seu cargo não pode editar este registro.', parent=self)
            return
        dialog = RecordDialog(self, self.p, reg, TIPOS_ACESSO + self.s.tipos_temporarios_ativos(),
                              checkout_only=only_checkout)
        if dialog.result is not None:
            def work():
                self.s.atualizar_registro(reg['Id'], dialog.result)
                self.refresh()
                self.app.toast('Alteração salva.')
            self.app.execute(work)

    def remove(self):
        ids = self.table.selection()
        if not ids:
            messagebox.showwarning('Seleção necessária', 'Selecione os registros a excluir.', parent=self)
            return
        if not messagebox.askyesno('Confirmar exclusão',
                f'Excluir {len(ids)} registro(s)? Esta ação será registrada na auditoria.', parent=self):
            return
        def work():
            n = self.s.excluir(ids)
            self.refresh()
            self.app.toast(f'{n} registro(s) excluído(s).')
        self.app.execute(work)
