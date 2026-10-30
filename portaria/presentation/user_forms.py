import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from datetime import datetime, date
import math, calendar
from ..config import *
import re, random
from ..domain.validation import normalizar, cpf_valido, formatar_cpf, so_digitos, email_valido, erro_senha, novo_id
from ..domain.security import conferir_hash, criar_hash
from ..config import ITERACOES_PALAVRA, ITERACOES_SENHA, CARGOS, CARGO_ADM, CARGO_USUARIO, CARGO_FINAL
from .components import Botao


class FormularioUsuario(tk.Frame):
    """Formulário de cadastro. Chama ao_concluir(usuario) depois de salvar."""

    def __init__(self, app, pai, titulo, cargo_fixo=None, ao_concluir=None, ao_cancelar=None, texto_cancelar='Cancelar'):
        self.app = app
        super().__init__(pai, bg=COR_CARTAO, padx=24, pady=12)
        self.cargo_fixo = cargo_fixo
        self.ao_concluir = ao_concluir
        self.columnconfigure((0, 1), weight=1, uniform='c')
        tk.Label(self, text=titulo, font=('Segoe UI', 14, 'bold'), bg=COR_CARTAO, fg=COR_TITULO).grid(row=0, column=0, columnspan=2, sticky='w')
        tk.Label(self, text='Todos os campos são obrigatórios.', font=('Segoe UI', 9), bg=COR_CARTAO, fg=COR_TEXTO_SUAVE).grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 6))
        _l, self.e_nome = self.campo('Nome completo:', 2, 0, 2)
        _l, self.e_exibicao = self.campo('Nome para exibição:', 4, 0)
        _l, self.e_email = self.campo('E-mail:', 4, 1)
        self.l_cpf, self.e_cpf = self.campo('CPF:', 6, 0)
        self.e_cpf.bind('<KeyRelease>', self.ao_digitar_cpf)
        if cargo_fixo:
            tk.Label(self, text='Cargo: ' + cargo_fixo, font=('Segoe UI', 10, 'bold'), bg=COR_CARTAO, fg=COR_TITULO).grid(row=7, column=1, sticky='w', padx=6)
        else:
            tk.Label(self, text='Cargo:', font=('Segoe UI', 10), bg=COR_CARTAO).grid(row=6, column=1, sticky='w', padx=6)
            self.var_cargo = tk.StringVar(value=CARGO_ADM)
            ttk.Combobox(self, textvariable=self.var_cargo, values=[CARGO_ADM, CARGO_USUARIO], state='readonly', font=('Segoe UI', 11)).grid(row=7, column=1, sticky='ew', padx=6, pady=(2, 6))
        _l, self.e_senha = self.campo('Senha:', 8, 0, show='•')
        _l, self.e_conf = self.campo('Confirmação da senha:', 8, 1, show='•')
        self.var_mostrar = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text='Mostrar senhas', variable=self.var_mostrar, bg=COR_CARTAO, activebackground=COR_CARTAO, command=self.alternar_senha).grid(row=10, column=0, columnspan=2, sticky='w', padx=2)
        tk.Label(self, text='Palavras-chave de recuperação (3)', font=('Segoe UI', 10, 'bold'), bg=COR_CARTAO, fg=COR_TITULO).grid(row=11, column=0, columnspan=2, sticky='w', pady=(8, 0))
        tk.Label(self, text='Escolha 3 palavras diferentes (só letras, mín. 4). Se esquecer a senha, você terá de reconhecê-las entre alternativas parecidas.', font=('Segoe UI', 9), bg=COR_CARTAO, fg=COR_TEXTO_SUAVE, wraplength=520, justify='left').grid(row=12, column=0, columnspan=2, sticky='w')
        linha_palavras = tk.Frame(self, bg=COR_CARTAO)
        linha_palavras.grid(row=13, column=0, columnspan=2, sticky='ew')
        linha_palavras.columnconfigure((0, 1, 2), weight=1, uniform='p')
        self.e_palavras = []
        for i in range(3):
            tk.Label(linha_palavras, text='Palavra-chave %d:' % (i + 1), font=('Segoe UI', 10), bg=COR_CARTAO).grid(row=0, column=i, sticky='w', padx=6)
            e = tk.Entry(linha_palavras, font=('Segoe UI', 11))
            e.grid(row=1, column=i, sticky='ew', padx=6, pady=(2, 6), ipady=3)
            self.e_palavras.append(e)
        botoes = tk.Frame(self, bg=COR_CARTAO)
        botoes.grid(row=14, column=0, columnspan=2, sticky='e', pady=(10, 0))
        if ao_cancelar:
            Botao(botoes, text=texto_cancelar, bg=COR_NEUTRO, bd=0, padx=14, pady=6, cursor='hand2', command=ao_cancelar).pack(side='left', padx=6)
        Botao(botoes, text='Salvar cadastro', bg=COR_VERDE, fg='white', bd=0, padx=14, pady=6, font=('Segoe UI', 10, 'bold'), cursor='hand2', command=self.salvar).pack(side='left')

    def campo(self, rotulo, linha, coluna, colspan=1, show=None):
        etiqueta = tk.Label(self, text=rotulo, font=('Segoe UI', 10), bg=COR_CARTAO)
        etiqueta.grid(row=linha, column=coluna, columnspan=colspan, sticky='w', padx=6)
        entrada = tk.Entry(self, font=('Segoe UI', 11), show=show) if show else tk.Entry(self, font=('Segoe UI', 11))
        entrada.grid(row=linha + 1, column=coluna, columnspan=colspan, sticky='ew', padx=6, pady=(2, 6), ipady=3)
        return (etiqueta, entrada)

    def alternar_senha(self):
        simbolo = '' if self.var_mostrar.get() else '•'
        self.e_senha.config(show=simbolo)
        self.e_conf.config(show=simbolo)

    def ao_digitar_cpf(self, _evento=None):
        atual = self.e_cpf.get()
        formatado = formatar_cpf(atual)
        if formatado != atual:
            self.e_cpf.delete(0, tk.END)
            self.e_cpf.insert(0, formatado)
        if len(so_digitos(formatado)) == 11:
            ok = cpf_valido(formatado)
            self.l_cpf.config(text='CPF:  ✔ válido' if ok else 'CPF:  ✖ inválido', fg=COR_VERDE if ok else COR_VERMELHO)
        else:
            self.l_cpf.config(text='CPF:', fg=COR_TITULO)

    def avisar(self, mensagem):
        self.app.messagebox.showwarning('Atenção', mensagem)

    def salvar(self):
        nome = ' '.join(self.e_nome.get().split())
        exibicao = ' '.join(self.e_exibicao.get().split())
        email = self.e_email.get().strip().lower()
        cpf = so_digitos(self.e_cpf.get())
        senha, confirmacao = (self.e_senha.get(), self.e_conf.get())
        palavras = [e.get().strip().lower() for e in self.e_palavras]
        cargo = self.cargo_fixo or self.var_cargo.get()
        if len(nome.split()) < 2:
            return self.avisar('Informe o nome completo (nome e sobrenome).')
        if exibicao == '' or len(exibicao) > 25:
            return self.avisar('Informe o nome para exibição (até 25 caracteres).')
        if not email_valido(email):
            return self.avisar('E-mail inválido.')
        if any((u['Email'].lower() == email for u in self.app.service.usuarios)):
            return self.avisar('Este e-mail já está cadastrado.')
        if not cpf_valido(cpf):
            return self.avisar('CPF inválido. Confira os números digitados.')
        if any((u['CPF'] == cpf for u in self.app.service.usuarios)):
            return self.avisar('Este CPF já está cadastrado.')
        if cargo not in CARGOS:
            return self.avisar('Cargo inválido.')
        erro = erro_senha(senha)
        if erro:
            return self.avisar(erro)
        if senha != confirmacao:
            return self.avisar('A confirmação da senha não confere.')
        for p in palavras:
            if re.match('^[a-zà-ÿ]{4,20}$', p) is None:
                return self.avisar('Cada palavra-chave deve ter só letras (de 4 a 20), sem espaços.')
        if len({normalizar(p) for p in palavras}) < 3:
            return self.avisar('As 3 palavras-chave precisam ser diferentes entre si.')
        novo = self.app.service.cadastrar_usuario(nome, exibicao, email, cpf, cargo, senha, palavras)
        if self.ao_concluir:
            self.ao_concluir(novo)


class RecuperarSenha(tk.Frame):

    def __init__(self, app, pai, ao_voltar):
        self.app = app
        super().__init__(pai, bg=COR_CARTAO, padx=10, pady=6)
        self.ao_voltar = ao_voltar
        self.usuario = None
        self.corpo = tk.Frame(self, bg=COR_CARTAO)
        self.corpo.pack()
        self.passo_dados()

    def limpar_corpo(self):
        for w in self.corpo.winfo_children():
            w.destroy()

    def titulo(self, texto, subtitulo):
        tk.Label(self.corpo, text=texto, font=('Segoe UI', 14, 'bold'), bg=COR_CARTAO, fg=COR_TITULO).pack(anchor='w')
        tk.Label(self.corpo, text=subtitulo, font=('Segoe UI', 9), bg=COR_CARTAO, fg=COR_TEXTO_SUAVE, wraplength=400, justify='left').pack(anchor='w', pady=(0, 10))

    def botoes(self, texto_ok, comando):
        barra = tk.Frame(self.corpo, bg=COR_CARTAO)
        barra.pack(anchor='e', pady=(12, 0))
        Botao(barra, text='← Voltar ao login', bg=COR_NEUTRO, bd=0, padx=14, pady=6, cursor='hand2', command=self.ao_voltar).pack(side='left', padx=6)
        Botao(barra, text=texto_ok, bg=COR_AZUL, fg='white', bd=0, padx=14, pady=6, font=('Segoe UI', 10, 'bold'), cursor='hand2', command=comando).pack(side='left')

    def avisar(self, mensagem):
        self.app.messagebox.showwarning('Atenção', mensagem)

    def passo_dados(self):
        self.limpar_corpo()
        self.titulo('Recuperar senha', 'Passo 1 de 3 — confirme seus dados. Digite o CPF e o e-mail cadastrados.')
        tk.Label(self.corpo, text='CPF:', bg=COR_CARTAO, font=('Segoe UI', 10)).pack(anchor='w')
        self.e_cpf = tk.Entry(self.corpo, font=('Segoe UI', 11), width=34)
        self.e_cpf.pack(pady=(2, 8), ipady=3)
        self.e_cpf.bind('<KeyRelease>', self.formatar)
        tk.Label(self.corpo, text='E-mail:', bg=COR_CARTAO, font=('Segoe UI', 10)).pack(anchor='w')
        self.e_email = tk.Entry(self.corpo, font=('Segoe UI', 11), width=34)
        self.e_email.pack(pady=(2, 0), ipady=3)
        self.botoes('Continuar', self.verificar_dados)
        self.e_cpf.focus_set()

    def formatar(self, _e=None):
        atual = self.e_cpf.get()
        novo = formatar_cpf(atual)
        if novo != atual:
            self.e_cpf.delete(0, tk.END)
            self.e_cpf.insert(0, novo)

    def verificar_dados(self):
        cpf = so_digitos(self.e_cpf.get())
        email = self.e_email.get().strip().lower()
        u = self.app.service.achar_usuario_por_cpf(cpf)
        if u is not None and self.app.service.minutos_bloqueio_restantes(u):
            return self.app.avisar_bloqueio(u, self)
        if u is None or u['Email'].lower() != email:
            if u is not None:
                self.app.service.registrar_falha(u)
            return self.avisar('Os dados informados não conferem.')
        self.usuario = u
        self.passo_palavras()

    def passo_palavras(self):
        self.limpar_corpo()
        self.titulo('Palavras-chave', 'Passo 2 de 3 — para cada pergunta, selecione a palavra que você cadastrou.')
        self.variaveis, self.ordem = ([], [])
        for i, p in enumerate(self.usuario['Palavras']):
            opcoes = list(p['Opcoes'])
            random.shuffle(opcoes)
            self.ordem.append(opcoes)
            moldura = tk.LabelFrame(self.corpo, text='Pergunta %d: qual é a sua palavra-chave nº %d?' % (i + 1, i + 1), bg=COR_CARTAO, padx=10, pady=6, font=('Segoe UI', 9, 'bold'))
            moldura.pack(fill='x', pady=4)
            var = tk.IntVar(value=-1)
            self.variaveis.append(var)
            for j, op in enumerate(opcoes):
                tk.Radiobutton(moldura, text='%s) %s' % ('ABCD'[j], op), variable=var, value=j, bg=COR_CARTAO, activebackground=COR_CARTAO, anchor='w', width=20, font=('Segoe UI', 10)).grid(row=j // 2, column=j % 2, sticky='w', padx=6)
        self.botoes('Verificar', self.verificar_palavras)

    def verificar_palavras(self):
        if self.app.service.minutos_bloqueio_restantes(self.usuario):
            return self.app.avisar_bloqueio(self.usuario)
        if any((v.get() < 0 for v in self.variaveis)):
            return self.avisar('Responda as 3 perguntas.')
        certas = [conferir_hash(normalizar(self.ordem[i][v.get()]), p['Salt'], p['Hash'], ITERACOES_PALAVRA) for i, (v, p) in enumerate(zip(self.variaveis, self.usuario['Palavras']))]
        if not all(certas):
            self.app.service.registrar_falha(self.usuario)
            self.app.messagebox.showerror('Recuperação negada', 'As palavras-chave não conferem.\nPor segurança, a recuperação foi encerrada.')
            self.ao_voltar()
            return
        self.passo_nova_senha()

    def passo_nova_senha(self):
        self.limpar_corpo()
        self.titulo('Nova senha', 'Passo 3 de 3 — defina a nova senha (mín. 8 caracteres, com letras e números).')
        tk.Label(self.corpo, text='Nova senha:', bg=COR_CARTAO, font=('Segoe UI', 10)).pack(anchor='w')
        self.e_nova = tk.Entry(self.corpo, font=('Segoe UI', 11), width=34, show='•')
        self.e_nova.pack(pady=(2, 8), ipady=3)
        tk.Label(self.corpo, text='Confirmação da nova senha:', bg=COR_CARTAO, font=('Segoe UI', 10)).pack(anchor='w')
        self.e_conf = tk.Entry(self.corpo, font=('Segoe UI', 11), width=34, show='•')
        self.e_conf.pack(pady=(2, 0), ipady=3)
        self.botoes('Salvar nova senha', self.salvar_nova)
        self.e_nova.focus_set()

    def salvar_nova(self):
        if self.app.service.minutos_bloqueio_restantes(self.usuario):
            return self.app.avisar_bloqueio(self.usuario)
        nova, conf = (self.e_nova.get(), self.e_conf.get())
        erro = erro_senha(nova)
        if erro:
            return self.avisar(erro)
        if nova != conf:
            return self.avisar('A confirmação da senha não confere.')
        self.app.service.redefinir_senha(self.usuario, nova)
        self.app.messagebox.showinfo('Senha redefinida', 'Senha alterada com sucesso! Faça login com a nova senha.')
        self.ao_voltar()
