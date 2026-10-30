import calendar
import csv
import difflib
import hashlib
import hmac
import json
import math
import os
import random
import re
import secrets
import sys
import unicodedata
import uuid
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from datetime import datetime, date, timedelta

# ----------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------
FORMATO_DATA = "%d/%m/%Y"
FORMATO_HORA = "%H:%M"
FORMATO_DATA_HORA = FORMATO_DATA + " " + FORMATO_HORA
TIPOS_ACESSO = ["Visitante", "Morador", "Entregador", "Funcionário"]

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(PASTA, "registros_portaria.csv")
ARQUIVO_AUDITORIA = os.path.join(PASTA, "auditoria_portaria.csv")
ARQUIVO_TIPOS_TEMP = os.path.join(PASTA, "tipos_temporarios.csv")
CABECALHO = ["Id", "Nome", "Tipo", "Entrada", "Saida"]
CABECALHO_AUDITORIA = ["Quando", "Acao", "Id", "Nome", "Campo", "Anterior", "Novo", "Usuario"]
CABECALHO_TIPOS_TEMP = ["Tipo", "CriadoEm"]
OPCAO_NOVO = "+ Novo tipo temporário..."
VALIDADE_TEMPORARIO = timedelta(hours=24)
FORMATO_CRIACAO = "%d/%m/%Y %H:%M:%S"

COLUNAS = ["Nome", "Tipo", "Entrada", "Saida"]
ROTULOS = {"Nome": "Nome", "Tipo": "Tipo de acesso", "Entrada": "Entrada", "Saida": "Saída"}

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

# Visual do aplicativo: creme + pistache / verde selva
BARRA_TITULO_PERSONALIZADA = True   # False = usa a barra de título normal do sistema
COR_FUNDO = "#F3EFE2"           # creme de abacaxi (fundo das telas)
COR_CARTAO = "#FCFAF3"          # creme bem claro (cartões, formulários, campos)
COR_CREME = "#EFE8CD"           # greige comfy (detalhes e textos sobre o verde)
COR_BORDA = "#D2CBB0"
COR_TITULO = "#2E3A28"          # verde escuro (textos)
COR_TEXTO_SUAVE = "#7A7864"
COR_INATIVO = "#9A9A86"
COR_PISTACHE_CLARO = "#DCE6C8"
COR_NEUTRO = "#E6E0C8"
COR_PENDENTE = "#F6EBC0"
COR_VERDE = "#7C9A64"           # pistache (ação principal: cadastrar, salvar, entrar)
COR_AZUL = "#5F7350"            # verde selva (ações secundárias)
COR_VERMELHO = "#A8513E"        # terracota (excluir, erros)
COR_LARANJA = "#B8862F"         # mostarda (registrar saída, avisos)
COR_CINZA = "#7A7563"
COR_TEMPORARIO = "#9B5A2E"      # tipos temporários (texto)

# ----------------------------------------------------------------------
# Botão com cantos arredondados e borda (substitui o tk.Button comum)
# ----------------------------------------------------------------------
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



# Listas em memória
registros = []   # cada item: {"Id", "Nome", "Tipo", "Entrada", "Saida"}
auditoria = []   # cada item: {"Quando", "Acao", "Id", "Nome", "Campo", "Anterior", "Novo"}
tipos_temporarios = []   # cada item: {"Tipo", "CriadoEm"}  (ativos por 24 h, depois arquivados)
ultimo_tipo = {"valor": TIPOS_ACESSO[0]}   # última opção válida escolhida no campo Tipo


# ----------------------------------------------------------------------
# Funções auxiliares
# ----------------------------------------------------------------------
def novo_id():
    return uuid.uuid4().hex[:8]


def agora_data():
    return datetime.now().strftime(FORMATO_DATA)


def agora_hora():
    return datetime.now().strftime(FORMATO_HORA)


def converter_data_hora(texto):
    """Converte 'dd/mm/aaaa hh:mm' em datetime. Retorna None se inválido."""
    try:
        return datetime.strptime(texto.strip(), FORMATO_DATA_HORA)
    except ValueError:
        return None


def normalizar(texto):
    """Minúsculas e sem acento, para a pesquisa ignorar maiúsculas/acentos."""
    decomposto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def validar_ordem(entrada, saida):
    """Verificação semântica: a saída não pode ser anterior à entrada."""
    if not saida:
        return None
    dt_entrada = converter_data_hora(entrada)
    dt_saida = converter_data_hora(saida)
    if dt_entrada and dt_saida and dt_saida < dt_entrada:
        return "A saída não pode ser anterior à entrada."
    return None


def buscar_registro(id_registro):
    for reg in registros:
        if reg["Id"] == id_registro:
            return reg
    return None


def eh_temporario(tipo):
    """Um tipo que não está na lista fixa é considerado temporário."""
    return tipo not in TIPOS_ACESSO


def tipos_temporarios_ativos():
    """Tipos temporários criados há menos de 24 horas (os demais ficam arquivados)."""
    agora = datetime.now()
    ativos = []
    for item in tipos_temporarios:
        try:
            criado = datetime.strptime(item["CriadoEm"], FORMATO_CRIACAO)
        except ValueError:
            continue
        if agora - criado < VALIDADE_TEMPORARIO and item["Tipo"] not in ativos:
            ativos.append(item["Tipo"])
    return ativos


# ----------------------------------------------------------------------
# Leitura e gravação dos arquivos
# ----------------------------------------------------------------------
def carregar_registros():
    if not os.path.exists(ARQUIVO):
        return
    precisa_salvar = False
    try:
        with open(ARQUIVO, newline="", encoding="utf-8-sig") as f:
            for linha in csv.DictReader(f):
                id_reg = linha.get("Id") or ""
                if not id_reg:           # arquivo da versão 1 (sem Id)
                    id_reg = novo_id()
                    precisa_salvar = True
                registros.append({
                    "Id": id_reg,
                    "Nome": (linha.get("Nome") or "").strip(),
                    "Tipo": (linha.get("Tipo") or "").strip(),
                    "Entrada": (linha.get("Entrada") or "").strip(),
                    "Saida": (linha.get("Saida") or "").strip(),
                })
    except (OSError, csv.Error):
        messagebox.showwarning("Aviso", "Não foi possível ler o arquivo de registros.")
    if precisa_salvar:
        salvar_registros()


def salvar_registros():
    try:
        with open(ARQUIVO, "w", newline="", encoding="utf-8-sig") as f:
            escritor = csv.DictWriter(f, fieldnames=CABECALHO)
            escritor.writeheader()
            escritor.writerows(registros)
    except OSError:
        messagebox.showerror("Erro", "Não foi possível salvar o arquivo de registros.")


def carregar_tipos_temporarios():
    if not os.path.exists(ARQUIVO_TIPOS_TEMP):
        return
    try:
        with open(ARQUIVO_TIPOS_TEMP, newline="", encoding="utf-8-sig") as f:
            for linha in csv.DictReader(f):
                if linha.get("Tipo"):
                    tipos_temporarios.append({"Tipo": linha["Tipo"].strip(),
                                              "CriadoEm": (linha.get("CriadoEm") or "").strip()})
    except (OSError, csv.Error):
        messagebox.showwarning("Aviso", "Não foi possível ler o arquivo de tipos temporários.")


def salvar_tipos_temporarios():
    try:
        with open(ARQUIVO_TIPOS_TEMP, "w", newline="", encoding="utf-8-sig") as f:
            escritor = csv.DictWriter(f, fieldnames=CABECALHO_TIPOS_TEMP)
            escritor.writeheader()
            escritor.writerows(tipos_temporarios)
    except OSError:
        messagebox.showerror("Erro", "Não foi possível salvar o arquivo de tipos temporários.")


def carregar_auditoria():
    if not os.path.exists(ARQUIVO_AUDITORIA):
        return
    try:
        with open(ARQUIVO_AUDITORIA, newline="", encoding="utf-8-sig") as f:
            for linha in csv.DictReader(f):
                auditoria.append({c: (linha.get(c) or "") for c in CABECALHO_AUDITORIA})
    except (OSError, csv.Error):
        messagebox.showwarning("Aviso", "Não foi possível ler o arquivo de auditoria.")


def salvar_auditoria():
    try:
        with open(ARQUIVO_AUDITORIA, "w", newline="", encoding="utf-8-sig") as f:
            escritor = csv.DictWriter(f, fieldnames=CABECALHO_AUDITORIA)
            escritor.writeheader()
            escritor.writerows(auditoria)
    except OSError:
        messagebox.showerror("Erro", "Não foi possível salvar o arquivo de auditoria.")


def registrar_auditoria(acao, id_reg, nome, campo, anterior, novo):
    auditoria.append({
        "Quando": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Acao": acao,
        "Id": id_reg,
        "Nome": nome,
        "Campo": campo,
        "Anterior": anterior,
        "Novo": novo,
        "Usuario": nome_sessao(),
    })
    salvar_auditoria()
    atualizar_auditoria()


# ----------------------------------------------------------------------
# Painéis dentro da janela principal (o app NÃO abre janelas novas)
# ----------------------------------------------------------------------
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
    """Substitui tkinter.messagebox: mostra os avisos e confirmações dentro da própria janela."""

    def _caixa(self, titulo, texto, icone, cor_icone, botoes, padrao=None):
        ov = Sobreposicao(janela)
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


messagebox = _CaixaMensagem()


def pedir_texto(titulo, instrucao):
    """Pergunta um texto dentro da janela. Retorna o texto digitado ou None se cancelado."""
    ov = Sobreposicao(janela)
    tk.Label(ov, text=titulo, font=("Segoe UI", 12, "bold"), bg=COR_CARTAO, fg=COR_TITULO).pack(anchor="w")
    tk.Label(ov, text=instrucao, font=("Segoe UI", 10), bg=COR_CARTAO, justify="left", wraplength=380).pack(
        anchor="w", pady=(4, 8))
    entrada = tk.Entry(ov, font=("Segoe UI", 11), width=38)
    entrada.pack(fill="x", ipady=3)
    barra = tk.Frame(ov, bg=COR_CARTAO)
    barra.pack(anchor="e", pady=(12, 0))
    Botao(barra, text="Cancelar", bg=COR_NEUTRO, bd=0, padx=14, pady=6, cursor="hand2",
              command=ov.fechar).pack(side="left", padx=4)
    Botao(barra, text="OK", bg=COR_AZUL, fg="white", bd=0, padx=18, pady=6, font=("Segoe UI", 10, "bold"),
              cursor="hand2", command=lambda: ov.fechar(entrada.get())).pack(side="left")
    entrada.bind("<Return>", lambda _e: ov.fechar(entrada.get()))
    ov.foco = entrada
    ov.exibir()
    return ov.valor


# ----------------------------------------------------------------------
# Calendário e relógio (também dentro da janela, feitos só com a biblioteca padrão)
# ----------------------------------------------------------------------
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


class CampoData(tk.Frame):
    """Campo de data (dd/mm/aaaa) com botão de calendário."""

    def __init__(self, pai):
        super().__init__(pai, bg=COR_CARTAO)
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, font=("Segoe UI", 11), width=11)
        self.entry.pack(side="left", fill="x", expand=True, ipady=3)
        Botao(self, text="📅", font=("Segoe UI Emoji", 10), bd=0, bg=COR_PISTACHE_CLARO,
                  cursor="hand2", command=self.abrir).pack(side="left", padx=(4, 0), ipady=1)

    def get(self):
        return self.var.get().strip()

    def set(self, texto):
        self.var.set(texto)

    def clear(self):
        self.var.set("")

    def abrir(self):
        try:
            inicial = datetime.strptime(self.get(), FORMATO_DATA).date()
        except ValueError:
            inicial = date.today()
        posicao = (self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())
        seletor = SeletorData(self.winfo_toplevel(), inicial, posicao)
        if isinstance(seletor.resultado, date):
            self.var.set(seletor.resultado.strftime(FORMATO_DATA))


class CampoHora(tk.Frame):
    """Campo de hora (hh:mm) com botão de relógio."""

    def __init__(self, pai):
        super().__init__(pai, bg=COR_CARTAO)
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, font=("Segoe UI", 11), width=7)
        self.entry.pack(side="left", fill="x", expand=True, ipady=3)
        Botao(self, text="🕒", font=("Segoe UI Emoji", 10), bd=0, bg=COR_PISTACHE_CLARO,
                  cursor="hand2", command=self.abrir).pack(side="left", padx=(4, 0), ipady=1)

    def get(self):
        return self.var.get().strip()

    def set(self, texto):
        self.var.set(texto)

    def clear(self):
        self.var.set("")

    def abrir(self):
        try:
            inicial = datetime.strptime(self.get(), FORMATO_HORA)
        except ValueError:
            inicial = datetime.now()
        posicao = (self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())
        seletor = SeletorHora(self.winfo_toplevel(), inicial, posicao)
        if seletor.resultado:
            self.var.set(seletor.resultado)


# ----------------------------------------------------------------------
# Tipos de acesso temporários
# ----------------------------------------------------------------------
def criar_tipo_temporario():
    """Pergunta o nome do tipo temporário e o disponibiliza por 24 horas.
    Retorna o nome a usar, ou None se cancelado."""
    nome = pedir_texto(
        "Tipo de acesso temporário",
        "Descreva o tipo (ex.: Mecânico, Técnico de internet).\n"
        "Ele ficará disponível na lista por 24 horas.")
    if nome is None:
        return None
    nome = " ".join(nome.split())
    if nome == "":
        messagebox.showwarning("Atenção", "Informe o nome do tipo temporário.")
        return None
    for fixo in TIPOS_ACESSO:                       # igual a um tipo fixo: usa o fixo
        if normalizar(fixo) == normalizar(nome):
            return fixo
    for ativo in tipos_temporarios_ativos():        # já existe e está ativo: reutiliza
        if normalizar(ativo) == normalizar(nome):
            return ativo
    tipos_temporarios.append({"Tipo": nome, "CriadoEm": datetime.now().strftime(FORMATO_CRIACAO)})
    salvar_tipos_temporarios()
    atualizar_opcoes_tipo()
    return nome


def atualizar_opcoes_tipo():
    """Remonta a lista do campo Tipo: fixos + temporários ativos + opção 'Novo'.
    Tipos temporários com mais de 24 h somem da lista (ficam arquivados no CSV)."""
    valores = TIPOS_ACESSO + tipos_temporarios_ativos() + [OPCAO_NOVO]
    campo_tipo["values"] = valores
    if campo_tipo.get() not in valores or campo_tipo.get() == OPCAO_NOVO:
        campo_tipo.set(TIPOS_ACESSO[0])
        ultimo_tipo["valor"] = TIPOS_ACESSO[0]


def ao_selecionar_tipo(_evento=None):
    if campo_tipo.get() == OPCAO_NOVO:
        novo = criar_tipo_temporario()
        campo_tipo.set(novo if novo else ultimo_tipo["valor"])
    ultimo_tipo["valor"] = campo_tipo.get()


def verificar_expiracao():
    """Roda a cada minuto para retirar da lista os tipos temporários vencidos."""
    atualizar_opcoes_tipo()
    janela.after(60000, verificar_expiracao)


def editar_para_temporario(reg):
    novo = criar_tipo_temporario()
    if novo:
        aplicar_edicao(reg, "Tipo", novo)


# ----------------------------------------------------------------------
# Tabela principal
# ----------------------------------------------------------------------
def atualizar_tabela():
    """Redesenha a tabela aplicando a pesquisa e o filtro de pendentes."""
    selecionados = set(tabela.selection())
    for item in tabela.get_children():
        tabela.delete(item)

    termos = normalizar(var_busca.get().strip()).split()
    so_pendentes = var_pendentes.get()
    exibidos = 0
    for reg in reversed(registros):                 # mais recentes primeiro
        if so_pendentes and reg["Saida"]:
            continue
        if termos:
            texto = normalizar(" ".join([reg["Nome"], reg["Tipo"], reg["Entrada"], reg["Saida"],
                                         "temporario" if eh_temporario(reg["Tipo"]) else ""]))
            if not all(t in texto for t in termos):
                continue
        tags = []
        if not reg["Saida"]:
            tags.append("pendente")
        tipo_exibido = reg["Tipo"]
        if eh_temporario(reg["Tipo"]):              # tipo temporário: * e texto roxo
            tipo_exibido += " *"
            tags.append("temporario")
        tabela.insert("", "end", iid=reg["Id"],
                      values=(reg["Nome"], tipo_exibido, reg["Entrada"], reg["Saida"] or "—"),
                      tags=tuple(tags))
        exibidos += 1

    for iid in selecionados:
        if tabela.exists(iid):
            tabela.selection_add(iid)

    pendentes = sum(1 for r in registros if not r["Saida"])
    lbl_contagem.config(text="Exibindo %d de %d registro(s)  |  Sem saída: %d" % (exibidos, len(registros), pendentes))


def limpar_filtro():
    var_busca.set("")
    var_pendentes.set(False)
    campo_busca.focus()


# ----------------------------------------------------------------------
# Ações dos botões
# ----------------------------------------------------------------------
def cadastrar():
    if not exigir("cadastrar"):
        return
    nome_pessoa = campo_nome.get().strip()
    tipo_acesso = campo_tipo.get().strip()

    if nome_pessoa == "":
        messagebox.showwarning("Atenção", "Informe o nome da pessoa.")
        campo_nome.focus()
        return

    # VERIFICAÇÃO SEMÂNTICA 1: o tipo precisa ser fixo ou um temporário ainda ativo (< 24 h)
    if tipo_acesso not in TIPOS_ACESSO + tipos_temporarios_ativos():
        messagebox.showwarning("Atenção", "Selecione um tipo de acesso válido.\n"
                                          "(Um tipo temporário pode ter passado de 24 horas.)")
        return

    entrada = converter_data_hora(campo_ent_data.get() + " " + campo_ent_hora.get())
    if entrada is None:
        messagebox.showwarning("Atenção", "Data ou hora de entrada inválida.\nUse dd/mm/aaaa e hh:mm "
                                          "(ou escolha pelo calendário e pelo relógio).")
        campo_ent_data.entry.focus()
        return
    texto_entrada = entrada.strftime(FORMATO_DATA_HORA)

    texto_saida = ""
    data_sai, hora_sai = campo_sai_data.get(), campo_sai_hora.get()
    if data_sai or hora_sai:
        if not (data_sai and hora_sai):
            messagebox.showwarning("Atenção", "Preencha a data e a hora da saída, ou deixe os dois em branco.")
            return
        saida = converter_data_hora(data_sai + " " + hora_sai)
        if saida is None:
            messagebox.showwarning("Atenção", "Data ou hora de saída inválida.\nUse dd/mm/aaaa e hh:mm.")
            campo_sai_data.entry.focus()
            return
        texto_saida = saida.strftime(FORMATO_DATA_HORA)

    # VERIFICAÇÃO SEMÂNTICA 2: a saída não pode ser anterior à entrada
    erro = validar_ordem(texto_entrada, texto_saida)
    if erro:
        messagebox.showwarning("Atenção", erro)
        return

    registros.append({
        "Id": novo_id(),
        "Nome": nome_pessoa,
        "Tipo": tipo_acesso,
        "Entrada": texto_entrada,
        "Saida": texto_saida,
    })
    salvar_registros()
    atualizar_tabela()
    messagebox.showinfo("Cadastro", "Registro cadastrado com sucesso!")
    limpar()


def limpar():
    """Limpa o formulário e restaura a data/hora atual na entrada."""
    campo_nome.delete(0, tk.END)
    campo_tipo.set(TIPOS_ACESSO[0])
    ultimo_tipo["valor"] = TIPOS_ACESSO[0]
    campo_ent_data.set(agora_data())
    campo_ent_hora.set(agora_hora())
    campo_sai_data.clear()
    campo_sai_hora.clear()
    campo_nome.focus()


def registrar_saida():
    """Registra a saída do registro selecionado na tabela (use a pesquisa para achá-lo).
    Usa a data/hora de saída do formulário; se estiverem vazias, usa o momento atual."""
    if not exigir("saida"):
        return
    selecionados = tabela.selection()
    if len(selecionados) != 1:
        messagebox.showwarning("Atenção", "Selecione na tabela UM registro para registrar a saída.\n"
                                          "Dica: use a pesquisa para localizar quem entrou dias atrás.")
        return
    reg = buscar_registro(selecionados[0])
    if reg is None:
        return
    if reg["Saida"]:
        messagebox.showwarning("Atenção", "Este registro já possui saída (%s).\n"
                                          "Para corrigir, dê um duplo clique na célula Saída "
                                          "(a alteração ficará na Auditoria)." % reg["Saida"])
        return

    data_sai, hora_sai = campo_sai_data.get(), campo_sai_hora.get()
    if not data_sai and not hora_sai:
        data_sai, hora_sai = agora_data(), agora_hora()
    elif not (data_sai and hora_sai):
        messagebox.showwarning("Atenção", "Preencha a data e a hora da saída, ou deixe os dois em branco "
                                          "para usar o momento atual.")
        return
    saida = converter_data_hora(data_sai + " " + hora_sai)
    if saida is None:
        messagebox.showwarning("Atenção", "Data ou hora de saída inválida.")
        return
    texto_saida = saida.strftime(FORMATO_DATA_HORA)

    erro = validar_ordem(reg["Entrada"], texto_saida)
    if erro:
        messagebox.showwarning("Atenção", erro + "\nEntrada deste registro: " + reg["Entrada"])
        return

    if aplicar_edicao(reg, "Saida", texto_saida):
        campo_sai_data.clear()
        campo_sai_hora.clear()


def aplicar_edicao(reg, campo, novo):
    """Aplica uma alteração em um campo do registro.
    - Primeiro preenchimento da saída: apenas grava (não vai para a auditoria).
    - Qualquer outra alteração: grava, registra na auditoria e mostra o valor anterior."""
    # Permissão: preencher a saída vazia exige "saida"; qualquer outra alteração exige "editar"
    if campo == "Saida" and reg["Saida"] == "":
        if not exigir("saida"):
            return False
    elif not exigir("editar"):
        return False
    anterior = reg[campo]
    if anterior == novo:
        return False
    nome_ref = reg["Nome"]          # nome antes da alteração (para o histórico)
    reg[campo] = novo
    salvar_registros()
    atualizar_tabela()

    if campo == "Saida" and anterior == "":
        messagebox.showinfo("Saída registrada", "Saída de %s registrada em %s." % (reg["Nome"], novo))
        return True

    registrar_auditoria("EDIÇÃO", reg["Id"], nome_ref, ROTULOS[campo], anterior, novo)
    messagebox.showinfo(
        "Registro alterado",
        "Campo alterado: %s\nValor anterior: %s\nNovo valor: %s\n\nA alteração foi guardada na Auditoria."
        % (ROTULOS[campo], anterior or "(vazio)", novo or "(vazio)"))
    return True


def excluir_selecionado():
    if not exigir("excluir"):
        return
    selecionados = tabela.selection()
    if not selecionados:
        messagebox.showwarning("Atenção", "Selecione um registro na tabela para excluir.")
        return
    if not messagebox.askyesno("Confirmar", "Excluir %d registro(s)?\nA exclusão ficará guardada na Auditoria."
                               % len(selecionados)):
        return
    for iid in selecionados:
        reg = buscar_registro(iid)
        if reg is None:
            continue
        resumo = "%s | %s | Entrada: %s | Saída: %s" % (reg["Nome"], reg["Tipo"], reg["Entrada"], reg["Saida"] or "—")
        registrar_auditoria("EXCLUSÃO", reg["Id"], reg["Nome"], "Registro completo", resumo, "—")
        registros.remove(reg)
    salvar_registros()
    atualizar_tabela()


# ----------------------------------------------------------------------
# Edição direta na tabela (duplo clique)
# ----------------------------------------------------------------------
def iniciar_edicao(evento):
    if tabela.identify_region(evento.x, evento.y) != "cell":
        return
    iid = tabela.identify_row(evento.y)
    coluna = tabela.identify_column(evento.x)
    reg = buscar_registro(iid) if iid else None
    if reg is None:
        return
    campo = COLUNAS[int(coluna[1:]) - 1]

    if campo == "Saida" and not reg["Saida"]:
        if not exigir("saida"):
            return
    elif not exigir("editar", "Seu cargo só pode preencher a saída de registros que ainda não têm saída."):
        return

    if campo == "Nome":
        editar_texto(iid, coluna, reg)
    elif campo == "Tipo":
        menu = tk.Menu(janela, tearoff=0)
        for tipo in TIPOS_ACESSO + tipos_temporarios_ativos():
            rotulo = tipo + " *" if eh_temporario(tipo) else tipo
            menu.add_command(label=rotulo, command=lambda t=tipo: aplicar_edicao(reg, "Tipo", t))
        menu.add_separator()
        menu.add_command(label=OPCAO_NOVO, command=lambda: editar_para_temporario(reg))
        menu.tk_popup(evento.x_root, evento.y_root)
        menu.grab_release()
    else:
        editar_data_hora(reg, campo, (evento.x_root, evento.y_root))


def editar_texto(iid, coluna, reg):
    caixa = tabela.bbox(iid, coluna)
    if not caixa:
        return
    x, y, largura, altura = caixa
    editor = tk.Entry(tabela, font=("Segoe UI", 10))
    editor.place(x=x, y=y, width=largura, height=altura)
    editor.insert(0, reg["Nome"])
    editor.select_range(0, tk.END)
    editor.focus_set()
    estado = {"fim": False}

    def confirmar(_e=None):
        if estado["fim"]:
            return "break"
        estado["fim"] = True
        novo = editor.get().strip()
        editor.destroy()
        if novo == "":
            messagebox.showwarning("Atenção", "O nome não pode ficar vazio.")
        else:
            aplicar_edicao(reg, "Nome", novo)
        return "break"

    def cancelar(_e=None):
        if not estado["fim"]:
            estado["fim"] = True
            editor.destroy()
        return "break"

    editor.bind("<Return>", confirmar)
    editor.bind("<Escape>", cancelar)
    editor.bind("<FocusOut>", confirmar)


def editar_data_hora(reg, campo, posicao):
    """Abre o calendário e depois o relógio para alterar Entrada ou Saída."""
    atual = converter_data_hora(reg[campo]) if reg[campo] else None
    base = atual or datetime.now()

    seletor_data = SeletorData(janela, base.date(), posicao, permitir_limpar=(campo == "Saida"))
    if seletor_data.resultado is None:
        return                                   # cancelado
    if seletor_data.resultado == "":
        novo = ""                                # só a saída pode ser limpa
    else:
        seletor_hora = SeletorHora(janela, base, posicao)
        if seletor_hora.resultado is None:
            return
        novo = "%s %s" % (seletor_data.resultado.strftime(FORMATO_DATA), seletor_hora.resultado)

    if campo == "Entrada":
        erro = validar_ordem(novo, reg["Saida"])
    else:
        erro = validar_ordem(reg["Entrada"], novo)
    if erro:
        messagebox.showwarning("Atenção", erro)
        return
    aplicar_edicao(reg, campo, novo)


# ----------------------------------------------------------------------
# Página: Registro de auditoria (edições e exclusões)
# ----------------------------------------------------------------------
tabela_aud = None
var_filtro_aud = None
lbl_detalhe_aud = None
lbl_cont_aud = None


def construir_pagina_auditoria(pai):
    global tabela_aud, var_filtro_aud, lbl_detalhe_aud, lbl_cont_aud
    pagina = tk.Frame(pai, bg=COR_FUNDO)

    tk.Label(pagina, text="Edições mostram o valor anterior. Exclusões guardam o registro completo.",
             font=("Segoe UI", 10), fg=COR_TITULO, bg=COR_FUNDO).pack(anchor="w", padx=20, pady=(16, 0))

    barra = tk.Frame(pagina, bg=COR_FUNDO)
    barra.pack(fill="x", padx=20, pady=10)
    tk.Label(barra, text="Mostrar:", font=("Segoe UI", 10), bg=COR_FUNDO).pack(side="left")
    var_filtro_aud = tk.StringVar(value="Todos")
    filtro = ttk.Combobox(barra, textvariable=var_filtro_aud, state="readonly", width=12,
                          values=["Todos", "Edições", "Exclusões"])
    filtro.pack(side="left", padx=8)
    filtro.bind("<<ComboboxSelected>>", lambda _e: atualizar_auditoria())
    lbl_cont_aud = tk.Label(barra, font=("Segoe UI", 9), fg=COR_TEXTO_SUAVE, bg=COR_FUNDO)
    lbl_cont_aud.pack(side="right")

    area = tk.Frame(pagina, bg=COR_FUNDO)
    area.pack(fill="both", expand=True, padx=20)
    tabela_aud = ttk.Treeview(area, show="headings", selectmode="browse",
                              columns=("Quando", "Acao", "Usuario", "Nome", "Campo", "Anterior", "Novo"))
    larguras = {"Quando": 130, "Acao": 85, "Usuario": 100, "Nome": 105, "Campo": 105, "Anterior": 170, "Novo": 100}
    titulos = {"Quando": "Data/hora", "Acao": "Ação", "Usuario": "Responsável", "Nome": "Pessoa", "Campo": "Campo",
               "Anterior": "Valor anterior", "Novo": "Novo valor"}
    for col in titulos:
        tabela_aud.heading(col, text=titulos[col])
        tabela_aud.column(col, width=larguras[col], anchor="w")
    tabela_aud.tag_configure("edicao", background=COR_PENDENTE)
    tabela_aud.tag_configure("exclusao", background="#F2DCD3")
    rolagem = ttk.Scrollbar(area, orient="vertical", command=tabela_aud.yview)
    tabela_aud.configure(yscrollcommand=rolagem.set)
    tabela_aud.pack(side="left", fill="both", expand=True)
    rolagem.pack(side="right", fill="y")

    lbl_detalhe_aud = tk.Label(pagina, text="Selecione uma linha para ver os detalhes.",
                               font=("Segoe UI", 10), bg=COR_CARTAO, fg=COR_TITULO, anchor="w", justify="left",
                               wraplength=820, padx=10, pady=8,
                               highlightbackground=COR_BORDA, highlightthickness=1)
    lbl_detalhe_aud.pack(fill="x", padx=20, pady=12)

    def mostrar_detalhe(_e=None):
        sel = tabela_aud.selection()
        if not sel:
            return
        v = tabela_aud.item(sel[0], "values")
        lbl_detalhe_aud.config(text="%s em %s — %s (responsável: %s)\nCampo: %s\nValor anterior: %s\nNovo valor: %s"
                               % (v[1], v[0], v[3], v[2] or "—", v[4], v[5], v[6]))

    tabela_aud.bind("<<TreeviewSelect>>", mostrar_detalhe)
    return pagina


def atualizar_auditoria():
    if tabela_aud is None:
        return
    filtro = var_filtro_aud.get()
    for item in tabela_aud.get_children():
        tabela_aud.delete(item)
    mostrados = 0
    for ev in reversed(auditoria):                  # mais recentes primeiro
        if filtro == "Edições" and ev["Acao"] != "EDIÇÃO":
            continue
        if filtro == "Exclusões" and ev["Acao"] != "EXCLUSÃO":
            continue
        tag = "exclusao" if ev["Acao"] == "EXCLUSÃO" else "edicao"
        tabela_aud.insert("", "end", tags=(tag,),
                          values=(ev["Quando"], ev["Acao"], ev["Usuario"], ev["Nome"], ev["Campo"],
                                  ev["Anterior"], ev["Novo"]))
        mostrados += 1
    lbl_cont_aud.config(text="%d evento(s)" % mostrados)


# ----------------------------------------------------------------------
# Login, cargos e usuários (versão 4)
# ----------------------------------------------------------------------
ARQUIVO_USUARIOS = os.path.join(PASTA, "usuarios_portaria.json")

CARGO_FINAL = "Admin Final"
CARGO_ADM = "Adm"
CARGO_USUARIO = "Usuário"
CARGOS = [CARGO_FINAL, CARGO_ADM, CARGO_USUARIO]

# Permissões de cada cargo. Para mudar o que um cargo pode fazer, basta trocar True/False.
PERMISSOES = {
    CARGO_FINAL:   {"cadastrar": True, "saida": True, "editar": True,  "excluir": True,  "auditoria": True,  "usuarios": True},
    CARGO_ADM:     {"cadastrar": True, "saida": True, "editar": True,  "excluir": True,  "auditoria": True,  "usuarios": False},
    CARGO_USUARIO: {"cadastrar": True, "saida": True, "editar": False, "excluir": False, "auditoria": False, "usuarios": False},
}

MAX_TENTATIVAS = 5            # erros seguidos antes de bloquear a conta
MINUTOS_BLOQUEIO = 5
ITERACOES_SENHA = 200000      # custo do hash da senha (PBKDF2)
ITERACOES_PALAVRA = 50000     # custo do hash das palavras-chave
COR_TEAL = "#4F6B4A"

usuarios = []                 # lista de dicionários (ver criar_dados_usuario)
sessao = {"usuario": None}    # usuário que está logado


def pode(acao):
    """Retorna True se o cargo do usuário logado tem permissão para a ação."""
    u = sessao["usuario"]
    return bool(u and PERMISSOES.get(u["Cargo"], {}).get(acao))


def exigir(acao, mensagem=None):
    """Verificação de permissão: mostra aviso e retorna False se o cargo não pode."""
    if pode(acao):
        return True
    messagebox.showwarning("Acesso negado", mensagem or "Seu cargo não tem permissão para esta ação.")
    return False


def nome_sessao():
    u = sessao["usuario"]
    return u["NomeExibicao"] if u else ""


# ----------------------------------------------------------------------
# Validações (CPF, e-mail, senha, palavras-chave)
# ----------------------------------------------------------------------
def so_digitos(texto):
    return re.sub(r"\D", "", texto)


def cpf_valido(cpf):
    """Validador de CPF: 11 dígitos, não repetidos, e os 2 dígitos verificadores corretos."""
    d = so_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def formatar_cpf(texto):
    d = so_digitos(texto)[:11]
    resultado = ".".join(p for p in (d[0:3], d[3:6], d[6:9]) if p)
    if len(d) > 9:
        resultado += "-" + d[9:]
    return resultado


def mascarar_cpf(d):
    return "***.***.%s-%s" % (d[6:9], d[9:11]) if len(d) == 11 else "—"


def email_valido(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$", email) is not None


def erro_senha(senha):
    if len(senha) < 8 or not re.search(r"[A-Za-zÀ-ÿ]", senha) or not re.search(r"\d", senha):
        return "A senha deve ter pelo menos 8 caracteres, com letras e números."
    return None


# ----------------------------------------------------------------------
# Hash de senhas e palavras-chave (a senha nunca é guardada em texto puro)
# ----------------------------------------------------------------------
def hash_texto(texto, salt_hex, iteracoes):
    return hashlib.pbkdf2_hmac("sha256", texto.encode("utf-8"), bytes.fromhex(salt_hex), iteracoes).hex()


def criar_hash(texto, iteracoes):
    salt = secrets.token_hex(16)
    return salt, hash_texto(texto, salt, iteracoes)


def conferir_hash(texto, salt_hex, hash_guardado, iteracoes):
    return hmac.compare_digest(hash_texto(texto, salt_hex, iteracoes), hash_guardado)


# ----------------------------------------------------------------------
# Opções parecidas com a palavra-chave (para a recuperação de senha)
# ----------------------------------------------------------------------
PALAVRAS_BASE = """
gato pato rato mato fato lato cavalo cabelo castelo camelo cachorro macaco tigre zebra vaca lobo ovelha abelha
coelho joelho vermelho pássaro peixe peito leite leito feito jeito sapo sapato prato prata plano plana pedra
padre perna pessoa fogo fogão jogo logo lago lado mata meta mesa mola mala bala bola sala sola cola copa copo
corpo porto perto porta forte morte norte corte sorte parte carta casa cama cara caro cana capa cada nada roda
rosa rota nuvem chuva luva uva vela vila fila fina fita vida mundo mudo muro maro mapa mala malha palha folha
fralda falda saia seia areia aldeia ideia janela panela tigela cadeira madeira bandeira fronteira ladeira
biscoito mosquito morcego caderno inverno interno eterno verão verde verme verso versão pente dente gente
mente ponte fonte monte morro corro curso curto cinto cinco cisne sino pino fino lixo luxo bicho nicho
carro barro garra jarra farra terra serra guerra perra livro livre litro letra lenha linha limão leão
amor humor dor cor flor sol mel fel mar par luz cruz paz voz nós foz faz feliz raiz juiz giz cais
mesa meta pesa peso passo pássaro paço palco palma calma calça calor valor favor sabor saber sabão
sabor pomar pomba bomba tomba tinta tenta ponta conta canto santo manto tanto quanto
estrela estrelas escola escova esposa espada espelho espeto estudo estudar
tempo tempero templo tropa trovão troco troca trilha trilho trigo trabalho tapete tapeçaria
cidade verdade vontade saudade amizade bondade liberdade beleza certeza tristeza riqueza pobreza
chave chaves clave cravo craque cravos prova pronto ponto pinto
boneca boneco banana bananas barraca barriga barbeiro caneca canoa cenoura cebola
manga mango mesa gaveta garrafa garfo faca foca fica faixa baixa caixa peixe queixa
rádio radio ração razão rasgo rastro rastelo pastel pastor pastora motor moto moda modo molho
tigre trigo trapo trato trato tratado quadro quarto quarta quatro
cheiro cheio chefe cheque chuva chama chave chato chapéu chão
navio nariz nuvem ninho ninhos nome nota noite noiva noivo
orelha ouvido ouro osso ovo olho óculos ombro onda
praia prazo preço pressa prego prego premio prêmio praça
relógio remédio revista rio rua ruído rumo rápido
sapato segredo semana sempre senha sorriso soldado sonho sombra
tambor tarde teatro telhado tesoura tijolo timão tomate torre
vaso vento verão viagem vidro vizinho vulcão
zebra zero zona zelo
""".split()


def variar_palavra(p):
    """Gera uma variação de escrita da palavra (troca de letra, transposição etc.)."""
    letras = list(p)
    tipo = random.choice(["vogal", "consoante", "transpor", "duplicar", "remover", "sufixo"])
    vogais = "aeiou"
    if tipo == "vogal":
        idx = [i for i, c in enumerate(letras) if c in vogais]
        if idx:
            i = random.choice(idx)
            letras[i] = random.choice([v for v in vogais if v != letras[i]])
    elif tipo == "consoante":
        grupos = ["bpd", "cgqs", "mn", "tdf", "lr", "zsx", "vfb", "jgh"]
        idx = [i for i, c in enumerate(letras) if any(c in g for g in grupos)]
        if idx:
            i = random.choice(idx)
            g = next(g for g in grupos if letras[i] in g)
            letras[i] = random.choice([c for c in g if c != letras[i]])
    elif tipo == "transpor" and len(letras) > 3:
        i = random.randrange(len(letras) - 1)
        letras[i], letras[i + 1] = letras[i + 1], letras[i]
    elif tipo == "duplicar":
        i = random.randrange(len(letras))
        letras.insert(i, letras[i])
    elif tipo == "remover" and len(letras) > 4:
        del letras[random.randrange(len(letras))]
    else:
        return p + random.choice(["s", "a", "o", "e"])
    return "".join(letras)


def gerar_semelhantes(palavra, quantidade=3):
    """Devolve palavras com escrita parecida com a escolhida (para servirem de alternativas A-D)."""
    alvo = normalizar(palavra)
    escolhidas, vistos = [], {alvo}

    # 1) palavras reais parecidas, do dicionário embutido
    pontuadas = []
    for cand in set(PALAVRAS_BASE):
        n = normalizar(cand)
        if n in vistos or abs(len(n) - len(alvo)) > 2:
            continue
        r = difflib.SequenceMatcher(None, alvo, n).ratio()
        if r >= 0.5:
            pontuadas.append((r, cand))
    pontuadas.sort(reverse=True)
    melhores = pontuadas[:8]
    random.shuffle(melhores)
    for _r, cand in melhores:
        if len(escolhidas) == quantidade:
            break
        escolhidas.append(cand)
        vistos.add(normalizar(cand))

    # 2) variações de escrita, se faltou
    tentativas = 0
    while len(escolhidas) < quantidade and tentativas < 300:
        tentativas += 1
        var = variar_palavra(alvo)
        n = normalizar(var)
        if n in vistos or len(n) < 2:
            continue
        escolhidas.append(var)
        vistos.add(n)
    return escolhidas


# ----------------------------------------------------------------------
# Arquivo de usuários
# ----------------------------------------------------------------------
def carregar_usuarios():
    """Lê usuarios_portaria.json. Retorna False se o arquivo existir mas estiver ilegível."""
    if not os.path.exists(ARQUIVO_USUARIOS):
        return True
    try:
        with open(ARQUIVO_USUARIOS, encoding="utf-8") as f:
            dados = json.load(f)
        if not isinstance(dados, list):
            raise ValueError("formato inesperado")
        usuarios.extend(dados)
        return True
    except (OSError, ValueError):
        messagebox.showerror("Erro", "Não foi possível ler o arquivo de usuários (usuarios_portaria.json).\n"
                                     "Ele não foi alterado. Verifique o arquivo ou restaure uma cópia.")
        return False


def salvar_usuarios():
    try:
        with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as f:
            json.dump(usuarios, f, ensure_ascii=False, indent=2)
    except OSError:
        messagebox.showerror("Erro", "Não foi possível salvar o arquivo de usuários.")


def achar_usuario_por_login(texto):
    """Login por e-mail ou por CPF."""
    t = texto.strip()
    if "@" in t:
        return next((u for u in usuarios if u["Email"].lower() == t.lower()), None)
    d = so_digitos(t)
    return next((u for u in usuarios if d and u["CPF"] == d), None)


def achar_usuario_por_cpf(cpf):
    d = so_digitos(cpf)
    return next((u for u in usuarios if d and u["CPF"] == d), None)


def achar_usuario_por_id(id_usuario):
    return next((u for u in usuarios if u["Id"] == id_usuario), None)


def minutos_bloqueio_restantes(u):
    if not u.get("BloqueadoAte"):
        return 0
    try:
        ate = datetime.strptime(u["BloqueadoAte"], FORMATO_CRIACAO)
    except ValueError:
        return 0
    segundos = (ate - datetime.now()).total_seconds()
    return int(math.ceil(segundos / 60)) if segundos > 0 else 0


def registrar_falha(u):
    """Conta um erro de acesso; após MAX_TENTATIVAS a conta fica bloqueada por alguns minutos."""
    u["Tentativas"] = u.get("Tentativas", 0) + 1
    if u["Tentativas"] >= MAX_TENTATIVAS:
        u["Tentativas"] = 0
        u["BloqueadoAte"] = (datetime.now() + timedelta(minutes=MINUTOS_BLOQUEIO)).strftime(FORMATO_CRIACAO)
    salvar_usuarios()


def limpar_falhas(u):
    u["Tentativas"] = 0
    u["BloqueadoAte"] = ""
    salvar_usuarios()


def avisar_bloqueio(u, pai=None):
    messagebox.showwarning("Conta bloqueada",
                           "Muitas tentativas incorretas. Tente novamente em %d minuto(s)." % minutos_bloqueio_restantes(u),
                           parent=pai or janela)


def montar_usuario(nome, exibicao, email, cpf, cargo, senha, palavras):
    """Cria o dicionário do usuário já com senha e palavras-chave protegidas por hash."""
    salt, h = criar_hash(senha, ITERACOES_SENHA)
    lista_palavras = []
    for p in palavras:
        opcoes = [p] + gerar_semelhantes(p)
        while len(opcoes) < 4:                       # garantia: sempre 4 alternativas (A-D)
            extra = p + random.choice("aeos")
            if normalizar(extra) not in [normalizar(o) for o in opcoes]:
                opcoes.append(extra)
        random.shuffle(opcoes)
        s, hp = criar_hash(normalizar(p), ITERACOES_PALAVRA)
        lista_palavras.append({"Opcoes": opcoes, "Salt": s, "Hash": hp})
    return {
        "Id": novo_id(), "NomeCompleto": nome, "NomeExibicao": exibicao, "Email": email, "CPF": cpf,
        "Cargo": cargo, "SenhaSalt": salt, "SenhaHash": h, "Palavras": lista_palavras,
        "Tentativas": 0, "BloqueadoAte": "", "CriadoEm": datetime.now().strftime(FORMATO_CRIACAO),
    }


# ----------------------------------------------------------------------
# Formulário de cadastro de usuário (inline, dentro da própria janela)
# ----------------------------------------------------------------------
COR_MENU = "#4A5A3E"            # fundo do painel lateral e da barra de título
COR_MENU_BTN = "#5E7050"        # botões do painel lateral
COR_MENU_BORDA = "#EDE6CB"      # borda creme dos botões do painel
COR_MENU_ATIVO = "#EDE6CB"      # item da página aberta
COR_MENU_HOVER = "#71855F"


class FormularioUsuario(tk.Frame):
    """Formulário de cadastro. Chama ao_concluir(usuario) depois de salvar."""

    def __init__(self, pai, titulo, cargo_fixo=None, ao_concluir=None, ao_cancelar=None, texto_cancelar="Cancelar"):
        super().__init__(pai, bg=COR_CARTAO, padx=24, pady=12)
        self.cargo_fixo = cargo_fixo
        self.ao_concluir = ao_concluir
        self.columnconfigure((0, 1), weight=1, uniform="c")

        tk.Label(self, text=titulo, font=("Segoe UI", 14, "bold"), bg=COR_CARTAO, fg=COR_TITULO).grid(
            row=0, column=0, columnspan=2, sticky="w")
        tk.Label(self, text="Todos os campos são obrigatórios.", font=("Segoe UI", 9), bg=COR_CARTAO,
                 fg=COR_TEXTO_SUAVE).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))

        _l, self.e_nome = self.campo("Nome completo:", 2, 0, 2)
        _l, self.e_exibicao = self.campo("Nome para exibição:", 4, 0)
        _l, self.e_email = self.campo("E-mail:", 4, 1)
        self.l_cpf, self.e_cpf = self.campo("CPF:", 6, 0)
        self.e_cpf.bind("<KeyRelease>", self.ao_digitar_cpf)

        if cargo_fixo:
            tk.Label(self, text="Cargo: " + cargo_fixo, font=("Segoe UI", 10, "bold"), bg=COR_CARTAO,
                     fg=COR_TITULO).grid(row=7, column=1, sticky="w", padx=6)
        else:
            tk.Label(self, text="Cargo:", font=("Segoe UI", 10), bg=COR_CARTAO).grid(row=6, column=1, sticky="w", padx=6)
            self.var_cargo = tk.StringVar(value=CARGO_ADM)
            ttk.Combobox(self, textvariable=self.var_cargo, values=[CARGO_ADM, CARGO_USUARIO],
                         state="readonly", font=("Segoe UI", 11)).grid(row=7, column=1, sticky="ew", padx=6, pady=(2, 6))

        _l, self.e_senha = self.campo("Senha:", 8, 0, show="•")
        _l, self.e_conf = self.campo("Confirmação da senha:", 8, 1, show="•")
        self.var_mostrar = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text="Mostrar senhas", variable=self.var_mostrar, bg=COR_CARTAO, activebackground=COR_CARTAO,
                       command=self.alternar_senha).grid(row=10, column=0, columnspan=2, sticky="w", padx=2)

        tk.Label(self, text="Palavras-chave de recuperação (3)", font=("Segoe UI", 10, "bold"), bg=COR_CARTAO,
                 fg=COR_TITULO).grid(row=11, column=0, columnspan=2, sticky="w", pady=(8, 0))
        tk.Label(self, text="Escolha 3 palavras diferentes (só letras, mín. 4). Se esquecer a senha, você terá de "
                            "reconhecê-las entre alternativas parecidas.",
                 font=("Segoe UI", 9), bg=COR_CARTAO, fg=COR_TEXTO_SUAVE, wraplength=520, justify="left").grid(
            row=12, column=0, columnspan=2, sticky="w")
        linha_palavras = tk.Frame(self, bg=COR_CARTAO)
        linha_palavras.grid(row=13, column=0, columnspan=2, sticky="ew")
        linha_palavras.columnconfigure((0, 1, 2), weight=1, uniform="p")
        self.e_palavras = []
        for i in range(3):
            tk.Label(linha_palavras, text="Palavra-chave %d:" % (i + 1), font=("Segoe UI", 10),
                     bg=COR_CARTAO).grid(row=0, column=i, sticky="w", padx=6)
            e = tk.Entry(linha_palavras, font=("Segoe UI", 11))
            e.grid(row=1, column=i, sticky="ew", padx=6, pady=(2, 6), ipady=3)
            self.e_palavras.append(e)

        botoes = tk.Frame(self, bg=COR_CARTAO)
        botoes.grid(row=14, column=0, columnspan=2, sticky="e", pady=(10, 0))
        if ao_cancelar:
            Botao(botoes, text=texto_cancelar, bg=COR_NEUTRO, bd=0, padx=14, pady=6, cursor="hand2",
                      command=ao_cancelar).pack(side="left", padx=6)
        Botao(botoes, text="Salvar cadastro", bg=COR_VERDE, fg="white", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 10, "bold"), cursor="hand2", command=self.salvar).pack(side="left")

    def campo(self, rotulo, linha, coluna, colspan=1, show=None):
        etiqueta = tk.Label(self, text=rotulo, font=("Segoe UI", 10), bg=COR_CARTAO)
        etiqueta.grid(row=linha, column=coluna, columnspan=colspan, sticky="w", padx=6)
        entrada = tk.Entry(self, font=("Segoe UI", 11), show=show) if show else tk.Entry(self, font=("Segoe UI", 11))
        entrada.grid(row=linha + 1, column=coluna, columnspan=colspan, sticky="ew", padx=6, pady=(2, 6), ipady=3)
        return etiqueta, entrada

    def alternar_senha(self):
        simbolo = "" if self.var_mostrar.get() else "•"
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
            self.l_cpf.config(text="CPF:  ✔ válido" if ok else "CPF:  ✖ inválido", fg=COR_VERDE if ok else COR_VERMELHO)
        else:
            self.l_cpf.config(text="CPF:", fg=COR_TITULO)

    def avisar(self, mensagem):
        messagebox.showwarning("Atenção", mensagem)

    def salvar(self):
        nome = " ".join(self.e_nome.get().split())
        exibicao = " ".join(self.e_exibicao.get().split())
        email = self.e_email.get().strip().lower()
        cpf = so_digitos(self.e_cpf.get())
        senha, confirmacao = self.e_senha.get(), self.e_conf.get()
        palavras = [e.get().strip().lower() for e in self.e_palavras]
        cargo = self.cargo_fixo or self.var_cargo.get()

        if len(nome.split()) < 2:
            return self.avisar("Informe o nome completo (nome e sobrenome).")
        if exibicao == "" or len(exibicao) > 25:
            return self.avisar("Informe o nome para exibição (até 25 caracteres).")
        if not email_valido(email):
            return self.avisar("E-mail inválido.")
        if any(u["Email"].lower() == email for u in usuarios):
            return self.avisar("Este e-mail já está cadastrado.")
        if not cpf_valido(cpf):
            return self.avisar("CPF inválido. Confira os números digitados.")
        if any(u["CPF"] == cpf for u in usuarios):
            return self.avisar("Este CPF já está cadastrado.")
        if cargo not in CARGOS:
            return self.avisar("Cargo inválido.")
        erro = erro_senha(senha)
        if erro:
            return self.avisar(erro)
        if senha != confirmacao:
            return self.avisar("A confirmação da senha não confere.")
        for p in palavras:
            if re.match(r"^[a-zà-ÿ]{4,20}$", p) is None:
                return self.avisar("Cada palavra-chave deve ter só letras (de 4 a 20), sem espaços.")
        if len({normalizar(p) for p in palavras}) < 3:
            return self.avisar("As 3 palavras-chave precisam ser diferentes entre si.")

        novo = montar_usuario(nome, exibicao, email, cpf, cargo, senha, palavras)
        usuarios.append(novo)
        salvar_usuarios()
        if self.ao_concluir:
            self.ao_concluir(novo)


# ----------------------------------------------------------------------
# Recuperação de senha (inline): CPF + e-mail digitado + 3 palavras-chave (alternativas A-D)
# ----------------------------------------------------------------------
class RecuperarSenha(tk.Frame):
    def __init__(self, pai, ao_voltar):
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
        tk.Label(self.corpo, text=texto, font=("Segoe UI", 14, "bold"), bg=COR_CARTAO, fg=COR_TITULO).pack(anchor="w")
        tk.Label(self.corpo, text=subtitulo, font=("Segoe UI", 9), bg=COR_CARTAO, fg=COR_TEXTO_SUAVE,
                 wraplength=400, justify="left").pack(anchor="w", pady=(0, 10))

    def botoes(self, texto_ok, comando):
        barra = tk.Frame(self.corpo, bg=COR_CARTAO)
        barra.pack(anchor="e", pady=(12, 0))
        Botao(barra, text="← Voltar ao login", bg=COR_NEUTRO, bd=0, padx=14, pady=6, cursor="hand2",
                  command=self.ao_voltar).pack(side="left", padx=6)
        Botao(barra, text=texto_ok, bg=COR_AZUL, fg="white", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 10, "bold"), cursor="hand2", command=comando).pack(side="left")

    def avisar(self, mensagem):
        messagebox.showwarning("Atenção", mensagem)

    # --- passo 1: CPF e e-mail ------------------------------------------
    def passo_dados(self):
        self.limpar_corpo()
        self.titulo("Recuperar senha", "Passo 1 de 3 — confirme seus dados. Digite o CPF e o e-mail cadastrados.")
        tk.Label(self.corpo, text="CPF:", bg=COR_CARTAO, font=("Segoe UI", 10)).pack(anchor="w")
        self.e_cpf = tk.Entry(self.corpo, font=("Segoe UI", 11), width=34)
        self.e_cpf.pack(pady=(2, 8), ipady=3)
        self.e_cpf.bind("<KeyRelease>", self.formatar)
        tk.Label(self.corpo, text="E-mail:", bg=COR_CARTAO, font=("Segoe UI", 10)).pack(anchor="w")
        self.e_email = tk.Entry(self.corpo, font=("Segoe UI", 11), width=34)
        self.e_email.pack(pady=(2, 0), ipady=3)
        self.botoes("Continuar", self.verificar_dados)
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
        u = achar_usuario_por_cpf(cpf)
        if u is not None and minutos_bloqueio_restantes(u):
            return avisar_bloqueio(u, self)
        if u is None or u["Email"].lower() != email:
            if u is not None:
                registrar_falha(u)
            return self.avisar("Os dados informados não conferem.")
        self.usuario = u
        self.passo_palavras()

    # --- passo 2: palavras-chave ----------------------------------------
    def passo_palavras(self):
        self.limpar_corpo()
        self.titulo("Palavras-chave", "Passo 2 de 3 — para cada pergunta, selecione a palavra que você cadastrou.")
        self.variaveis, self.ordem = [], []
        for i, p in enumerate(self.usuario["Palavras"]):
            opcoes = list(p["Opcoes"])
            random.shuffle(opcoes)
            self.ordem.append(opcoes)
            moldura = tk.LabelFrame(self.corpo, text="Pergunta %d: qual é a sua palavra-chave nº %d?" % (i + 1, i + 1),
                                    bg=COR_CARTAO, padx=10, pady=6, font=("Segoe UI", 9, "bold"))
            moldura.pack(fill="x", pady=4)
            var = tk.IntVar(value=-1)
            self.variaveis.append(var)
            for j, op in enumerate(opcoes):
                tk.Radiobutton(moldura, text="%s) %s" % ("ABCD"[j], op), variable=var, value=j, bg=COR_CARTAO,
                               activebackground=COR_CARTAO, anchor="w", width=20, font=("Segoe UI", 10)).grid(
                    row=j // 2, column=j % 2, sticky="w", padx=6)
        self.botoes("Verificar", self.verificar_palavras)

    def verificar_palavras(self):
        if any(v.get() < 0 for v in self.variaveis):
            return self.avisar("Responda as 3 perguntas.")
        certas = [conferir_hash(normalizar(self.ordem[i][v.get()]), p["Salt"], p["Hash"], ITERACOES_PALAVRA)
                  for i, (v, p) in enumerate(zip(self.variaveis, self.usuario["Palavras"]))]
        if not all(certas):
            registrar_falha(self.usuario)
            messagebox.showerror("Recuperação negada", "As palavras-chave não conferem.\n"
                                                       "Por segurança, a recuperação foi encerrada.")
            self.ao_voltar()
            return
        self.passo_nova_senha()

    # --- passo 3: nova senha --------------------------------------------
    def passo_nova_senha(self):
        self.limpar_corpo()
        self.titulo("Nova senha", "Passo 3 de 3 — defina a nova senha (mín. 8 caracteres, com letras e números).")
        tk.Label(self.corpo, text="Nova senha:", bg=COR_CARTAO, font=("Segoe UI", 10)).pack(anchor="w")
        self.e_nova = tk.Entry(self.corpo, font=("Segoe UI", 11), width=34, show="•")
        self.e_nova.pack(pady=(2, 8), ipady=3)
        tk.Label(self.corpo, text="Confirmação da nova senha:", bg=COR_CARTAO, font=("Segoe UI", 10)).pack(anchor="w")
        self.e_conf = tk.Entry(self.corpo, font=("Segoe UI", 11), width=34, show="•")
        self.e_conf.pack(pady=(2, 0), ipady=3)
        self.botoes("Salvar nova senha", self.salvar_nova)
        self.e_nova.focus_set()

    def salvar_nova(self):
        nova, conf = self.e_nova.get(), self.e_conf.get()
        erro = erro_senha(nova)
        if erro:
            return self.avisar(erro)
        if nova != conf:
            return self.avisar("A confirmação da senha não confere.")
        self.usuario["SenhaSalt"], self.usuario["SenhaHash"] = criar_hash(nova, ITERACOES_SENHA)
        limpar_falhas(self.usuario)
        messagebox.showinfo("Senha redefinida", "Senha alterada com sucesso! Faça login com a nova senha.")
        self.ao_voltar()


# ----------------------------------------------------------------------
# Tela de login (tudo na mesma janela: login, primeiro acesso e recuperação)
# ----------------------------------------------------------------------
entrada_login = None
entrada_senha = None
var_login_cargo = None
var_ver_senha = None


def limpar_area_login():
    for w in area_login.winfo_children():
        w.destroy()


def cabecalho_login(grande=True):
    if grande:
        tk.Label(area_login, text="🏠", font=("Segoe UI Emoji", 32), bg=COR_CARTAO).pack()
    tk.Label(area_login, text="Cadastro de Portaria", font=("Segoe UI", 18 if grande else 14, "bold"),
             bg=COR_CARTAO, fg=COR_TITULO).pack()
    tk.Label(area_login, text="Controle de entrada e saída", font=("Segoe UI", 10), bg=COR_CARTAO,
             fg=COR_TEXTO_SUAVE).pack()


def montar_login():
    global entrada_login, entrada_senha, var_login_cargo, var_ver_senha
    limpar_area_login()
    if not usuarios:                       # ainda não existe nenhum usuário: primeiro acesso
        montar_setup()
        return
    cabecalho_login()
    form = tk.Frame(area_login, bg=COR_CARTAO)
    form.pack(pady=(14, 0))
    tk.Label(form, text="Entrar como:", font=("Segoe UI", 10), bg=COR_CARTAO).pack(anchor="w")
    var_login_cargo = tk.StringVar(value=CARGO_FINAL)
    ttk.Combobox(form, textvariable=var_login_cargo, values=CARGOS, state="readonly",
                 font=("Segoe UI", 11), width=32).pack(fill="x", pady=(2, 10), ipady=2)
    tk.Label(form, text="E-mail ou CPF:", font=("Segoe UI", 10), bg=COR_CARTAO).pack(anchor="w")
    entrada_login = tk.Entry(form, font=("Segoe UI", 11), width=34)
    entrada_login.pack(fill="x", pady=(2, 10), ipady=3)
    tk.Label(form, text="Senha:", font=("Segoe UI", 10), bg=COR_CARTAO).pack(anchor="w")
    entrada_senha = tk.Entry(form, font=("Segoe UI", 11), width=34, show="•")
    entrada_senha.pack(fill="x", pady=(2, 4), ipady=3)
    var_ver_senha = tk.BooleanVar(value=False)
    tk.Checkbutton(form, text="Mostrar senha", variable=var_ver_senha, bg=COR_CARTAO, activebackground=COR_CARTAO,
                   command=lambda: entrada_senha.config(show="" if var_ver_senha.get() else "•")).pack(anchor="w")
    Botao(form, text="Entrar", bg=COR_VERDE, fg="white", activebackground="#17724A", activeforeground="white",
              font=("Segoe UI", 11, "bold"), bd=0, pady=8, cursor="hand2", command=entrar).pack(fill="x", pady=(10, 6))
    Botao(form, text="Esqueci minha senha", fg=COR_AZUL, bg=COR_CARTAO, borda="", raio=8, bd=0,
              font=("Segoe UI", 9, "underline"), cursor="hand2", command=montar_recuperacao).pack()
    entrada_login.bind("<Return>", lambda _e: entrada_senha.focus_set())
    entrada_senha.bind("<Return>", lambda _e: entrar())
    entrada_login.focus_set()


def montar_setup():
    """Primeiro acesso: cadastro do Admin Final (dono do sistema)."""
    limpar_area_login()
    cabecalho_login(grande=False)
    tk.Label(area_login, text="Primeiro acesso — cadastre o Admin Final para começar.", font=("Segoe UI", 10, "bold"),
             bg=COR_CARTAO, fg=COR_AZUL).pack(pady=(6, 0))
    FormularioUsuario(area_login, "Cadastro do Admin Final", cargo_fixo=CARGO_FINAL,
                      ao_concluir=fim_setup).pack()


def fim_setup(_usuario):
    messagebox.showinfo("Admin Final cadastrado",
                        "Cadastro concluído! Entre com o cargo Admin Final, usando seu e-mail ou CPF e a senha.")
    montar_login()


def montar_recuperacao():
    limpar_area_login()
    cabecalho_login(grande=False)
    RecuperarSenha(area_login, montar_login).pack(pady=(8, 0))


def entrar():
    cargo = var_login_cargo.get()
    login = entrada_login.get()
    senha = entrada_senha.get()
    if not login.strip() or not senha:
        messagebox.showwarning("Atenção", "Informe o e-mail (ou CPF) e a senha.")
        return
    u = achar_usuario_por_login(login)
    if u is not None and minutos_bloqueio_restantes(u):
        return avisar_bloqueio(u)
    if u is None or u["Cargo"] != cargo or not conferir_hash(senha, u["SenhaSalt"], u["SenhaHash"], ITERACOES_SENHA):
        if u is not None:
            registrar_falha(u)
        messagebox.showerror("Acesso negado", "E-mail/CPF, senha ou cargo incorretos.")
        return
    limpar_falhas(u)
    sessao["usuario"] = u
    entrada_senha.delete(0, tk.END)
    mostrar_app()


def sair():
    sessao["usuario"] = None
    mostrar_login()


def mostrar_login():
    app.pack_forget()
    janela.title("Cadastro de Portaria - Login")
    login_frame.pack(fill="both", expand=True)
    montar_login()


# ----------------------------------------------------------------------
# Painel lateral (pode ser ocultado) e navegação entre páginas
# ----------------------------------------------------------------------
# (chave, texto do menu, título da página, permissão exigida)
PAGINAS = [
    ("portaria", "🏠  Portaria", "Portaria — controle de entrada e saída", None),
    ("usuarios", "👥  Usuários", "Usuários do sistema", "usuarios"),
    ("auditoria", "📋  Registro de auditoria", "Registro de auditoria", "auditoria"),
    ("novo", "➕  Cadastro de novos administradores", "Cadastro de novos administradores", "usuarios"),
]
estado_menu = {"visivel": True, "pagina": "portaria", "botoes": {}}


def montar_menu():
    """Cria os itens do painel lateral que o cargo do usuário logado pode acessar."""
    for w in menu_itens.winfo_children():
        w.destroy()
    estado_menu["botoes"] = {}
    for chave, rotulo, _titulo, acao in PAGINAS:
        if acao and not pode(acao):
            continue
        b = Botao(menu_itens, text=rotulo, anchor="w", justify="left", wraplength=190,
                      font=("Segoe UI", 10, "bold"), fg="white", bg=COR_MENU_BTN, hover=COR_MENU_HOVER,
                      borda=COR_MENU_BORDA, raio=12, padx=14, pady=10, cursor="hand2",
                      command=lambda k=chave: ir_para(k))
        b.pack(fill="x", padx=8, pady=2)
        estado_menu["botoes"][chave] = b


def realcar_menu():
    for chave, botao in estado_menu["botoes"].items():
        ativo = chave == estado_menu["pagina"]
        botao.config(bg=COR_MENU_ATIVO if ativo else COR_MENU_BTN, fg=COR_TITULO if ativo else "white",
                     hover=COR_MENU_ATIVO if ativo else COR_MENU_HOVER)


def alternar_menu():
    """Mostra ou oculta o painel lateral (botão ☰)."""
    if estado_menu["visivel"]:
        sidebar.pack_forget()
        estado_menu["visivel"] = False
    else:
        sidebar.pack(side="left", fill="y", before=direita)
        estado_menu["visivel"] = True


def ir_para(nome):
    for chave, _rotulo, titulo, acao in PAGINAS:
        if chave == nome:
            if acao and not exigir(acao):
                return
            lbl_titulo_pagina.config(text=titulo)
            break
    for pagina in paginas.values():
        pagina.pack_forget()
    paginas[nome].pack(fill="both", expand=True)
    estado_menu["pagina"] = nome
    realcar_menu()
    if nome == "auditoria":
        atualizar_auditoria()
    elif nome == "usuarios":
        atualizar_usuarios()
    elif nome == "novo":
        reiniciar_formulario_novo()
    elif nome == "portaria":
        atualizar_tabela()


def aplicar_permissoes():
    """Habilita/desabilita os botões da portaria conforme o cargo do usuário logado."""
    regras = [(btn_cadastrar, "cadastrar", COR_VERDE), (btn_saida, "saida", COR_LARANJA),
              (btn_excluir, "excluir", COR_VERMELHO)]
    for botao, acao, cor in regras:
        if pode(acao):
            botao.config(state="normal", bg=cor, cursor="hand2")
        else:
            botao.config(state="disabled", bg="#B8C0CC", cursor="arrow")


def mostrar_app():
    login_frame.pack_forget()
    janela.title("Cadastro de Portaria")
    app.pack(fill="both", expand=True)
    if not estado_menu["visivel"]:
        alternar_menu()
    u = sessao["usuario"]
    lbl_usuario.config(text="👤 %s\n%s" % (u["NomeExibicao"], u["Cargo"]))
    montar_menu()
    aplicar_permissoes()
    limpar_filtro()
    limpar()
    ir_para("portaria")
    campo_nome.focus()


# ----------------------------------------------------------------------
# Página: Usuários (somente Admin Final)
# ----------------------------------------------------------------------
tabela_usr = None


def construir_pagina_usuarios(pai):
    global tabela_usr
    pagina = tk.Frame(pai, bg=COR_FUNDO)
    tk.Label(pagina, text="Veja os acessos, altere cargos (Adm ↔ Usuário), desbloqueie contas ou remova usuários.",
             font=("Segoe UI", 10), fg=COR_TITULO, bg=COR_FUNDO).pack(anchor="w", padx=20, pady=(16, 0))
    barra = tk.Frame(pagina, bg=COR_FUNDO)
    barra.pack(fill="x", padx=20, pady=10)
    estilo = dict(font=("Segoe UI", 10, "bold"), fg="white", bd=0, padx=12, pady=6, cursor="hand2")
    Botao(barra, text="➕  Novo administrador / usuário", bg=COR_VERDE,
              command=lambda: ir_para("novo"), **estilo).pack(side="left")
    Botao(barra, text="⇄  Alterar cargo", bg=COR_AZUL, command=alterar_cargo, **estilo).pack(side="left", padx=8)
    Botao(barra, text="🔓  Desbloquear", bg=COR_LARANJA, command=desbloquear_usuario, **estilo).pack(side="left")
    Botao(barra, text="✕  Excluir usuário", bg=COR_VERMELHO, command=excluir_usuario, **estilo).pack(side="right")

    area = tk.Frame(pagina, bg=COR_FUNDO)
    area.pack(fill="both", expand=True, padx=20, pady=(0, 16))
    colunas = ("Exibicao", "Completo", "Cargo", "Email", "CPF", "Status")
    tabela_usr = ttk.Treeview(area, columns=colunas, show="headings", selectmode="browse")
    titulos = {"Exibicao": "Nome de exibição", "Completo": "Nome completo", "Cargo": "Cargo",
               "Email": "E-mail", "CPF": "CPF", "Status": "Status"}
    larguras = {"Exibicao": 120, "Completo": 170, "Cargo": 80, "Email": 190, "CPF": 100, "Status": 110}
    for c in colunas:
        tabela_usr.heading(c, text=titulos[c])
        tabela_usr.column(c, width=larguras[c], anchor="w")
    rolagem = ttk.Scrollbar(area, orient="vertical", command=tabela_usr.yview)
    tabela_usr.configure(yscrollcommand=rolagem.set)
    tabela_usr.pack(side="left", fill="both", expand=True)
    rolagem.pack(side="right", fill="y")
    return pagina


def atualizar_usuarios():
    if tabela_usr is None:
        return
    for item in tabela_usr.get_children():
        tabela_usr.delete(item)
    for u in usuarios:
        restante = minutos_bloqueio_restantes(u)
        status = "Bloqueado (%d min)" % restante if restante else "Ativo"
        tabela_usr.insert("", "end", iid=u["Id"], values=(u["NomeExibicao"], u["NomeCompleto"], u["Cargo"],
                                                          u["Email"], mascarar_cpf(u["CPF"]), status))


def usuario_selecionado():
    sel = tabela_usr.selection()
    if not sel:
        messagebox.showwarning("Atenção", "Selecione um usuário na lista.")
        return None
    return achar_usuario_por_id(sel[0])


def alterar_cargo():
    if not exigir("usuarios"):
        return
    u = usuario_selecionado()
    if u is None:
        return
    if u["Cargo"] == CARGO_FINAL:
        messagebox.showwarning("Atenção", "O cargo do Admin Final não pode ser alterado.")
        return
    novo = CARGO_USUARIO if u["Cargo"] == CARGO_ADM else CARGO_ADM
    if messagebox.askyesno("Alterar cargo", "Alterar o cargo de %s de %s para %s?" % (u["NomeExibicao"], u["Cargo"], novo)):
        u["Cargo"] = novo
        salvar_usuarios()
        atualizar_usuarios()


def excluir_usuario():
    if not exigir("usuarios"):
        return
    u = usuario_selecionado()
    if u is None:
        return
    if u["Cargo"] == CARGO_FINAL:
        messagebox.showwarning("Atenção", "O Admin Final não pode ser excluído.")
        return
    if messagebox.askyesno("Excluir usuário", "Excluir o acesso de %s (%s)?" % (u["NomeExibicao"], u["Cargo"])):
        usuarios.remove(u)
        salvar_usuarios()
        atualizar_usuarios()


def desbloquear_usuario():
    if not exigir("usuarios"):
        return
    u = usuario_selecionado()
    if u is None:
        return
    limpar_falhas(u)
    atualizar_usuarios()


# ----------------------------------------------------------------------
# Página: Cadastro de novos administradores (somente Admin Final)
# ----------------------------------------------------------------------
moldura_novo = None


def construir_pagina_novo(pai):
    global moldura_novo
    pagina = tk.Frame(pai, bg=COR_FUNDO)
    tk.Label(pagina, text="Crie contas de Adm e de Usuário. Cada uma tem senha e 3 palavras-chave de recuperação próprias.",
             font=("Segoe UI", 10), fg=COR_TITULO, bg=COR_FUNDO).pack(anchor="w", padx=20, pady=(16, 0))
    moldura_novo = tk.Frame(pagina, bg=COR_FUNDO)
    moldura_novo.pack(pady=10)
    return pagina


def reiniciar_formulario_novo():
    """Mostra o formulário em branco."""
    for w in moldura_novo.winfo_children():
        w.destroy()
    FormularioUsuario(moldura_novo, "Novo administrador / usuário", ao_concluir=apos_cadastro_novo).pack()


def apos_cadastro_novo(u):
    messagebox.showinfo("Cadastro concluído", "%s (%s) foi cadastrado com sucesso." % (u["NomeExibicao"], u["Cargo"]))
    reiniciar_formulario_novo()


# ----------------------------------------------------------------------
# Barra de título no tema do aplicativo (minimizar, maximizar e fechar)
# ----------------------------------------------------------------------
EH_WINDOWS = sys.platform.startswith("win")
LARGURA_PADRAO, ALTURA_PADRAO = 1100, 720
LARGURA_MINIMA, ALTURA_MINIMA = 980, 640
estado_janela = {"maximizada": False, "geometria": None, "minimizado": False, "arraste": (0, 0)}
btn_maximizar = None
grip = None


def area_de_trabalho():
    """Área útil da tela (sem a barra de tarefas, no Windows)."""
    if EH_WINDOWS:
        try:
            import ctypes
            from ctypes import wintypes
            retangulo = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(retangulo), 0)
            return retangulo.left, retangulo.top, retangulo.right, retangulo.bottom
        except Exception:
            pass
    return 0, 0, janela.winfo_screenwidth(), janela.winfo_screenheight()


def garantir_icone_na_barra_de_tarefas():
    """No Windows, janelas sem moldura somem da barra de tarefas; isto traz o ícone de volta."""
    if not EH_WINDOWS:
        return
    try:
        import ctypes
        GWL_EXSTYLE, WS_EX_APPWINDOW, WS_EX_TOOLWINDOW = -20, 0x00040000, 0x00000080
        hwnd = ctypes.windll.user32.GetParent(janela.winfo_id())
        estilo = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        estilo = (estilo & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, estilo)
        janela.withdraw()
        janela.after(10, janela.deiconify)
    except Exception:
        pass


def minimizar():
    # janelas sem moldura não minimizam: devolvemos a moldura só durante a minimização
    estado_janela["minimizado"] = True
    janela.overrideredirect(False)
    janela.update_idletasks()
    janela.iconify()


def restaurar_moldura():
    janela.overrideredirect(True)
    garantir_icone_na_barra_de_tarefas()
    janela.after(150, janela.focus_force)


def ao_mapear(evento):
    if evento.widget is janela and estado_janela["minimizado"]:
        estado_janela["minimizado"] = False
        janela.after(10, restaurar_moldura)


def alternar_maximizar():
    if estado_janela["maximizada"]:
        janela.geometry(estado_janela["geometria"])
        estado_janela["maximizada"] = False
        btn_maximizar.config(text="▢")
        grip.place(relx=1.0, rely=1.0, anchor="se")
    else:
        estado_janela["geometria"] = janela.geometry()
        x1, y1, x2, y2 = area_de_trabalho()
        janela.geometry("%dx%d+%d+%d" % (x2 - x1, y2 - y1, x1, y1))
        estado_janela["maximizada"] = True
        btn_maximizar.config(text="❐")
        grip.place_forget()


def iniciar_arraste(evento):
    estado_janela["arraste"] = (evento.x_root - janela.winfo_x(), evento.y_root - janela.winfo_y())


def arrastar(evento):
    if estado_janela["maximizada"]:
        return
    dx, dy = estado_janela["arraste"]
    janela.geometry("+%d+%d" % (evento.x_root - dx, max(0, evento.y_root - dy)))


def redimensionar(evento):
    largura = max(LARGURA_MINIMA, evento.x_root - janela.winfo_x())
    altura = max(ALTURA_MINIMA, evento.y_root - janela.winfo_y())
    janela.geometry("%dx%d" % (largura, altura))


def construir_barra_titulo():
    global btn_maximizar, grip
    barra = tk.Frame(janela, bg=COR_MENU, height=40)
    barra.pack(side="top", fill="x")
    barra.pack_propagate(False)
    titulo = tk.Label(barra, text="🏠  Cadastro de Portaria", font=("Segoe UI", 10, "bold"), bg=COR_MENU,
                      fg=COR_CREME)
    titulo.pack(side="left", padx=14)
    estilo = dict(width=3, font=("Segoe UI", 10, "bold"), fg="white", bg=COR_MENU_BTN, borda=COR_MENU_BORDA,
                  hover=COR_MENU_HOVER, raio=8, padx=6, pady=2)
    Botao(barra, text="✕", command=janela.destroy, **{**estilo, "bg": "#9C4A3A", "hover": "#B5604D"}).pack(
        side="right", padx=(2, 10), pady=6)
    btn_maximizar = Botao(barra, text="▢", command=alternar_maximizar, **estilo)
    btn_maximizar.pack(side="right", padx=2, pady=6)
    Botao(barra, text="—", command=minimizar, **estilo).pack(side="right", padx=2, pady=6)
    for peca in (barra, titulo):
        peca.bind("<ButtonPress-1>", iniciar_arraste)
        peca.bind("<B1-Motion>", arrastar)
        peca.bind("<Double-Button-1>", lambda _e: alternar_maximizar())
    grip = tk.Label(janela, text="◢", font=("Segoe UI", 11), bg=COR_FUNDO, fg=COR_BORDA,
                cursor="size_nw_se" if EH_WINDOWS else "bottom_right_corner")
    grip.place(relx=1.0, rely=1.0, anchor="se")
    grip.bind("<B1-Motion>", redimensionar)


def colorir_barra_nativa():
    """Alternativa (BARRA_TITULO_PERSONALIZADA = False): pinta a barra nativa do Windows 11."""
    if not EH_WINDOWS:
        return
    try:
        import ctypes

        def colorref(cor):
            r, g, b = [v // 257 for v in janela.winfo_rgb(cor)]
            return r | (g << 8) | (b << 16)

        hwnd = ctypes.windll.user32.GetParent(janela.winfo_id())
        for atributo, cor in ((35, COR_MENU), (36, COR_CREME), (34, COR_MENU)):   # fundo, texto, borda
            valor = ctypes.c_int(colorref(cor))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(valor), ctypes.sizeof(valor))
    except Exception:
        pass


def configurar_moldura_da_janela():
    x = max(0, (janela.winfo_screenwidth() - LARGURA_PADRAO) // 2)
    y = max(0, (janela.winfo_screenheight() - ALTURA_PADRAO) // 3)
    janela.geometry("%dx%d+%d+%d" % (LARGURA_PADRAO, ALTURA_PADRAO, x, y))
    janela.minsize(LARGURA_MINIMA, ALTURA_MINIMA)
    if BARRA_TITULO_PERSONALIZADA:
        janela.overrideredirect(True)
        janela.configure(highlightthickness=1, highlightbackground=COR_MENU, highlightcolor=COR_MENU)
        construir_barra_titulo()
        janela.bind("<Map>", ao_mapear)
        janela.after(150, garantir_icone_na_barra_de_tarefas)
        janela.after(400, janela.focus_force)
    else:
        janela.after(200, colorir_barra_nativa)


# ----------------------------------------------------------------------
# Interface gráfica principal
# ----------------------------------------------------------------------
janela = tk.Tk()
janela.title("Cadastro de Portaria")
janela.configure(bg=COR_FUNDO)

# Campos de texto no tema: fundo creme claro e borda fina que fica verde ao receber o foco
janela.option_add("*Frame.highlightColor", COR_BORDA)
janela.option_add("*Label.foreground", COR_TITULO)
janela.option_add("*Checkbutton.foreground", COR_TITULO)
janela.option_add("*Radiobutton.foreground", COR_TITULO)
janela.option_add("*Checkbutton.highlightThickness", 0)
janela.option_add("*Radiobutton.highlightThickness", 0)
janela.option_add("*Entry.background", "#FFFEF8")
janela.option_add("*Entry.relief", "flat")
janela.option_add("*Entry.highlightThickness", 1)
janela.option_add("*Entry.highlightBackground", COR_BORDA)
janela.option_add("*Entry.highlightColor", COR_AZUL)
janela.option_add("*Entry.selectBackground", COR_VERDE)
janela.option_add("*Entry.selectForeground", "white")
janela.option_add("*TCombobox*Listbox.background", "#FFFEF8")
janela.option_add("*TCombobox*Listbox.selectBackground", COR_AZUL)

configurar_moldura_da_janela()

estilo_ttk = ttk.Style()
try:
    estilo_ttk.theme_use("clam")
except tk.TclError:
    pass
estilo_ttk.configure("Treeview", rowheight=28, font=("Segoe UI", 10), background=COR_CARTAO,
                     fieldbackground=COR_CARTAO, foreground=COR_TITULO, bordercolor=COR_BORDA,
                     lightcolor=COR_BORDA, darkcolor=COR_BORDA)
estilo_ttk.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=COR_PISTACHE_CLARO,
                     foreground=COR_TITULO, relief="flat", bordercolor=COR_BORDA)
estilo_ttk.map("Treeview", background=[("selected", COR_AZUL)], foreground=[("selected", "white")])
estilo_ttk.map("Treeview.Heading", background=[("active", "#CBD7B2")])
estilo_ttk.configure("TCombobox", fieldbackground="#FFFEF8", background=COR_PISTACHE_CLARO, foreground=COR_TITULO,
                     bordercolor=COR_BORDA, arrowcolor=COR_AZUL)
estilo_ttk.map("TCombobox", fieldbackground=[("readonly", "#FFFEF8")], foreground=[("readonly", COR_TITULO)])
estilo_ttk.configure("Vertical.TScrollbar", background=COR_NEUTRO, troughcolor=COR_FUNDO, bordercolor=COR_BORDA,
                     arrowcolor=COR_AZUL)

# Estrutura da tela do sistema (aparece depois do login): painel lateral + conteúdo
app = tk.Frame(janela, bg=COR_FUNDO)

sidebar = tk.Frame(app, bg=COR_MENU, width=250)
sidebar.pack_propagate(False)
sidebar.pack(side="left", fill="y")
tk.Label(sidebar, text="🏠  Cadastro de Portaria", font=("Segoe UI", 11, "bold"), bg=COR_MENU, fg="white",
         anchor="w").pack(fill="x", padx=16, pady=(18, 2))
tk.Label(sidebar, text="Controle de entrada e saída", font=("Segoe UI", 9), bg=COR_MENU, fg="#D9DFC6",
         anchor="w").pack(fill="x", padx=16)
lbl_usuario = tk.Label(sidebar, font=("Segoe UI", 10, "bold"), bg="#3C4A32", fg=COR_CREME, justify="left",
                       anchor="w", padx=12, pady=8)
lbl_usuario.pack(fill="x", padx=12, pady=(16, 10))
menu_itens = tk.Frame(sidebar, bg=COR_MENU)
menu_itens.pack(fill="x")
Botao(sidebar, text="⎋  Sair", font=("Segoe UI", 10, "bold"), fg="white", bg="#9C4A3A",
          hover="#B5604D", borda=COR_MENU_BORDA, raio=12, pady=8, cursor="hand2",
          command=lambda: sair()).pack(side="bottom", fill="x", padx=12, pady=14)

direita = tk.Frame(app, bg=COR_FUNDO)
direita.pack(side="left", fill="both", expand=True)
barra_topo = tk.Frame(direita, bg=COR_CARTAO, highlightbackground=COR_BORDA, highlightthickness=1)
barra_topo.pack(fill="x")
Botao(barra_topo, text="☰", font=("Segoe UI", 13), bg=COR_PISTACHE_CLARO, fg=COR_TITULO, raio=10,
          cursor="hand2", padx=12, pady=2, command=lambda: alternar_menu()).pack(side="left", padx=8, pady=7)
lbl_titulo_pagina = tk.Label(barra_topo, font=("Segoe UI", 14, "bold"), bg=COR_CARTAO, fg=COR_TITULO)
lbl_titulo_pagina.pack(side="left", padx=6)
conteudo = tk.Frame(direita, bg=COR_FUNDO)
conteudo.pack(fill="both", expand=True)

# Página da portaria (cadastro, tabela e pesquisa)
pagina_portaria = tk.Frame(conteudo, bg=COR_FUNDO)

# Formulário (4 colunas: nome/tipo ocupam 2 cada; data e hora separadas)
formulario = tk.Frame(pagina_portaria, bg=COR_CARTAO, padx=14, pady=12,
                      highlightbackground=COR_BORDA, highlightthickness=1)
formulario.pack(fill="x", padx=20, pady=6)
for _c in range(4):
    formulario.columnconfigure(_c, weight=1, uniform="col")

fonte_rotulo = ("Segoe UI", 10)

tk.Label(formulario, text="Nome da pessoa:", font=fonte_rotulo, bg=COR_CARTAO).grid(
    row=0, column=0, columnspan=2, sticky="w", padx=6)
tk.Label(formulario, text="Tipo de acesso:", font=fonte_rotulo, bg=COR_CARTAO).grid(
    row=0, column=2, columnspan=2, sticky="w", padx=6)

campo_nome = tk.Entry(formulario, font=("Segoe UI", 11))
campo_nome.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 10), padx=6, ipady=3)

campo_tipo = ttk.Combobox(formulario, values=TIPOS_ACESSO + [OPCAO_NOVO], state="readonly", font=("Segoe UI", 11))
campo_tipo.grid(row=1, column=2, columnspan=2, sticky="ew", pady=(2, 10), padx=6, ipady=2)
campo_tipo.set(TIPOS_ACESSO[0])
campo_tipo.bind("<<ComboboxSelected>>", ao_selecionar_tipo)

for _col, _texto in enumerate(["Data da entrada:", "Hora da entrada:", "Data da saída:", "Hora da saída:"]):
    tk.Label(formulario, text=_texto, font=fonte_rotulo, bg=COR_CARTAO).grid(row=2, column=_col, sticky="w", padx=6)

campo_ent_data = CampoData(formulario)
campo_ent_data.grid(row=3, column=0, sticky="ew", padx=6, pady=(2, 4))
campo_ent_hora = CampoHora(formulario)
campo_ent_hora.grid(row=3, column=1, sticky="ew", padx=6, pady=(2, 4))
campo_sai_data = CampoData(formulario)
campo_sai_data.grid(row=3, column=2, sticky="ew", padx=6, pady=(2, 4))
campo_sai_hora = CampoHora(formulario)
campo_sai_hora.grid(row=3, column=3, sticky="ew", padx=6, pady=(2, 4))

campo_ent_data.set(agora_data())
campo_ent_hora.set(agora_hora())

tk.Label(formulario, text="Saída em branco = ainda no local. Para dar saída em registro antigo: pesquise, selecione e clique em Registrar saída.",
         font=("Segoe UI", 9), fg=COR_TEXTO_SUAVE, bg=COR_CARTAO, wraplength=780, justify="left").grid(
    row=4, column=0, columnspan=4, sticky="w", padx=6)

# Botões
barra_botoes = tk.Frame(pagina_portaria, bg=COR_FUNDO)
barra_botoes.pack(fill="x", padx=20, pady=(10, 6))
estilo_botao = dict(font=("Segoe UI", 10, "bold"), fg="white", bd=0, padx=12, pady=7,
                    cursor="hand2", activeforeground="white", disabledforeground="#F5F7FA")

btn_cadastrar = Botao(barra_botoes, text="+  Cadastrar", bg=COR_VERDE, activebackground="#17724A",
                          command=cadastrar, **estilo_botao)
btn_cadastrar.pack(side="left")
btn_limpar = Botao(barra_botoes, text="🗑  Limpar", bg=COR_AZUL, activebackground="#1859A8",
                       command=limpar, **estilo_botao)
btn_limpar.pack(side="left", padx=8)
btn_saida = Botao(barra_botoes, text="⏏  Registrar saída", bg=COR_LARANJA, activebackground="#B96300",
                      command=registrar_saida, **estilo_botao)
btn_saida.pack(side="left")
btn_excluir = Botao(barra_botoes, text="✕  Excluir selecionado", bg=COR_VERMELHO, activebackground="#B82B22",
                        command=excluir_selecionado, **estilo_botao)
btn_excluir.pack(side="right")

# Barra de pesquisa
barra_busca = tk.Frame(pagina_portaria, bg=COR_FUNDO)
barra_busca.pack(fill="x", padx=20, pady=(8, 2))
tk.Label(barra_busca, text="🔍 Pesquisar no histórico:", font=("Segoe UI", 10, "bold"),
         bg=COR_FUNDO, fg=COR_TITULO).pack(side="left")
var_busca = tk.StringVar()
campo_busca = tk.Entry(barra_busca, textvariable=var_busca, font=("Segoe UI", 11), width=28)
campo_busca.pack(side="left", padx=8, ipady=3)
var_pendentes = tk.BooleanVar(value=False)
tk.Checkbutton(barra_busca, text="Somente sem saída", variable=var_pendentes, bg=COR_FUNDO,
               font=("Segoe UI", 10), activebackground=COR_FUNDO,
               command=lambda: atualizar_tabela()).pack(side="left", padx=6)
Botao(barra_busca, text="Limpar filtro", font=("Segoe UI", 9), bd=0, bg=COR_PISTACHE_CLARO, cursor="hand2",
          padx=10, pady=3, command=limpar_filtro).pack(side="left")

# Tabela de registros
area_tabela = tk.Frame(pagina_portaria, bg=COR_FUNDO)
area_tabela.pack(fill="both", expand=True, padx=20, pady=(4, 2))

tabela = ttk.Treeview(area_tabela, columns=tuple(COLUNAS), show="headings", selectmode="extended")
tabela.heading("Nome", text="Nome")
tabela.heading("Tipo", text="Tipo de acesso")
tabela.heading("Entrada", text="Entrada")
tabela.heading("Saida", text="Saída")
tabela.column("Nome", width=240, anchor="w")
tabela.column("Tipo", width=130, anchor="w")
tabela.column("Entrada", width=150, anchor="w")
tabela.column("Saida", width=150, anchor="w")
tabela.tag_configure("pendente", background=COR_PENDENTE)
tabela.tag_configure("temporario", foreground=COR_TEMPORARIO)

rolagem = ttk.Scrollbar(area_tabela, orient="vertical", command=tabela.yview)
tabela.configure(yscrollcommand=rolagem.set)
tabela.pack(side="left", fill="both", expand=True)
rolagem.pack(side="right", fill="y")
tabela.bind("<Double-1>", iniciar_edicao)

lbl_contagem = tk.Label(pagina_portaria, font=("Segoe UI", 9, "bold"), bg=COR_FUNDO, fg=COR_TITULO, anchor="w")
lbl_contagem.pack(fill="x", padx=20)
tk.Label(pagina_portaria, text="Dica: duplo clique em uma célula para editar. Amarelo = sem saída registrada. * (marrom) = tipo de acesso temporário.",
         font=("Segoe UI", 9), bg=COR_FUNDO, fg=COR_TEXTO_SUAVE, anchor="w").pack(fill="x", padx=20, pady=(0, 10))

# A pesquisa filtra a tabela enquanto você digita
var_busca.trace_add("write", lambda *_args: atualizar_tabela())

# Enter nos campos do formulário cadastra
for _campo in (campo_nome, campo_ent_data.entry, campo_ent_hora.entry, campo_sai_data.entry, campo_sai_hora.entry):
    _campo.bind("<Return>", lambda _e: cadastrar())

# ----------------------------------------------------------------------
# Demais páginas (todas dentro da mesma janela) e tela de login
# ----------------------------------------------------------------------
paginas = {
    "portaria": pagina_portaria,
    "usuarios": construir_pagina_usuarios(conteudo),
    "auditoria": construir_pagina_auditoria(conteudo),
    "novo": construir_pagina_novo(conteudo),
}

login_frame = tk.Frame(janela, bg=COR_FUNDO)
cartao = tk.Frame(login_frame, bg=COR_CARTAO, padx=36, pady=20, highlightbackground=COR_BORDA, highlightthickness=1)
cartao.place(relx=0.5, rely=0.5, anchor="center")
area_login = tk.Frame(cartao, bg=COR_CARTAO)
area_login.pack()

# ----------------------------------------------------------------------
# Início do programa
# ----------------------------------------------------------------------
carregar_registros()
carregar_auditoria()
carregar_tipos_temporarios()
if not carregar_usuarios():
    janela.destroy()
    sys.exit(1)
atualizar_opcoes_tipo()
verificar_expiracao()
atualizar_tabela()
mostrar_login()                               # sem usuários, o próprio login mostra o cadastro do Admin Final
if BARRA_TITULO_PERSONALIZADA:
    grip.lift()
janela.mainloop()