"""Ações e eventos de window_chrome.py na interface Tkinter."""
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


class WindowChromeMixin:
    def area_de_trabalho(self):
        """Área útil da tela (sem a barra de tarefas, no Windows)."""
        if EH_WINDOWS:
            try:
                import ctypes
                from ctypes import wintypes
                retangulo = wintypes.RECT()
                ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(retangulo), 0)
                return (retangulo.left, retangulo.top, retangulo.right, retangulo.bottom)
            except Exception:
                pass
        return (0, 0, self.janela.winfo_screenwidth(), self.janela.winfo_screenheight())

    def garantir_icone_na_barra_de_tarefas(self):
        """No Windows, janelas sem moldura somem da barra de tarefas; isto traz o ícone de volta."""
        if not EH_WINDOWS:
            return
        try:
            import ctypes
            GWL_EXSTYLE, WS_EX_APPWINDOW, WS_EX_TOOLWINDOW = (-20, 262144, 128)
            hwnd = ctypes.windll.user32.GetParent(self.janela.winfo_id())
            estilo = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            estilo = estilo & ~WS_EX_TOOLWINDOW | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, estilo)
            self.janela.withdraw()
            self.janela.after(10, self.janela.deiconify)
        except Exception:
            pass

    def minimizar(self):
        self.estado_janela['minimizado'] = True
        self.janela.overrideredirect(False)
        self.janela.update_idletasks()
        self.janela.iconify()

    def restaurar_moldura(self):
        self.janela.overrideredirect(True)
        self.garantir_icone_na_barra_de_tarefas()
        self.janela.after(150, self.janela.focus_force)

    def ao_mapear(self, evento):
        if evento.widget is self.janela and self.estado_janela['minimizado']:
            self.estado_janela['minimizado'] = False
            self.janela.after(10, self.restaurar_moldura)

    def alternar_maximizar(self):
        if self.estado_janela['maximizada']:
            self.janela.geometry(self.estado_janela['geometria'])
            self.estado_janela['maximizada'] = False
            self.btn_maximizar.config(text='▢')
            self.grip.place(relx=1.0, rely=1.0, anchor='se')
        else:
            self.estado_janela['geometria'] = self.janela.geometry()
            x1, y1, x2, y2 = self.area_de_trabalho()
            self.janela.geometry('%dx%d+%d+%d' % (x2 - x1, y2 - y1, x1, y1))
            self.estado_janela['maximizada'] = True
            self.btn_maximizar.config(text='❐')
            self.grip.place_forget()

    def iniciar_arraste(self, evento):
        self.estado_janela['arraste'] = (evento.x_root - self.janela.winfo_x(), evento.y_root - self.janela.winfo_y())

    def arrastar(self, evento):
        if self.estado_janela['maximizada']:
            return
        dx, dy = self.estado_janela['arraste']
        self.janela.geometry('+%d+%d' % (evento.x_root - dx, max(0, evento.y_root - dy)))

    def redimensionar(self, evento):
        largura = max(LARGURA_MINIMA, evento.x_root - self.janela.winfo_x())
        altura = max(ALTURA_MINIMA, evento.y_root - self.janela.winfo_y())
        self.janela.geometry('%dx%d' % (largura, altura))

    def construir_barra_titulo(self):
        barra = tk.Frame(self.janela, bg=COR_MENU, height=40)
        barra.pack(side='top', fill='x')
        barra.pack_propagate(False)
        titulo = tk.Label(barra, text='🏠  Cadastro de Portaria', font=('Segoe UI', 10, 'bold'), bg=COR_MENU, fg=COR_CREME)
        titulo.pack(side='left', padx=14)
        estilo = dict(width=3, font=('Segoe UI', 10, 'bold'), fg='white', bg=COR_MENU_BTN, borda=COR_MENU_BORDA, hover=COR_MENU_HOVER, raio=8, padx=6, pady=2)
        Botao(barra, text='✕', command=self.janela.destroy, **{**estilo, 'bg': '#9C4A3A', 'hover': '#B5604D'}).pack(side='right', padx=(2, 10), pady=6)
        self.btn_maximizar = Botao(barra, text='▢', command=self.alternar_maximizar, **estilo)
        self.btn_maximizar.pack(side='right', padx=2, pady=6)
        Botao(barra, text='—', command=self.minimizar, **estilo).pack(side='right', padx=2, pady=6)
        for peca in (barra, titulo):
            peca.bind('<ButtonPress-1>', self.iniciar_arraste)
            peca.bind('<B1-Motion>', self.arrastar)
            peca.bind('<Double-Button-1>', lambda _e: self.alternar_maximizar())
        self.grip = tk.Label(self.janela, text='◢', font=('Segoe UI', 11), bg=COR_FUNDO, fg=COR_BORDA, cursor='size_nw_se' if EH_WINDOWS else 'bottom_right_corner')
        self.grip.place(relx=1.0, rely=1.0, anchor='se')
        self.grip.bind('<B1-Motion>', self.redimensionar)

    def colorir_barra_nativa(self):
        """Alternativa (BARRA_TITULO_PERSONALIZADA = False): pinta a barra nativa do Windows 11."""
        if not EH_WINDOWS:
            return
        try:
            import ctypes

            def colorref(cor):
                r, g, b = [v // 257 for v in self.janela.winfo_rgb(cor)]
                return r | g << 8 | b << 16
            hwnd = ctypes.windll.user32.GetParent(self.janela.winfo_id())
            for atributo, cor in ((35, COR_MENU), (36, COR_CREME), (34, COR_MENU)):
                valor = ctypes.c_int(colorref(cor))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(valor), ctypes.sizeof(valor))
        except Exception:
            pass

    def configurar_moldura_da_janela(self):
        x = max(0, (self.janela.winfo_screenwidth() - LARGURA_PADRAO) // 2)
        y = max(0, (self.janela.winfo_screenheight() - ALTURA_PADRAO) // 3)
        self.janela.geometry('%dx%d+%d+%d' % (LARGURA_PADRAO, ALTURA_PADRAO, x, y))
        self.janela.minsize(LARGURA_MINIMA, ALTURA_MINIMA)
        if BARRA_TITULO_PERSONALIZADA:
            self.janela.overrideredirect(True)
            self.janela.configure(highlightthickness=1, highlightbackground=COR_MENU, highlightcolor=COR_MENU)
            self.construir_barra_titulo()
            self.janela.bind('<Map>', self.ao_mapear)
            self.janela.after(150, self.garantir_icone_na_barra_de_tarefas)
            self.janela.after(400, self.janela.focus_force)
        else:
            self.janela.after(200, self.colorir_barra_nativa)
