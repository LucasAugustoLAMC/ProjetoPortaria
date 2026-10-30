"""Ações e eventos de navigation.py na interface Tkinter."""
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


class NavigationMixin:
    def montar_menu(self):
        """Cria os itens do painel lateral que o cargo do usuário logado pode acessar."""
        for w in self.menu_itens.winfo_children():
            w.destroy()
        self.estado_menu['botoes'] = {}
        for chave, rotulo, _titulo, acao in PAGINAS:
            if acao and (not self.service.pode(acao)):
                continue
            b = Botao(self.menu_itens, text=rotulo, anchor='w', justify='left', wraplength=190, font=('Segoe UI', 10, 'bold'), fg='white', bg=COR_MENU_BTN, hover=COR_MENU_HOVER, borda=COR_MENU_BORDA, raio=12, padx=14, pady=10, cursor='hand2', command=lambda k=chave: self.ir_para(k))
            b.pack(fill='x', padx=8, pady=2)
            self.estado_menu['botoes'][chave] = b

    def realcar_menu(self):
        for chave, botao in self.estado_menu['botoes'].items():
            ativo = chave == self.estado_menu['pagina']
            botao.config(bg=COR_MENU_ATIVO if ativo else COR_MENU_BTN, fg=COR_TITULO if ativo else 'white', hover=COR_MENU_ATIVO if ativo else COR_MENU_HOVER)

    def alternar_menu(self):
        """Mostra ou oculta o painel lateral (botão ☰)."""
        if self.estado_menu['visivel']:
            self.sidebar.pack_forget()
            self.estado_menu['visivel'] = False
        else:
            self.sidebar.pack(side='left', fill='y', before=self.direita)
            self.estado_menu['visivel'] = True

    def ir_para(self, nome):
        for chave, _rotulo, titulo, acao in PAGINAS:
            if chave == nome:
                if acao and (not self.exigir(acao)):
                    return
                self.lbl_titulo_pagina.config(text=titulo)
                break
        for pagina in self.paginas.values():
            pagina.pack_forget()
        self.paginas[nome].pack(fill='both', expand=True)
        self.estado_menu['pagina'] = nome
        self.realcar_menu()
        if nome == 'auditoria':
            self.atualizar_auditoria()
        elif nome == 'usuarios':
            self.atualizar_usuarios()
        elif nome == 'novo':
            self.reiniciar_formulario_novo()
        elif nome == 'portaria':
            self.atualizar_tabela()

    def aplicar_permissoes(self):
        """Habilita/desabilita os botões da portaria conforme o cargo do usuário logado."""
        regras = [(self.btn_cadastrar, 'cadastrar', COR_VERDE), (self.btn_saida, 'saida', COR_LARANJA), (self.btn_excluir, 'excluir', COR_VERMELHO)]
        for botao, acao, cor in regras:
            if self.service.pode(acao):
                botao.config(state='normal', bg=cor, cursor='hand2')
            else:
                botao.config(state='disabled', bg='#B8C0CC', cursor='arrow')

    def mostrar_app(self):
        self.login_frame.pack_forget()
        self.janela.title('Cadastro de Portaria')
        self.app.pack(fill='both', expand=True)
        if not self.estado_menu['visivel']:
            self.alternar_menu()
        u = self.service.sessao['usuario']
        self.lbl_usuario.config(text='👤 %s\n%s' % (u['NomeExibicao'], u['Cargo']))
        self.montar_menu()
        self.aplicar_permissoes()
        self.limpar_filtro()
        self.limpar()
        self.ir_para('portaria')
        self.campo_nome.focus()
