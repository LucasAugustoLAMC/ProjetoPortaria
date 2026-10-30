"""Ações e eventos de audit.py na interface Tkinter."""
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


class AuditMixin:
    def construir_pagina_auditoria(self, pai):
        pagina = tk.Frame(pai, bg=COR_FUNDO)
        tk.Label(pagina, text='Edições mostram o valor anterior. Exclusões guardam o registro completo.', font=('Segoe UI', 10), fg=COR_TITULO, bg=COR_FUNDO).pack(anchor='w', padx=20, pady=(16, 0))
        barra = tk.Frame(pagina, bg=COR_FUNDO)
        barra.pack(fill='x', padx=20, pady=10)
        tk.Label(barra, text='Mostrar:', font=('Segoe UI', 10), bg=COR_FUNDO).pack(side='left')
        self.var_filtro_aud = tk.StringVar(value='Todos')
        filtro = ttk.Combobox(barra, textvariable=self.var_filtro_aud, state='readonly', width=12, values=['Todos', 'Edições', 'Exclusões'])
        filtro.pack(side='left', padx=8)
        filtro.bind('<<ComboboxSelected>>', lambda _e: self.atualizar_auditoria())
        self.lbl_cont_aud = tk.Label(barra, font=('Segoe UI', 9), fg=COR_TEXTO_SUAVE, bg=COR_FUNDO)
        self.lbl_cont_aud.pack(side='right')
        area = tk.Frame(pagina, bg=COR_FUNDO)
        area.pack(fill='both', expand=True, padx=20)
        self.tabela_aud = ttk.Treeview(area, show='headings', selectmode='browse', columns=('Quando', 'Acao', 'Usuario', 'Nome', 'Campo', 'Anterior', 'Novo'))
        larguras = {'Quando': 130, 'Acao': 85, 'Usuario': 100, 'Nome': 105, 'Campo': 105, 'Anterior': 170, 'Novo': 100}
        titulos = {'Quando': 'Data/hora', 'Acao': 'Ação', 'Usuario': 'Responsável', 'Nome': 'Pessoa', 'Campo': 'Campo', 'Anterior': 'Valor anterior', 'Novo': 'Novo valor'}
        for col in titulos:
            self.tabela_aud.heading(col, text=titulos[col])
            self.tabela_aud.column(col, width=larguras[col], anchor='w')
        self.tabela_aud.tag_configure('edicao', background=COR_PENDENTE)
        self.tabela_aud.tag_configure('exclusao', background='#F2DCD3')
        rolagem = ttk.Scrollbar(area, orient='vertical', command=self.tabela_aud.yview)
        self.tabela_aud.configure(yscrollcommand=rolagem.set)
        self.tabela_aud.pack(side='left', fill='both', expand=True)
        rolagem.pack(side='right', fill='y')
        self.lbl_detalhe_aud = tk.Label(pagina, text='Selecione uma linha para ver os detalhes.', font=('Segoe UI', 10), bg=COR_CARTAO, fg=COR_TITULO, anchor='w', justify='left', wraplength=820, padx=10, pady=8, highlightbackground=COR_BORDA, highlightthickness=1)
        self.lbl_detalhe_aud.pack(fill='x', padx=20, pady=12)

        def mostrar_detalhe(_e=None):
            sel = self.tabela_aud.selection()
            if not sel:
                return
            v = self.tabela_aud.item(sel[0], 'values')
            self.lbl_detalhe_aud.config(text='%s em %s — %s (responsável: %s)\nCampo: %s\nValor anterior: %s\nNovo valor: %s' % (v[1], v[0], v[3], v[2] or '—', v[4], v[5], v[6]))
        self.tabela_aud.bind('<<TreeviewSelect>>', mostrar_detalhe)
        return pagina

    def atualizar_auditoria(self):
        if self.tabela_aud is None:
            return
        filtro = self.var_filtro_aud.get()
        for item in self.tabela_aud.get_children():
            self.tabela_aud.delete(item)
        mostrados = 0
        for ev in reversed(self.service.auditoria):
            if filtro == 'Edições' and ev['Acao'] != 'EDIÇÃO':
                continue
            if filtro == 'Exclusões' and ev['Acao'] != 'EXCLUSÃO':
                continue
            tag = 'exclusao' if ev['Acao'] == 'EXCLUSÃO' else 'edicao'
            self.tabela_aud.insert('', 'end', tags=(tag,), values=(ev['Quando'], ev['Acao'], ev['Usuario'], ev['Nome'], ev['Campo'], ev['Anterior'], ev['Novo']))
            mostrados += 1
        self.lbl_cont_aud.config(text='%d evento(s)' % mostrados)
