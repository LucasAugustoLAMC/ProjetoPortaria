"""Fluxos de abertura do cofre, primeiro acesso, login e recuperação protegida."""
import random
import tkinter as tk
from tkinter import messagebox
from .theme import FONT, text, entry, button
from .users import UserForm
from .scrollable import ScrollableCard
from ..domain.validation import so_digitos


class AuthView(tk.Frame):
    def __init__(self, parent, app, mode='login'):
        super().__init__(parent, bg=app.p.bg)
        self.app, self.p = app, app.p
        self.mode = mode
        self.recovery_user = None
        self.recovery_options = []
        self.recovery_vars = []
        self.token = None
        self.scroller = ScrollableCard(self, self.p)
        self.scroller.pack(fill='both', expand=True)
        self.inner = self.scroller.content
        self.inner.bind('<Configure>', self._reflow_text, add='+')
        self.show(mode)

    def _reflow_text(self, event):
        if hasattr(self, 'subtitle') and self.subtitle.winfo_exists():
            self.subtitle.configure(wraplength=max(160, event.width - 74))

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()
        self.scroller._bound.clear()

    def title(self, title, subtitle):
        text(self.inner, self.p, 'PORTARIA  /  ACESSO SEGURO', size=9, weight='bold',
             muted=True).pack(anchor='w', pady=(0, 9))
        text(self.inner, self.p, title, size=23, weight='bold').pack(anchor='w')
        self.subtitle = text(self.inner, self.p, subtitle, muted=True, wraplength=420,
                             justify='left')
        self.subtitle.pack(anchor='w', pady=(6, 20))

    def labeled(self, title, show=None):
        text(self.inner, self.p, title, muted=True).pack(anchor='w', pady=(6, 4))
        widget = entry(self.inner, self.p, show=show)
        widget.pack(fill='x', ipady=10, pady=(0, 10))
        return widget

    def show(self, mode):
        self.mode = mode
        self.clear()
        if mode == 'unlock':
            self.title('Desbloquear base local', 'O cofre está criptografado. Informe a senha do Admin Final para abrir os dados.')
            self.secret = self.labeled('Senha do Admin Final', show='•')
            self.secret.bind('<Return>', lambda _e: self.unlock())
            button(self.inner, self.p, 'Desbloquear cofre', self.unlock).pack(fill='x', pady=(8, 12))
            button(self.inner, self.p, 'Usar código de recuperação',
                   lambda: self.show('unlock_recovery'), kind='link').pack()
            self.secret.focus_set()
        elif mode == 'unlock_recovery':
            self.title('Código de emergência', 'Use o código recebido na ativação. Ele não é enviado por e-mail nem recuperável pelo aplicativo.')
            self.secret = self.labeled('Código de recuperação', show='•')
            button(self.inner, self.p, 'Desbloquear com código',
                   lambda: self.unlock(recovery=True)).pack(fill='x', pady=12)
            button(self.inner, self.p, 'Voltar à senha',
                   lambda: self.show('unlock'), kind='link').pack()
        elif mode == 'migrate':
            self.title('Proteger base existente', 'Uma instalação anterior foi identificada. Faça backup dos CSV/JSON antes de ativar a criptografia.')
            self.secret = self.labeled('Senha atual do Admin Final', show='•')
            button(self.inner, self.p, 'Migrar e criptografar', self.migrate).pack(fill='x', pady=(10, 8))
            text(self.inner, self.p, 'Após a migração os dados serão mantidos em dados_portaria.enc.',
                 muted=True, wraplength=510).pack(anchor='w')
        elif mode == 'setup':
            self.title('Primeira configuração', 'Crie o Admin Final. Role até o final para concluir e guarde o código de recuperação em local seguro.')
            form = UserForm(self.inner, self.app, self.created_admin, initial_admin=True)
            form.pack(fill='x')
        elif mode == 'login':
            self.title('Bem-vindo de volta', 'Entre com CPF ou e-mail e sua senha individual.')
            self.login = self.labeled('E-mail ou CPF')
            self.password = self.labeled('Senha', show='•')
            self.reveal = tk.BooleanVar(value=False)
            tk.Checkbutton(self.inner, text='Mostrar senha', variable=self.reveal,
                           bg=self.p.card, fg=self.p.text, selectcolor=self.p.card,
                           activebackground=self.p.card, command=lambda: self.password.configure(
                               show='' if self.reveal.get() else '•')).pack(anchor='w')
            self.password.bind('<Return>', lambda _e: self.sign_in())
            button(self.inner, self.p, 'Entrar', self.sign_in).pack(fill='x', pady=(12, 8))
            button(self.inner, self.p, 'Esqueci minha senha',
                   lambda: self.show('recover_identity'), kind='link').pack()
            self.login.focus_set()
        elif mode == 'recover_identity':
            self.title('Recuperar conta', 'Confirme CPF e e-mail. As tentativas são registradas e limitadas.')
            self.cpf = self.labeled('CPF')
            self.email = self.labeled('E-mail')
            button(self.inner, self.p, 'Continuar', self.recover_identity).pack(fill='x', pady=10)
            button(self.inner, self.p, 'Voltar ao login',
                   lambda: self.show('login'), kind='link').pack()
        elif mode == 'recover_questions':
            self.title('Confirme suas palavras', 'Selecione as três palavras cadastradas. Respostas incorretas podem bloquear a conta.')
            self.recovery_options = []
            self.recovery_vars = []
            for i, item in enumerate(self.recovery_user['Palavras']):
                choices = list(item['Opcoes'])
                random.shuffle(choices)
                self.recovery_options.append(choices)
                var = tk.IntVar(value=-1)
                self.recovery_vars.append(var)
                text(self.inner, self.p, f'Palavra-chave {i+1}', muted=True).pack(anchor='w', pady=(8, 0))
                group = tk.Frame(self.inner, bg=self.p.card)
                group.pack(fill='x')
                for j, option in enumerate(choices):
                    tk.Radiobutton(group, text=f'{"ABCD"[j]}) {option}', variable=var, value=j,
                                   bg=self.p.card, fg=self.p.text, selectcolor=self.p.card,
                                   activebackground=self.p.card, activeforeground=self.p.text,
                                   font=(FONT, 10)).grid(row=j//2, column=j%2, sticky='w', padx=(0, 20))
            button(self.inner, self.p, 'Verificar respostas', self.recover_questions).pack(fill='x', pady=15)
            button(self.inner, self.p, 'Cancelar recuperação',
                   lambda: self.show('login'), kind='link').pack()
        elif mode == 'recover_password':
            self.title('Definir nova senha', 'A autorização expira em cinco minutos e só pode ser utilizada uma vez.')
            self.newpass = self.labeled('Nova senha', show='•')
            self.newconf = self.labeled('Confirmação', show='•')
            button(self.inner, self.p, 'Salvar nova senha', self.recover_save).pack(fill='x', pady=10)

        self.scroller.bind_descendants()

    def unlock(self, recovery=False):
        def work():
            self.app.service.desbloquear_cofre(self.secret.get(), recuperacao=recovery)
            self.app.service.carregar()
            self.app.show_auth('login' if self.app.service.usuarios else 'setup')
        self.app.execute(work)

    def migrate(self):
        def work():
            self.app.service.ativar_criptografia(self.secret.get())
            self.app.show_recovery_code()
            self.app.show_auth('login')
        self.app.execute(work)

    def created_admin(self, _user):
        self.app.show_recovery_code()
        self.app.show_auth('login')

    def sign_in(self):
        def work():
            self.app.service.autenticar(self.login.get(), self.password.get())
            self.password.delete(0, 'end')
            self.app.show_dashboard('records')
        self.app.execute(work)

    def recover_identity(self):
        u = self.app.service.achar_usuario_por_cpf(so_digitos(self.cpf.get()))
        cpf, email = so_digitos(self.cpf.get()), self.email.get().strip().lower()
        if not u or u['Email'].lower() != email:
            if u:
                self.app.execute(lambda: self.app.service.registrar_falha(u))
            messagebox.showerror('Dados não conferem', 'CPF ou e-mail inválido.', parent=self)
            return
        if self.app.service.minutos_bloqueio_restantes(u):
            messagebox.showerror('Conta bloqueada', 'Aguarde o término do bloqueio.', parent=self)
            return
        self.recovery_user = u
        self.show('recover_questions')

    def recover_questions(self):
        if any(var.get() < 0 for var in self.recovery_vars):
            messagebox.showwarning('Respostas incompletas', 'Responda as três perguntas.', parent=self)
            return
        answers = [options[var.get()] for options, var in zip(self.recovery_options, self.recovery_vars)]
        def work():
            self.token = self.app.service.solicitar_recuperacao(self.recovery_user['CPF'],
                                                                 self.recovery_user['Email'], answers)
            self.show('recover_password')
        self.app.execute(work)

    def recover_save(self):
        if self.newpass.get() != self.newconf.get():
            messagebox.showwarning('Confirmação', 'As senhas devem ser iguais.', parent=self)
            return
        def work():
            self.app.service.redefinir_senha(self.recovery_user, self.newpass.get(),
                                              recovery_token=self.token)
            messagebox.showinfo('Senha redefinida', 'Sua senha foi atualizada. Entre novamente.', parent=self)
            self.token = None
            self.show('login')
        self.app.execute(work)
