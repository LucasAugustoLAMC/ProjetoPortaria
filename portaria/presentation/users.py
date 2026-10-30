"""Ações e eventos de users.py na interface Tkinter."""
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import sys, math, re, random, calendar
from datetime import datetime, date, timedelta
from ..config import *
from ..domain.validation import *
from ..domain.security import conferir_hash, criar_hash, gerar_semelhantes
from ..application.service import PortariaService
from .components import Botao, Sobreposicao, SeletorData, SeletorHora, CampoData, CampoHora
from .user_forms import FormularioUsuario, RecuperarSenha


class UsersMixin:
    def limpar_area_login(self):
        for w in self.area_login.winfo_children():
            w.destroy()

    def cabecalho_login(self, grande=True):
        if grande:
            tk.Label(self.area_login, text='🏠', font=('Segoe UI Emoji', 32), bg=COR_CARTAO).pack()
        tk.Label(self.area_login, text='Cadastro de Portaria', font=('Segoe UI', 18 if grande else 14, 'bold'), bg=COR_CARTAO, fg=COR_TITULO).pack()
        tk.Label(self.area_login, text='Controle de entrada e saída', font=('Segoe UI', 10), bg=COR_CARTAO, fg=COR_TEXTO_SUAVE).pack()

    def montar_login(self):
        self.limpar_area_login()
        if not self.service.usuarios:
            self.montar_setup()
            return
        self.cabecalho_login()
        form = tk.Frame(self.area_login, bg=COR_CARTAO)
        form.pack(pady=(14, 0))
        tk.Label(form, text='Entrar como:', font=('Segoe UI', 10), bg=COR_CARTAO).pack(anchor='w')
        self.var_login_cargo = tk.StringVar(value=CARGO_FINAL)
        ttk.Combobox(form, textvariable=self.var_login_cargo, values=CARGOS, state='readonly', font=('Segoe UI', 11), width=32).pack(fill='x', pady=(2, 10), ipady=2)
        tk.Label(form, text='E-mail ou CPF:', font=('Segoe UI', 10), bg=COR_CARTAO).pack(anchor='w')
        self.entrada_login = tk.Entry(form, font=('Segoe UI', 11), width=34)
        self.entrada_login.pack(fill='x', pady=(2, 10), ipady=3)
        tk.Label(form, text='Senha:', font=('Segoe UI', 10), bg=COR_CARTAO).pack(anchor='w')
        self.entrada_senha = tk.Entry(form, font=('Segoe UI', 11), width=34, show='•')
        self.entrada_senha.pack(fill='x', pady=(2, 4), ipady=3)
        self.var_ver_senha = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text='Mostrar senha', variable=self.var_ver_senha, bg=COR_CARTAO, activebackground=COR_CARTAO, command=lambda: self.entrada_senha.config(show='' if self.var_ver_senha.get() else '•')).pack(anchor='w')
        Botao(form, text='Entrar', bg=COR_VERDE, fg='white', activebackground='#17724A', activeforeground='white', font=('Segoe UI', 11, 'bold'), bd=0, pady=8, cursor='hand2', command=self.entrar).pack(fill='x', pady=(10, 6))
        Botao(form, text='Esqueci minha senha', fg=COR_AZUL, bg=COR_CARTAO, borda='', raio=8, bd=0, font=('Segoe UI', 9, 'underline'), cursor='hand2', command=self.montar_recuperacao).pack()
        self.entrada_login.bind('<Return>', lambda _e: self.entrada_senha.focus_set())
        self.entrada_senha.bind('<Return>', lambda _e: self.entrar())
        self.entrada_login.focus_set()

    def montar_setup(self):
        """Primeiro acesso: cadastro do Admin Final (dono do sistema)."""
        self.limpar_area_login()
        self.cabecalho_login(grande=False)
        tk.Label(self.area_login, text='Primeiro acesso — cadastre o Admin Final para começar.', font=('Segoe UI', 10, 'bold'), bg=COR_CARTAO, fg=COR_AZUL).pack(pady=(6, 0))
        FormularioUsuario(self, self.area_login, 'Cadastro do Admin Final', cargo_fixo=CARGO_FINAL, ao_concluir=self.fim_setup).pack()

    def fim_setup(self, _usuario):
        self._mostrar_codigo_recuperacao()
        self.messagebox.showinfo('Admin Final cadastrado', 'Cadastro concluído! Entre com o cargo Admin Final, usando seu e-mail ou CPF e a senha.')
        self.montar_login()

    def montar_recuperacao(self):
        self.limpar_area_login()
        self.cabecalho_login(grande=False)
        RecuperarSenha(self, self.area_login, self.montar_login).pack(pady=(8, 0))

    def entrar(self):
        cargo = self.var_login_cargo.get()
        login = self.entrada_login.get()
        senha = self.entrada_senha.get()
        if not login.strip() or not senha:
            self.messagebox.showwarning('Atenção', 'Informe o e-mail (ou CPF) e a senha.')
            return
        try:
            self.service.autenticar(login, senha, cargo)
        except ValidationError as exc:
            self.messagebox.showerror('Acesso negado', str(exc))
            return
        self.entrada_senha.delete(0, tk.END)
        self.mostrar_app()

    def sair(self):
        self.service.sair()
        self.mostrar_login()

    def mostrar_login(self):
        self.app.pack_forget()
        self.janela.title('Cadastro de Portaria - Login')
        self.login_frame.pack(fill='both', expand=True)
        self.montar_login()

    def construir_pagina_usuarios(self, pai):
        pagina = tk.Frame(pai, bg=COR_FUNDO)
        tk.Label(pagina, text='Veja os acessos, altere cargos (Adm ↔ Usuário), desbloqueie contas ou remova usuários.', font=('Segoe UI', 10), fg=COR_TITULO, bg=COR_FUNDO).pack(anchor='w', padx=20, pady=(16, 0))
        barra = tk.Frame(pagina, bg=COR_FUNDO)
        barra.pack(fill='x', padx=20, pady=10)
        estilo = dict(font=('Segoe UI', 10, 'bold'), fg='white', bd=0, padx=12, pady=6, cursor='hand2')
        Botao(barra, text='➕  Novo administrador / usuário', bg=COR_VERDE, command=lambda: self.ir_para('novo'), **estilo).pack(side='left')
        Botao(barra, text='⇄  Alterar cargo', bg=COR_AZUL, command=self.alterar_cargo, **estilo).pack(side='left', padx=8)
        Botao(barra, text='🔓  Desbloquear', bg=COR_LARANJA, command=self.desbloquear_usuario, **estilo).pack(side='left')
        Botao(barra, text='✕  Excluir usuário', bg=COR_VERMELHO, command=self.excluir_usuario, **estilo).pack(side='right')
        area = tk.Frame(pagina, bg=COR_FUNDO)
        area.pack(fill='both', expand=True, padx=20, pady=(0, 16))
        colunas = ('Exibicao', 'Completo', 'Cargo', 'Email', 'CPF', 'Status')
        self.tabela_usr = ttk.Treeview(area, columns=colunas, show='headings', selectmode='browse')
        titulos = {'Exibicao': 'Nome de exibição', 'Completo': 'Nome completo', 'Cargo': 'Cargo', 'Email': 'E-mail', 'CPF': 'CPF', 'Status': 'Status'}
        larguras = {'Exibicao': 120, 'Completo': 170, 'Cargo': 80, 'Email': 190, 'CPF': 100, 'Status': 110}
        for c in colunas:
            self.tabela_usr.heading(c, text=titulos[c])
            self.tabela_usr.column(c, width=larguras[c], anchor='w')
        rolagem = ttk.Scrollbar(area, orient='vertical', command=self.tabela_usr.yview)
        self.tabela_usr.configure(yscrollcommand=rolagem.set)
        self.tabela_usr.pack(side='left', fill='both', expand=True)
        rolagem.pack(side='right', fill='y')
        return pagina

    def atualizar_usuarios(self):
        if self.tabela_usr is None:
            return
        for item in self.tabela_usr.get_children():
            self.tabela_usr.delete(item)
        for u in self.service.usuarios:
            restante = self.service.minutos_bloqueio_restantes(u)
            status = 'Bloqueado (%d min)' % restante if restante else 'Ativo'
            self.tabela_usr.insert('', 'end', iid=u['Id'], values=(u['NomeExibicao'], u['NomeCompleto'], u['Cargo'], u['Email'], mascarar_cpf(u['CPF']), status))

    def usuario_selecionado(self):
        sel = self.tabela_usr.selection()
        if not sel:
            self.messagebox.showwarning('Atenção', 'Selecione um usuário na lista.')
            return None
        return self.service.achar_usuario_por_id(sel[0])

    def alterar_cargo(self):
        if not self.exigir('usuarios'):
            return
        u = self.usuario_selecionado()
        if u is None:
            return
        if u['Cargo'] == CARGO_FINAL:
            self.messagebox.showwarning('Atenção', 'O cargo do Admin Final não pode ser alterado.')
            return
        novo = CARGO_USUARIO if u['Cargo'] == CARGO_ADM else CARGO_ADM
        if self.messagebox.askyesno('Alterar cargo', 'Alterar o cargo de %s de %s para %s?' % (u['NomeExibicao'], u['Cargo'], novo)):
            self.service.alterar_cargo(u, novo)
            self.atualizar_usuarios()

    def excluir_usuario(self):
        if not self.exigir('usuarios'):
            return
        u = self.usuario_selecionado()
        if u is None:
            return
        if u['Cargo'] == CARGO_FINAL:
            self.messagebox.showwarning('Atenção', 'O Admin Final não pode ser excluído.')
            return
        if self.messagebox.askyesno('Excluir usuário', 'Excluir o acesso de %s (%s)?' % (u['NomeExibicao'], u['Cargo'])):
            self.service.excluir_usuario(u)
            self.atualizar_usuarios()

    def desbloquear_usuario(self):
        if not self.exigir('usuarios'):
            return
        u = self.usuario_selecionado()
        if u is None:
            return
        self.service.limpar_falhas(u)
        self.atualizar_usuarios()

    def construir_pagina_novo(self, pai):
        pagina = tk.Frame(pai, bg=COR_FUNDO)
        tk.Label(pagina, text='Crie contas de Adm e de Usuário. Cada uma tem senha e 3 palavras-chave de recuperação próprias.', font=('Segoe UI', 10), fg=COR_TITULO, bg=COR_FUNDO).pack(anchor='w', padx=20, pady=(16, 0))
        self.moldura_novo = tk.Frame(pagina, bg=COR_FUNDO)
        self.moldura_novo.pack(pady=10)
        return pagina

    def reiniciar_formulario_novo(self):
        """Mostra o formulário em branco."""
        for w in self.moldura_novo.winfo_children():
            w.destroy()
        FormularioUsuario(self, self.moldura_novo, 'Novo administrador / usuário', ao_concluir=self.apos_cadastro_novo).pack()

    def apos_cadastro_novo(self, u):
        self.messagebox.showinfo('Cadastro concluído', '%s (%s) foi cadastrado com sucesso.' % (u['NomeExibicao'], u['Cargo']))
        self.reiniciar_formulario_novo()
