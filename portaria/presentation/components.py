import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from datetime import datetime, date
import math, calendar
from ..config import *
from ..domain.input_masks import MASCARA_DATA, MASCARA_HORA, corresponde_mascara

def ajustar_cor(widget, cor, fator):
    """fator > 0 clareia (mistura com branco); fator < 0 escurece (mistura com preto)."""
    try:
        r, g, b = [v // 257 for v in widget.winfo_rgb(cor)]
    except tk.TclError:
        return cor
    if fator >= 0:
        r, g, b = [int(c + (255 - c) * fator) for c in (r, g, b)]
    else:
        r, g, b = [int(c * (1 + fator)) for c in (r, g, b)]
    return "#%02x%02x%02x" % (r, g, b)

class Botao(tk.Canvas):
    """Botão desenhado em um Canvas: cantos arredondados, borda destacada, efeito ao passar o mouse.
    Aceita as mesmas opções principais do tk.Button (text, command, bg, fg, font, padx, pady, state...).
    Opções extras: borda (cor da borda; '' = sem borda), hover (cor ao passar o mouse), raio (arredondamento)."""

    def __init__(self, master, text="", command=None, bg="#5F7350", fg=None, font=("Segoe UI", 10),
                 padx=None, pady=None, state="normal", cursor="hand2", anchor="center", width=None,
                 wraplength=0, justify="left", hover=None, borda=None, raio=10,
                 disabledforeground=None, **_ignorados):
        try:
            fundo_pai = master.cget("bg")
        except tk.TclError:
            fundo_pai = COR_CARTAO
        super().__init__(master, bg=fundo_pai, highlightthickness=0, bd=0)
        self._texto, self._comando = text, command
        self._cor, self._fg, self._fonte = bg, fg, font
        self._padx = padx if padx is not None else (5 if width else 12)
        self._pady = pady if pady is not None else (3 if width else 6)
        self._estado, self._cursor, self._ancora = state, cursor, anchor
        self._chars, self._wrap, self._justify = width, wraplength, justify
        self._hover_cor, self._borda, self._raio = hover, borda, raio
        self._fg_off = disabledforeground
        self._sobre = False
        self._pressionado = False
        self._larg_nat = self._alt_nat = 20
        self._medir()
        self._aplicar_cursor()
        self.bind("<Configure>", lambda e: self._desenhar(e.width, e.height))
        self.bind("<Enter>", self._ao_entrar)
        self.bind("<Leave>", self._ao_sair)
        self.bind("<ButtonPress-1>", self._ao_pressionar)
        self.bind("<ButtonRelease-1>", self._ao_soltar)

    # --- tamanho e desenho ---------------------------------------------
    def _medir(self):
        t = self.create_text(0, 0, text=self._texto, font=self._fonte, anchor="nw", width=self._wrap or 0)
        caixa = self.bbox(t) or (0, 0, 0, 0)
        self.delete(t)
        largura_texto, altura_texto = caixa[2] - caixa[0], caixa[3] - caixa[1]
        if self._chars:
            larg = int(self._chars * tkfont.Font(font=self._fonte).measure("0")) + 2 * self._padx
        else:
            larg = largura_texto + 2 * self._padx
        self._larg_nat = max(larg, 20)
        self._alt_nat = max(altura_texto + 2 * self._pady, 20)
        tk.Canvas.configure(self, width=self._larg_nat, height=self._alt_nat)

    def _cores(self):
        if self._estado == "disabled":
            return "#DAD6C6", (self._fg_off or "#8F8C7C"), "#C6C2AE"
        fundo = self._cor
        if self._pressionado:
            fundo = ajustar_cor(self, self._cor, -0.12)
        elif self._sobre:
            fundo = self._hover_cor or ajustar_cor(self, self._cor, 0.14)
        borda = self._borda
        if borda is None:
            borda = ajustar_cor(self, self._cor, -0.28)
        texto = self._fg
        if texto is None:                 # sem cor definida: escolhe a mais legível para o fundo
            r, g, b = [v // 257 for v in self.winfo_rgb(self._cor)]
            texto = COR_TITULO if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "white"
        return fundo, texto, borda

    def _desenhar(self, w=None, h=None):
        if not self.winfo_exists():
            return
        w = w or self._larg_nat
        h = h or self._alt_nat
        self.delete("all")
        fundo, texto, borda = self._cores()
        r = max(2, min(self._raio, h // 2, w // 2))
        if borda:
            self._retangulo(1, 1, w - 1, h - 1, r, fill=fundo, outline=borda, width=2)
        else:
            self._retangulo(0, 0, w, h, r, fill=fundo, outline=fundo)
        if self._ancora in ("w", "nw", "sw"):
            self.create_text(self._padx + 2, h / 2, text=self._texto, font=self._fonte, fill=texto, anchor="w",
                             width=self._wrap or 0, justify=self._justify)
        else:
            self.create_text(w / 2, h / 2, text=self._texto, font=self._fonte, fill=texto, anchor="center",
                             width=self._wrap or 0, justify="center")

    def _retangulo(self, x1, y1, x2, y2, r, **opcoes):
        pontos = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
                  x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(pontos, smooth=True, **opcoes)

    def _redesenhar(self):
        w, h = self.winfo_width(), self.winfo_height()
        self._desenhar(w if w > 1 else None, h if h > 1 else None)

    def _aplicar_cursor(self):
        tk.Canvas.configure(self, cursor=self._cursor if self._estado != "disabled" else "arrow")

    # --- eventos -------------------------------------------------------
    def _ao_entrar(self, _e):
        self._sobre = True
        self._redesenhar()

    def _ao_sair(self, _e):
        self._sobre = False
        self._pressionado = False
        self._redesenhar()

    def _ao_pressionar(self, _e):
        if self._estado != "disabled":
            self._pressionado = True
            self._redesenhar()

    def _ao_soltar(self, e):
        estava = self._pressionado
        self._pressionado = False
        dentro = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        self._redesenhar()
        if estava and dentro:
            self.invoke()                 # sempre por último: o comando pode destruir o botão

    def invoke(self):
        if self._estado != "disabled" and self._comando:
            return self._comando()

    # --- compatibilidade com tk.Button: configure / cget ---------------
    def configure(self, cnf=None, **kw):
        if cnf:
            kw.update(cnf)
        mapa = {"text": "_texto", "command": "_comando", "bg": "_cor", "background": "_cor", "fg": "_fg",
                "foreground": "_fg", "font": "_fonte", "state": "_estado", "hover": "_hover_cor",
                "borda": "_borda", "wraplength": "_wrap", "cursor": "_cursor",
                "disabledforeground": "_fg_off", "anchor": "_ancora"}
        remedir = False
        for chave in list(kw):
            if chave in mapa:
                setattr(self, mapa[chave], kw.pop(chave))
                remedir = remedir or chave in ("text", "font", "wraplength")
            elif chave in ("activebackground", "activeforeground", "relief", "bd", "borderwidth"):
                kw.pop(chave)
        if kw:
            tk.Canvas.configure(self, **kw)
        if remedir:
            self._medir()
        self._aplicar_cursor()
        self._redesenhar()

    config = configure

    def cget(self, chave):
        proprios = {"text": self._texto, "state": self._estado, "bg": self._cor, "background": self._cor,
                    "fg": self._fg, "foreground": self._fg, "command": self._comando}
        if chave in proprios:
            return proprios[chave]
        return tk.Canvas.cget(self, chave)

    __getitem__ = cget

class Sobreposicao(tk.Frame):
    """Painel flutuante desenhado dentro da janela principal.
    Bloqueia o resto da tela até ser fechado (funciona como um pop-up, mas sem criar janela)."""

    def __init__(self, pai, x=None, y=None):
        super().__init__(pai, bg=COR_CARTAO, highlightbackground=COR_AZUL, highlightcolor=COR_AZUL, highlightthickness=2, padx=12, pady=10)
        self.pronto = tk.BooleanVar(master=pai, value=False)
        self.pos = (x, y)          # posição desejada em coordenadas da tela (ou None = centralizar)
        self.valor = None          # valor devolvido ao fechar
        self.foco = None           # widget que recebe o foco ao abrir
        self.anterior = pai.grab_current()

    def _ligar_escape(self, widget):
        widget.bind("<Escape>", lambda _e: self.fechar(), add="+")
        for filho in widget.winfo_children():
            self._ligar_escape(filho)

    def exibir(self):
        raiz = self.winfo_toplevel()
        raiz.update_idletasks()
        self.update_idletasks()
        largura, altura = self.winfo_reqwidth(), self.winfo_reqheight()
        pw = raiz.winfo_width() if raiz.winfo_width() > 200 else 1100
        ph = raiz.winfo_height() if raiz.winfo_height() > 200 else 720
        x, y = self.pos
        if x is None:
            px, py = (pw - largura) // 2, (ph - altura) // 2
        else:
            px, py = x - raiz.winfo_rootx(), y - raiz.winfo_rooty()
        px = max(8, min(px, pw - largura - 8))
        py = max(8, min(py, ph - altura - 8))
        self.place(x=px, y=py)
        self.lift()
        self._ligar_escape(self)
        try:
            self.grab_set()
        except tk.TclError:
            pass
        (self.foco or self).focus_set()
        self.wait_variable(self.pronto)

    def fechar(self, valor=None):
        self.valor = valor
        try:
            self.grab_release()
        except tk.TclError:
            pass
        anterior = self.anterior
        self.destroy()
        if anterior is not None:
            try:
                anterior.grab_set()
            except tk.TclError:
                pass
        self.pronto.set(True)

class _CaixaMensagem:
    def __init__(self, app):
        self.app = app

    """Substitui tkinter.messagebox: mostra os avisos e confirmações dentro da própria janela."""

    def _caixa(self, titulo, texto, icone, cor_icone, botoes, padrao=None):
        ov = Sobreposicao(self.app.janela)
        cabeca = tk.Frame(ov, bg=COR_CARTAO)
        cabeca.pack(fill="x")
        tk.Label(cabeca, text=icone, font=("Segoe UI Symbol", 22, "bold"), bg=COR_CARTAO, fg=cor_icone).pack(
            side="left", padx=(0, 10))
        tk.Label(cabeca, text=titulo, font=("Segoe UI", 12, "bold"), bg=COR_CARTAO, fg=COR_TITULO).pack(side="left")
        tk.Label(ov, text=texto, font=("Segoe UI", 10), bg=COR_CARTAO, justify="left", anchor="w",
                 wraplength=420).pack(fill="x", pady=(10, 14))
        barra = tk.Frame(ov, bg=COR_CARTAO)
        barra.pack(anchor="e")
        for rotulo, valor, cor in botoes:
            Botao(barra, text=rotulo, bg=cor, fg="white" if cor != COR_NEUTRO else COR_TITULO, bd=0,
                      padx=18, pady=6, font=("Segoe UI", 10, "bold"), cursor="hand2",
                      command=lambda v=valor: ov.fechar(v)).pack(side="left", padx=4)
        ov.bind("<Return>", lambda _e: ov.fechar(padrao))
        ov.exibir()
        return ov.valor

    def showinfo(self, titulo, texto, **_k):
        self._caixa(titulo, texto, "ℹ", COR_AZUL, [("OK", True, COR_AZUL)], True)
        return "ok"

    def showwarning(self, titulo, texto, **_k):
        self._caixa(titulo, texto, "⚠", COR_LARANJA, [("OK", True, COR_LARANJA)], True)
        return "ok"

    def showerror(self, titulo, texto, **_k):
        self._caixa(titulo, texto, "✖", COR_VERMELHO, [("OK", True, COR_VERMELHO)], True)
        return "ok"

    def askyesno(self, titulo, texto, **_k):
        return bool(self._caixa(titulo, texto, "?", COR_AZUL,
                                [("Não", False, COR_NEUTRO), ("Sim", True, COR_AZUL)], False))

class SeletorData(Sobreposicao):
    """Calendário. Resultado: objeto date, '' (limpar) ou None (cancelado)."""

    def __init__(self, pai, inicial, posicao, permitir_limpar=False):
        super().__init__(pai, posicao[0], posicao[1])
        self.resultado = None
        self.ano, self.mes = inicial.year, inicial.month
        self.selecionada = inicial

        topo = tk.Frame(self, bg=COR_CARTAO)
        topo.pack(fill="x")
        estilo = dict(font=("Segoe UI", 10, "bold"), bd=0, bg=COR_CARTAO,
                      hover="#E9EEDC", borda="", cursor="hand2", width=3)
        Botao(topo, text="«", command=lambda: self.mover(-12), **estilo).pack(side="left")
        Botao(topo, text="‹", command=lambda: self.mover(-1), **estilo).pack(side="left")
        self.lbl_mes = tk.Label(topo, font=("Segoe UI", 11, "bold"), bg=COR_CARTAO, width=16)
        self.lbl_mes.pack(side="left", expand=True)
        Botao(topo, text="›", command=lambda: self.mover(1), **estilo).pack(side="left")
        Botao(topo, text="»", command=lambda: self.mover(12), **estilo).pack(side="left")

        self.grade = tk.Frame(self, bg=COR_CARTAO)
        self.grade.pack(pady=4)
        for col in range(7):
            self.grade.columnconfigure(col, minsize=38)

        rodape = tk.Frame(self, bg=COR_CARTAO)
        rodape.pack(fill="x", pady=(6, 0))
        estilo_rodape = dict(font=("Segoe UI", 9), bd=0, padx=10, pady=4, cursor="hand2")
        Botao(rodape, text="Hoje", bg=COR_PISTACHE_CLARO, command=lambda: self.escolher(date.today()),
                  **estilo_rodape).pack(side="left")
        if permitir_limpar:
            Botao(rodape, text="Limpar", bg="#F2DCD3", command=self.limpar,
                      **estilo_rodape).pack(side="left", padx=6)
        Botao(rodape, text="Cancelar", bg=COR_NEUTRO, command=self.fechar,
                  **estilo_rodape).pack(side="right")

        self.desenhar()
        self.exibir()

    def mover(self, delta_meses):
        total = self.ano * 12 + (self.mes - 1) + delta_meses
        novo_ano = total // 12
        if not 1 <= novo_ano <= 9999:
            return
        self.ano, self.mes = novo_ano, total % 12 + 1
        self.desenhar()

    def desenhar(self):
        for w in self.grade.winfo_children():
            w.destroy()
        self.lbl_mes.config(text="%s de %d" % (MESES[self.mes - 1], self.ano))
        for col, nome in enumerate(DIAS_SEMANA):
            tk.Label(self.grade, text=nome, font=("Segoe UI", 9, "bold"),
                     fg=COR_TEXTO_SUAVE, bg=COR_CARTAO).grid(row=0, column=col, pady=(6, 2))
        hoje = date.today()
        semanas = calendar.Calendar(firstweekday=6).monthdayscalendar(self.ano, self.mes)
        for lin, semana in enumerate(semanas, start=1):
            for col, dia in enumerate(semana):
                if dia == 0:
                    continue
                atual = date(self.ano, self.mes, dia)
                if atual == self.selecionada:
                    bg, fg = COR_AZUL, "white"
                elif atual == hoje:
                    bg, fg = COR_PISTACHE_CLARO, COR_TITULO
                else:
                    bg, fg = COR_CARTAO, COR_TITULO
                Botao(self.grade, text=str(dia), width=3, bd=0, bg=bg, fg=fg,
                          hover="#D4DFBC", borda="" if bg == COR_CARTAO else None, raio=8, font=("Segoe UI", 10), cursor="hand2",
                          command=lambda d=atual: self.escolher(d)).grid(row=lin, column=col, padx=1, pady=1)

    def escolher(self, dia):
        self.resultado = dia
        self.fechar(dia)

    def limpar(self):
        self.resultado = ""
        self.fechar("")

class SeletorHora(Sobreposicao):
    """Relógio: clique na hora (anel externo 1-12, interno 13-00) e depois nos minutos.
    Resultado: texto 'HH:MM' ou None (cancelado)."""

    CX = CY = 130
    R_EXT = 98
    R_INT = 62

    def __init__(self, pai, inicial, posicao):
        super().__init__(pai, posicao[0], posicao[1])
        self.resultado = None
        self.hora, self.minuto = inicial.hour, inicial.minute
        self.modo = "hora"

        topo = tk.Frame(self, bg=COR_CARTAO)
        topo.pack()
        self.lbl_h = tk.Label(topo, font=("Segoe UI", 30, "bold"), bg=COR_CARTAO, cursor="hand2", width=3)
        self.lbl_h.pack(side="left")
        tk.Label(topo, text=":", font=("Segoe UI", 30, "bold"), bg=COR_CARTAO, fg=COR_INATIVO).pack(side="left")
        self.lbl_m = tk.Label(topo, font=("Segoe UI", 30, "bold"), bg=COR_CARTAO, cursor="hand2", width=3)
        self.lbl_m.pack(side="left")
        self.lbl_h.bind("<Button-1>", lambda _e: self.trocar_modo("hora"))
        self.lbl_m.bind("<Button-1>", lambda _e: self.trocar_modo("minuto"))

        self.lbl_dica = tk.Label(self, font=("Segoe UI", 9), fg=COR_TEXTO_SUAVE, bg=COR_CARTAO)
        self.lbl_dica.pack()

        self.canvas = tk.Canvas(self, width=260, height=260, bg=COR_CARTAO, highlightthickness=0)
        self.canvas.pack(pady=4)
        self.canvas.bind("<Button-1>", self.ao_clicar)
        self.canvas.bind("<B1-Motion>", self.ao_clicar)
        self.canvas.bind("<ButtonRelease-1>", self.ao_soltar)

        rodape = tk.Frame(self, bg=COR_CARTAO)
        rodape.pack(fill="x", pady=(4, 0))
        estilo_rodape = dict(font=("Segoe UI", 9), bd=0, padx=12, pady=4, cursor="hand2")
        Botao(rodape, text="Agora", bg=COR_PISTACHE_CLARO, command=self.usar_agora, **estilo_rodape).pack(side="left")
        Botao(rodape, text="OK", bg=COR_AZUL, fg="white", command=self.confirmar,
                  **estilo_rodape).pack(side="right")
        Botao(rodape, text="Cancelar", bg=COR_NEUTRO, command=self.fechar,
                  **estilo_rodape).pack(side="right", padx=6)

        self.desenhar()
        self.exibir()

    # --- geometria -----------------------------------------------------
    def ponto(self, raio, angulo):
        rad = math.radians(angulo)
        return self.CX + raio * math.sin(rad), self.CY - raio * math.cos(rad)

    def trocar_modo(self, modo):
        self.modo = modo
        self.desenhar()

    def usar_agora(self):
        agora = datetime.now()
        self.hora, self.minuto = agora.hour, agora.minute
        self.modo = "hora"
        self.desenhar()

    def confirmar(self):
        self.resultado = "%02d:%02d" % (self.hora, self.minuto)
        self.fechar(self.resultado)

    # --- desenho -------------------------------------------------------
    def desenhar(self):
        c = self.canvas
        c.delete("all")
        cx, cy = self.CX, self.CY

        self.lbl_h.config(text="%02d" % self.hora, fg=COR_AZUL if self.modo == "hora" else COR_INATIVO)
        self.lbl_m.config(text="%02d" % self.minuto, fg=COR_AZUL if self.modo == "minuto" else COR_INATIVO)
        self.lbl_dica.config(text="Clique na hora (anel externo: 1–12, interno: 13–00)"
                             if self.modo == "hora" else "Clique nos minutos")

        c.create_oval(cx - 120, cy - 120, cx + 120, cy + 120, fill="#EFEAD8", outline="")

        if self.modo == "hora":
            if self.hora == 0:
                ang, raio = 0, self.R_INT
            elif self.hora <= 12:
                ang, raio = (self.hora % 12) * 30, self.R_EXT
            else:
                ang, raio = (self.hora - 12) * 30, self.R_INT
            raio_bola = 17 if raio == self.R_EXT else 15
        else:
            ang, raio, raio_bola = self.minuto * 6, self.R_EXT, 17
        px, py = self.ponto(raio, ang)
        c.create_line(cx, cy, px, py, fill=COR_AZUL, width=2)
        c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=COR_AZUL, outline=COR_AZUL)
        c.create_oval(px - raio_bola, py - raio_bola, px + raio_bola, py + raio_bola,
                      fill=COR_AZUL, outline=COR_AZUL)
        if self.modo == "minuto" and self.minuto % 5 != 0:
            c.create_oval(px - 3, py - 3, px + 3, py + 3, fill="white", outline="white")

        if self.modo == "hora":
            for k in range(12):
                externo = 12 if k == 0 else k
                interno = 0 if k == 0 else 12 + k
                self.numero(externo, k * 30, self.R_EXT, 11, externo == self.hora)
                self.numero(interno, k * 30, self.R_INT, 9, interno == self.hora)
        else:
            for m in range(0, 60, 5):
                self.numero(m, m * 6, self.R_EXT, 11, m == self.minuto)

    def numero(self, valor, angulo, raio, tamanho, selecionado):
        x, y = self.ponto(raio, angulo)
        texto = "%02d" % valor if self.modo == "minuto" or valor == 0 else str(valor)
        self.canvas.create_text(x, y, text=texto, font=("Segoe UI", tamanho),
                                fill="white" if selecionado else COR_TITULO)

    # --- eventos do mouse ----------------------------------------------
    def ao_clicar(self, evento):
        dx, dy = evento.x - self.CX, evento.y - self.CY
        dist = math.hypot(dx, dy)
        if dist < 15:
            return
        ang = math.degrees(math.atan2(dx, -dy)) % 360
        if self.modo == "hora":
            k = int(round(ang / 30)) % 12
            if dist < (self.R_EXT + self.R_INT) / 2:
                self.hora = 0 if k == 0 else 12 + k
            else:
                self.hora = 12 if k == 0 else k
        else:
            self.minuto = int(round(ang / 6)) % 60
        self.desenhar()

    def ao_soltar(self, _evento):
        if self.modo == "hora":      # depois de escolher a hora, vai para os minutos
            self.modo = "minuto"
            self.desenhar()

class _CampoMascarado(tk.Frame):
    """Campo com máscara validada pelo próprio Tk, inclusive em colagem de texto.

    Durante a digitação aceita prefixos parciais; nunca aceita caracteres
    fora da máscara. A validade completa também é checada pelo serviço.
    """
    def __init__(self, pai, mascara, largura, icone):
        super().__init__(pai, bg=COR_CARTAO)
        self.mascara = mascara
        self.var = tk.StringVar(master=self)
        validar = (self.register(self._validar), '%P')
        self.entry = tk.Entry(self, textvariable=self.var, font=("Segoe UI", 11),
                              width=largura, validate='key', validatecommand=validar)
        self.entry.pack(side='left', fill='x', expand=True, ipady=3)
        self.entry.bind('<KeyPress>', self._inserir_separador)
        Botao(self, text=icone, font=("Segoe UI Emoji", 10), bd=0,
              bg=COR_PISTACHE_CLARO, cursor='hand2', command=self.abrir).pack(
                  side='left', padx=(4, 0), ipady=1)

    def _validar(self, proposto):
        return corresponde_mascara(proposto, self.mascara)

    def _inserir_separador(self, evento):
        """Insere / ou : antes do próximo dígito, sem afetar edição/colagem."""
        if evento.char not in '0123456789' or not evento.char:
            return
        if self.entry.selection_present():
            return
        indice = self.entry.index(tk.INSERT)
        if indice < len(self.mascara) and self.mascara[indice] in '/:':
            if indice == len(self.entry.get()):
                self.entry.insert(indice, self.mascara[indice])

    def get(self):
        return self.var.get()

    def set(self, texto):
        if not corresponde_mascara(texto, self.mascara):
            raise ValueError('Valor incompatível com máscara %s' % self.mascara)
        self.var.set(texto)

    def clear(self):
        self.var.set('')


class CampoData(_CampoMascarado):
    """Campo de data dd/mm/aaaa com calendário e digitação protegida."""
    def __init__(self, pai):
        super().__init__(pai, MASCARA_DATA, 11, "📅")

    def abrir(self):
        try:
            inicial = datetime.strptime(self.get(), FORMATO_DATA).date()
        except ValueError:
            inicial = date.today()
        posicao = (self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())
        seletor = SeletorData(self.winfo_toplevel(), inicial, posicao)
        if isinstance(seletor.resultado, date):
            self.set(seletor.resultado.strftime(FORMATO_DATA))


class CampoHora(_CampoMascarado):
    """Campo de hora hh:mm com relógio e digitação protegida."""
    def __init__(self, pai):
        super().__init__(pai, MASCARA_HORA, 7, "🕒")

    def abrir(self):
        try:
            inicial = datetime.strptime(self.get(), FORMATO_HORA)
        except ValueError:
            inicial = datetime.now()
        posicao = (self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())
        seletor = SeletorHora(self.winfo_toplevel(), inicial, posicao)
        if seletor.resultado:
            self.set(seletor.resultado)
