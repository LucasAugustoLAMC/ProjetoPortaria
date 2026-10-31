"""Composição e navegação da interface v2. Sem regras de negócio em callbacks."""
import json
import logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from ..application.service import PortariaService
from ..config import DATA_DIR
from ..domain.validation import ValidationError, PermissionDenied
from ..infrastructure.storage import StorageError, _atomic_write
from .theme import THEMES, FONT, setup_ttk, text, button
from .auth import AuthView
from .records import RecordsView
from .audit import AuditView
from .users import UsersView


class PortariaApp(tk.Tk):
    def __init__(self, *, data_dir=None):
        super().__init__()
        self.title('Portaria • Controle de acessos')
        self.geometry('1280x790')
        self.minsize(520, 480)
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.settings_path = self.data_dir / 'ui_settings.json'
        self.theme_name = self._load_theme()
        self.p = THEMES[self.theme_name]
        self.service = PortariaService(self.data_dir)
        self._busy = False
        self._current_page = 'records'
        self._dashboard = False
        self._is_compact = False
        self._nav_visible = True
        self.configure(bg=self.p.bg)
        setup_ttk(self, self.p)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.report_callback_exception = self._callback_error
        try:
            if self.service.cofre_existe:
                self.show_auth('unlock')
            else:
                self.service.carregar()
                self.show_auth('migrate' if self.service.usuarios else 'setup')
        except (StorageError, ValidationError) as exc:
            self.show_fatal(str(exc))

    def _load_theme(self):
        try:
            settings = json.loads(self.settings_path.read_text(encoding='utf-8'))
            if isinstance(settings, dict) and settings.get('theme') in THEMES:
                return settings['theme']
        except (OSError, ValueError, TypeError):
            pass
        return 'Claro'

    def change_theme(self, name):
        if name not in THEMES or name == self.theme_name:
            return
        # Preferências de interface não contêm dados sensíveis.
        _atomic_write(self.settings_path, lambda f: json.dump({'theme': name}, f, ensure_ascii=False))
        self.theme_name, self.p = name, THEMES[name]
        self.configure(bg=self.p.bg)
        setup_ttk(self, self.p)
        if self._dashboard:
            self.show_dashboard(self._current_page)
        else:
            self.show_auth(getattr(self, 'auth_mode', 'login'))

    def _clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_fatal(self, reason):
        self._clear()
        pane = tk.Frame(self, bg=self.p.card, padx=30, pady=30)
        pane.pack(expand=True)
        text(pane, self.p, 'Não foi possível abrir a base', size=19, weight='bold').pack(anchor='w')
        text(pane, self.p, reason, muted=True, wraplength=520).pack(anchor='w', pady=(15, 12))
        text(pane, self.p, 'Nenhum arquivo foi sobrescrito. Verifique as permissões, o backup e o log.',
             muted=True, wraplength=520).pack(anchor='w')
        button(pane, self.p, 'Sair', self.destroy).pack(anchor='e', pady=(18, 0))

    def show_auth(self, mode='login'):
        self._dashboard = False
        self.auth_mode = mode
        self._clear()
        AuthView(self, self, mode).pack(fill='both', expand=True)

    def show_recovery_code(self):
        code = self.service.chave_recuperacao
        if not code:
            return
        dialog = tk.Toplevel(self)
        dialog.configure(bg=self.p.card)
        dialog.title('Código de recuperação — guardar agora')
        dialog.geometry('680x300')
        dialog.minsize(600, 285)
        dialog.transient(self)
        dialog.grab_set()
        frame = tk.Frame(dialog, bg=self.p.card, padx=28, pady=25)
        frame.pack(fill='both', expand=True)
        text(frame, self.p, 'Guarde seu código de emergência', size=19, weight='bold').pack(anchor='w')
        text(frame, self.p, 'Este código aparece apenas uma vez. Guarde fora do computador e da pasta do sistema.',
             muted=True, wraplength=580).pack(anchor='w', pady=(8, 18))
        value = tk.Entry(frame, bg=self.p.field, fg=self.p.text, relief='flat', font=(FONT, 12),
                         readonlybackground=self.p.field, justify='center')
        value.insert(0, code)
        value.configure(state='readonly')
        value.pack(fill='x', ipady=10)
        accepted = tk.BooleanVar(value=False)
        tk.Checkbutton(frame, text='Guardei o código em um local seguro.', variable=accepted,
                       bg=self.p.card, fg=self.p.text, selectcolor=self.p.card,
                       activebackground=self.p.card).pack(anchor='w', pady=(16, 7))
        def confirm():
            if not accepted.get():
                messagebox.showwarning('Confirmação obrigatória', 'Confirme que guardou o código.', parent=dialog)
                return
            self.service.chave_recuperacao = None
            dialog.destroy()
        button(frame, self.p, 'Concluir', confirm).pack(anchor='e')
        dialog.protocol('WM_DELETE_WINDOW', confirm)
        dialog.wait_window()

    def show_dashboard(self, page='records'):
        self._dashboard = True
        self._current_page = page
        self._clear()
        self.columnconfigure(0, weight=0, minsize=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.sidebar = tk.Frame(self, bg=self.p.sidebar, width=238)
        self.sidebar.grid(row=0, column=0, sticky='ns')
        self.sidebar.grid_propagate(False)
        self._make_sidebar()
        main = tk.Frame(self, bg=self.p.bg)
        main.grid(row=0, column=1, sticky='nsew')
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        bar = tk.Frame(main, bg=self.p.card, padx=18, pady=12)
        bar.grid(row=0, column=0, sticky='ew')
        self.menu_btn = button(bar, self.p, '☰', self.toggle_nav, kind='secondary', padx=12)
        self.menu_btn.pack(side='left', padx=(0, 10))
        text(bar, self.p, 'PAINEL DE CONTROLE', size=10, weight='bold').pack(side='left')
        user = self.service.sessao['usuario']
        text(bar, self.p, f'{user["NomeExibicao"]}  •  {user["Cargo"]}', muted=True).pack(side='right')
        self.content = tk.Frame(main, bg=self.p.bg)
        self.content.grid(row=1, column=0, sticky='nsew')
        self.footer = text(main, self.p, 'Base local protegida  ·  Acesso sujeito a permissões',
                           bg=self.p.bg, muted=True, size=9)
        self.footer.grid(row=2, column=0, sticky='ew', padx=24, pady=(4, 9))
        self.bind('<Configure>', self._responsive)
        self._responsive()
        self.show_page(page)

    def _make_sidebar(self):
        p = self.p
        mark = tk.Frame(self.sidebar, bg=p.sidebar)
        mark.pack(fill='x', padx=22, pady=(25, 22))
        tk.Label(mark, text='P', font=(FONT, 22, 'bold'), bg=p.primary, fg=p.on_primary,
                 width=2, height=1).pack(side='left')
        tk.Label(mark, text='PORTARIA\n  Gestor de acessos', bg=p.sidebar, fg='#F4F7FC',
                 font=(FONT, 11, 'bold'), justify='left').pack(side='left', padx=11)
        tk.Label(self.sidebar, text='MENU', bg=p.sidebar, fg='#AFC0D4',
                 font=(FONT, 9, 'bold')).pack(anchor='w', padx=22, pady=(7, 9))
        nav = [('records', 'Controle de acessos', None),
               ('audit', 'Auditoria', 'auditoria'),
               ('users', 'Usuários e permissões', 'usuarios'),
               ('settings', 'Aparência e sistema', None)]
        self.nav_buttons = {}
        for name, title, permission in nav:
            if permission and not self.service.pode(permission):
                continue
            btn = button(self.sidebar, p, title, lambda key=name: self.show_page(key),
                         kind='sidebar', anchor='w', padx=18, pady=15)
            btn.pack(fill='x', padx=12, pady=3)
            self.nav_buttons[name] = btn
        tk.Frame(self.sidebar, bg=p.sidebar).pack(fill='both', expand=True)
        button(self.sidebar, p, 'Sair da conta', self.logout, kind='sidebar',
               anchor='w').pack(fill='x', padx=12, pady=(8, 25))

    def toggle_nav(self):
        self._nav_visible = not self._nav_visible
        self._apply_sidebar()

    def _apply_sidebar(self):
        if not hasattr(self, 'sidebar'):
            return
        if self._nav_visible:
            self.sidebar.grid()
        else:
            self.sidebar.grid_remove()

    def _responsive(self, event=None):
        if not self._dashboard:
            return
        compact = self.winfo_width() < 985
        if compact != self._is_compact:
            self._is_compact = compact
            self._nav_visible = not compact
            self._apply_sidebar()

    def show_page(self, name):
        if name == 'audit' and not self.service.pode('auditoria'):
            raise PermissionDenied('Você não tem acesso à auditoria.')
        if name == 'users' and not self.service.pode('usuarios'):
            raise PermissionDenied('Você não tem acesso à gestão de usuários.')
        self._current_page = name
        for child in self.content.winfo_children():
            child.destroy()
        for key, btn in self.nav_buttons.items():
            btn.configure(bg=self.p.primary if key == name else self.p.sidebar)
        views = {'records': RecordsView, 'audit': AuditView, 'users': UsersView}
        view = views[name](self.content, self) if name in views else self._settings()
        view.pack(fill='both', expand=True)
        if self._is_compact and self._nav_visible:
            self._nav_visible = False
            self._apply_sidebar()

    def _settings(self):
        p = self.p
        container = tk.Frame(self.content, bg=p.bg)
        text(container, p, 'Aparência e sistema', bg=p.bg, size=21, weight='bold').pack(anchor='w', padx=24, pady=(22, 5))
        text(container, p, 'Personalize a interface sem modificar os registros.', bg=p.bg,
             muted=True).pack(anchor='w', padx=24, pady=(0, 15))
        card = tk.Frame(container, bg=p.card, padx=25, pady=23,
                        highlightbackground=p.border, highlightthickness=1)
        card.pack(fill='x', padx=24)
        text(card, p, 'Tema visual', size=15, weight='bold').pack(anchor='w')
        text(card, p, 'Escolha um tema. A preferência será mantida nas próximas aberturas.',
             muted=True).pack(anchor='w', pady=(3, 14))
        options = tk.Frame(card, bg=p.card)
        options.pack(anchor='w')
        for title in THEMES:
            button(options, p, title + ('  • Ativo' if title == self.theme_name else ''),
                   lambda theme=title: self.change_theme(theme),
                   kind='primary' if title == self.theme_name else 'secondary').pack(side='left', padx=(0, 9))
        second = tk.Frame(container, bg=p.card, padx=25, pady=23,
                          highlightbackground=p.border, highlightthickness=1)
        second.pack(fill='x', padx=24, pady=16)
        text(second, p, 'Segurança da base', size=15, weight='bold').pack(anchor='w')
        text(second, p, 'Cofre AES-256-GCM  •  Gravação atômica  •  Bloqueio de instância',
             muted=True).pack(anchor='w', pady=(6, 4))
        text(second, p, 'Os dados são locais e exigem backup externo. Alterações manuais ou restauração de um cofre antigo não são impedidas por criptografia.',
             muted=True, wraplength=780, justify='left').pack(anchor='w', pady=(0, 6))
        return container

    def logout(self):
        self.service.sair()
        self._dashboard = False
        self.show_auth('login')

    def toast(self, message):
        if hasattr(self, 'footer') and self.footer.winfo_exists():
            self.footer.configure(text='✓  ' + message)

    def execute(self, action, *, controls=()):
        """Bloqueia callbacks reentrantes, inclusive loops de diálogo aninhados."""
        if self._busy:
            return False
        self._busy = True
        original = []
        try:
            for item in controls:
                if item.winfo_exists():
                    original.append((item, item.cget('state')))
                    item.configure(state='disabled')
            action()
            return True
        except (ValidationError, PermissionDenied, StorageError, ValueError) as exc:
            messagebox.showerror('Operação não concluída', str(exc), parent=self)
            return False
        except Exception:
            logging.exception('Erro inesperado durante operação da interface')
            messagebox.showerror('Erro inesperado',
                'Não foi possível concluir a operação. Os dados não foram confirmados. Consulte portaria.log.',
                parent=self)
            return False
        finally:
            for widget, state in original:
                try:
                    if widget.winfo_exists():
                        widget.configure(state=state)
                except tk.TclError:
                    pass
            self._busy = False

    def _callback_error(self, exc, value, trace):
        logging.error('Erro não tratado em callback Tk', exc_info=(exc, value, trace))
        messagebox.showerror('Erro inesperado',
                             'Ocorreu um erro inesperado. Consulte o arquivo portaria.log.', parent=self)

    def run(self):
        self.mainloop()
