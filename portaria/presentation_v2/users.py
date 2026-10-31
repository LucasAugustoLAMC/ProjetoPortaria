"""Formulários de contas e administração de permissões."""
import tkinter as tk
import re
from tkinter import ttk, messagebox
from ..config import CARGO_FINAL, CARGO_ADM, CARGO_USUARIO
from ..domain.validation import so_digitos, formatar_cpf, mascarar_cpf
from .theme import FONT, text, button, field
from .scrollable import ScrollableCard


class UserForm(tk.Frame):
    def __init__(self, parent, app, on_created, *, initial_admin=False):
        super().__init__(parent, bg=app.p.card)
        self.app = app
        self.on_created = on_created
        self.admin = initial_admin
        p = app.p
        self.columnconfigure((0, 1), weight=1, uniform='fields')
        text(self, p, 'Dados do usuário', size=14, weight='bold').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 8))
        self.name = field(self, p, 'Nome completo *', row=1, column=0, limit=100)
        self.display = field(self, p, 'Nome de exibição *', row=1, column=1, limit=25)
        self.email = field(self, p, 'E-mail *', row=2, column=0, limit=150)
        self.cpf = field(self, p, 'CPF *', row=2, column=1, limit=14)
        validator = self.cpf.register(lambda v: len(v) <= 14 and re.fullmatch(r'[0-9.\-]*', v) is not None)
        self.cpf.configure(validate='key', validatecommand=(validator, '%P'))
        self.cpf.bind('<KeyRelease>', self._format_cpf)
        self.cpf.bind('<<Paste>>', lambda _e: self.after_idle(self._format_cpf))
        text(self, p, 'Papel de acesso', muted=True).grid(row=3, column=0, sticky='w', padx=6, pady=(6, 2))
        self.role = ttk.Combobox(self, values=[CARGO_FINAL] if initial_admin else [CARGO_ADM, CARGO_USUARIO],
                                 state='readonly')
        self.role.set(CARGO_FINAL if initial_admin else CARGO_USUARIO)
        self.role.grid(row=4, column=0, columnspan=2, sticky='ew', padx=6, pady=(0, 12))
        text(self, p, 'Credenciais e recuperação', size=14, weight='bold').grid(row=5, column=0, columnspan=2, sticky='w', pady=(4, 6))
        self.password = field(self, p, 'Senha *', row=6, column=0, show='•')
        self.confirm = field(self, p, 'Confirmar senha *', row=6, column=1, show='•')
        self.reveal = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text='Mostrar senhas', variable=self.reveal, bg=p.card,
                       fg=p.text, activebackground=p.card, selectcolor=p.card,
                       command=lambda: [w.configure(show='' if self.reveal.get() else '•')
                                        for w in (self.password, self.confirm)]).grid(
                                            row=7, column=0, columnspan=2, sticky='w', padx=6)
        self.words_hint = text(self, p, 'Três palavras diferentes, somente letras (4–20 caracteres).',
                               muted=True, justify='left')
        self.words_hint.grid(row=8, column=0, columnspan=2, sticky='w', padx=6, pady=(6, 4))
        self.words = []
        for i in range(3):
            e = field(self, p, f'Palavra {i + 1} *', row=9 + (i // 2), column=i % 2, limit=20)
            self.words.append(e)
        self.save_btn = button(self, p, 'Criar Admin Final' if initial_admin else 'Criar usuário', self.save)
        self.save_btn.grid(row=11, column=0, columnspan=2, sticky='ew', padx=6, pady=(18, 3))
        # Preserve as posições originais para alternar entre duas e uma coluna.
        self._wide_grid = {widget: dict(widget.grid_info()) for widget in self.grid_slaves()}
        self._narrow = None
        self.bind('<Configure>', self._responsive)

    def _responsive(self, event):
        narrow = event.width < 485
        self.words_hint.configure(wraplength=max(170, event.width - 20))
        if narrow == self._narrow:
            return
        self._narrow = narrow
        if narrow:
            self.columnconfigure(0, weight=1, uniform='')
            self.columnconfigure(1, weight=0, uniform='')
            ordered = sorted(self._wide_grid.items(),
                             key=lambda item: (int(item[1]['row']), int(item[1]['column'])))
            for row, (widget, _) in enumerate(ordered):
                align = 'w' if isinstance(widget, (tk.Label, tk.Checkbutton)) else 'ew'
                widget.grid_configure(row=row, column=0, columnspan=1, sticky=align)
        else:
            self.columnconfigure((0, 1), weight=1, uniform='fields')
            for widget, grid in self._wide_grid.items():
                widget.grid_configure(row=grid['row'], column=grid['column'],
                                      columnspan=grid['columnspan'], sticky=grid['sticky'])

    def _format_cpf(self, _event=None):
        raw = self.cpf.get()
        formatted = formatar_cpf(raw)
        if raw != formatted:
            self.cpf.delete(0, 'end')
            self.cpf.insert(0, formatted)

    def save(self):
        if self.password.get() != self.confirm.get():
            messagebox.showwarning('Confirmação incorreta', 'As duas senhas devem ser iguais.', parent=self)
            return
        def work():
            user = self.app.service.cadastrar_usuario(
                ' '.join(self.name.get().split()), ' '.join(self.display.get().split()),
                self.email.get().strip().lower(), so_digitos(self.cpf.get()),
                self.role.get(), self.password.get(), [e.get().strip().lower() for e in self.words])
            self.on_created(user)
        self.app.execute(work, controls=[self.save_btn])


class UserDialog(tk.Toplevel):
    def __init__(self, parent, app, on_created):
        super().__init__(parent)
        p = app.p
        self.title('Novo usuário')
        self.configure(bg=p.card)
        self.geometry('690x650')
        self.minsize(450, 440)
        scroller = ScrollableCard(self, p, max_width=690, padding_x=26, padding_y=20)
        scroller.pack(fill='both', expand=True)
        body = scroller.content
        text(body, p, 'Cadastrar novo usuário', size=19, weight='bold').pack(anchor='w')
        subtitle = text(body, p, 'Escolha o nível de acesso. Senhas e respostas são armazenadas com hash.',
                        muted=True, wraplength=520, justify='left')
        subtitle.pack(anchor='w', pady=(4, 12))
        body.bind('<Configure>', lambda event: subtitle.configure(
            wraplength=max(160, event.width - 60)), add='+')
        form = UserForm(body, app, lambda u: (on_created(u), self.destroy()))
        form.pack(fill='x', expand=True)
        scroller.bind_descendants()
        self.transient(parent.winfo_toplevel())
        self.grab_set()


class UsersView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.p.bg)
        self.app, p = app, app.p
        text(self, p, 'Usuários e permissões', size=21, weight='bold', bg=p.bg).pack(anchor='w', padx=24, pady=(22, 4))
        text(self, p, 'Gerencie contas por papel. O Admin Final não pode ser excluído ou rebaixado.',
             bg=p.bg, muted=True).pack(anchor='w', padx=24, pady=(0, 16))
        card = tk.Frame(self, bg=p.card, padx=20, pady=16, highlightbackground=p.border, highlightthickness=1)
        card.pack(fill='both', expand=True, padx=24, pady=(0, 18))
        bar = tk.Frame(card, bg=p.card)
        bar.pack(fill='x', pady=(0, 14))
        button(bar, p, '+ Novo usuário', self.add).pack(side='left')
        button(bar, p, 'Alterar papel', self.change_role, kind='secondary').pack(side='left', padx=7)
        button(bar, p, 'Desbloquear', self.unlock, kind='secondary').pack(side='left')
        button(bar, p, 'Excluir', self.delete, kind='danger').pack(side='right')
        area = tk.Frame(card, bg=p.card)
        area.pack(fill='both', expand=True)
        area.rowconfigure(0, weight=1)
        area.columnconfigure(0, weight=1)
        cols = ('NomeExibicao','NomeCompleto','Cargo','Email','CPF','Status')
        self.table = ttk.Treeview(area, columns=cols, show='headings', selectmode='browse')
        for col, title, width in [
            ('NomeExibicao','Exibição',120), ('NomeCompleto','Nome completo',165),
            ('Cargo','Papel',105),('Email','E-mail',220),('CPF','CPF',135),('Status','Status',110)]:
            self.table.heading(col, text=title)
            self.table.column(col, width=width, minwidth=85)
        self.table.grid(row=0, column=0, sticky='nsew')
        sy = ttk.Scrollbar(area, orient='vertical', command=self.table.yview)
        sy.grid(row=0, column=1, sticky='ns')
        sx = ttk.Scrollbar(area, orient='horizontal', command=self.table.xview)
        sx.grid(row=1, column=0, sticky='ew')
        self.table.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.refresh()

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for u in self.app.service.usuarios:
            minutes = self.app.service.minutos_bloqueio_restantes(u)
            self.table.insert('', 'end', iid=u['Id'], values=(u['NomeExibicao'],u['NomeCompleto'],
                u['Cargo'],u['Email'],mascarar_cpf(u['CPF']), f'Bloqueado ({minutes} min)' if minutes else 'Ativo'))

    def selected(self):
        ids = self.table.selection()
        if not ids:
            messagebox.showwarning('Selecione um usuário', 'Escolha uma conta na tabela.', parent=self)
            return None
        return self.app.service.achar_usuario_por_id(ids[0])

    def add(self):
        UserDialog(self, self.app, lambda _u: (self.refresh(), self.app.toast('Usuário criado.')))

    def change_role(self):
        u = self.selected()
        if not u:
            return
        if u['Cargo'] == CARGO_FINAL:
            messagebox.showwarning('Papel protegido', 'O Admin Final não pode ser rebaixado.', parent=self)
            return
        new = CARGO_ADM if u['Cargo'] == CARGO_USUARIO else CARGO_USUARIO
        if messagebox.askyesno('Alterar permissões', f'Alterar {u["NomeExibicao"]} para {new}?', parent=self):
            self.app.execute(lambda: (self.app.service.alterar_cargo(u, new), self.refresh(),
                                      self.app.toast('Papel atualizado.')))

    def unlock(self):
        u = self.selected()
        if u:
            self.app.execute(lambda: (self.app.service.desbloquear_usuario(u), self.refresh(),
                                      self.app.toast('Conta desbloqueada.')))

    def delete(self):
        u = self.selected()
        if not u:
            return
        if messagebox.askyesno('Excluir conta', f'Remover o acesso de {u["NomeExibicao"]}?', parent=self):
            self.app.execute(lambda: (self.app.service.excluir_usuario(u), self.refresh(),
                                      self.app.toast('Conta excluída.')))
