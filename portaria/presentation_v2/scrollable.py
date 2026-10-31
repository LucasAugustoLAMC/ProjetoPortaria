"""Painel de formulário adaptativo com rolagem via mouse, teclado e foco.

A geometria depende da área efetivamente disponível, nunca de uma altura fixa.
O conteúdo fica centralizado apenas quando cabe na janela.
"""
import math
import tkinter as tk
from tkinter import ttk


class ScrollableCard(tk.Frame):
    """Área rolável com largura limitada e cartão centralizado.

    `content` recebe os widgets da tela. A barra só aparece quando é necessária.
    A rolagem é vinculada aos filhos, sem `bind_all` global que afetaria outras janelas.
    """

    def __init__(self, parent, palette, *, max_width=650, margin=22, padding_x=30, padding_y=24):
        super().__init__(parent, bg=palette.bg)
        self.max_width = max_width
        self.margin = margin
        self.canvas = tk.Canvas(self, bg=palette.bg, bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.content = tk.Frame(
            self.canvas, bg=palette.card, padx=padding_x, pady=padding_y,
            highlightbackground=palette.border, highlightthickness=1,
        )
        self.window = self.canvas.create_window(0, 0, anchor='n', window=self.content)
        self._pending = False
        self._scrollable = False
        self._bound = set()
        self.canvas.bind('<Configure>', self._schedule_layout)
        self.content.bind('<Configure>', self._schedule_layout)
        self.canvas.bind('<MouseWheel>', self._on_wheel, add='+')
        self.canvas.bind('<Button-4>', self._on_wheel, add='+')
        self.canvas.bind('<Button-5>', self._on_wheel, add='+')
        self.bind('<Prior>', lambda _e: self._key_scroll(-1), add='+')
        self.bind('<Next>', lambda _e: self._key_scroll(1), add='+')

    def _schedule_layout(self, _event=None):
        if not self._pending and self.winfo_exists():
            self._pending = True
            self.after_idle(self._layout)

    def _layout(self):
        self._pending = False
        if not self.winfo_exists():
            return
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        margin = min(self.margin, max(6, width // 18))
        card_width = max(1, min(self.max_width, width - 2 * margin))
        self.canvas.itemconfigure(self.window, width=card_width)
        # O tamanho solicitado reflete a altura atual do formulário e seus textos.
        content_height = self.content.winfo_reqheight()
        overflow = content_height + margin * 2 > height
        if overflow != self._scrollable:
            self._scrollable = overflow
            if overflow:
                self.scrollbar.pack(side='right', fill='y')
            else:
                self.scrollbar.pack_forget()
                self.canvas.yview_moveto(0)
        top = margin if overflow else max(margin, (height - content_height) // 2)
        self.canvas.coords(self.window, width // 2, top)
        self.canvas.configure(scrollregion=(0, 0, width, max(height, top + content_height + margin)))

    def bind_descendants(self):
        """Atualiza os binds após reconstruir um formulário ou suas opções."""
        def visit(widget):
            if widget not in self._bound:
                for event in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                    widget.bind(event, self._on_wheel, add='+')
                widget.bind('<FocusIn>', self._on_focus, add='+')
                self._bound.add(widget)
            for child in widget.winfo_children():
                visit(child)
        visit(self.content)
        self._schedule_layout()

    def _on_wheel(self, event):
        if not self._scrollable:
            return None
        if getattr(event, 'num', None) in (4, 5):
            movement = -3 if event.num == 4 else 3
        else:
            delta = getattr(event, 'delta', 0)
            if not delta:
                return None
            movement = -int(delta / 120) * 3 if abs(delta) >= 120 else (-3 if delta > 0 else 3)
        self.canvas.yview_scroll(movement, 'units')
        return 'break'

    def _key_scroll(self, direction):
        if self._scrollable:
            self.canvas.yview_scroll(direction, 'pages')
            return 'break'
        return None

    def _on_focus(self, event):
        self.after_idle(lambda w=event.widget: self.ensure_visible(w) if w.winfo_exists() else None)

    def ensure_visible(self, widget):
        """Tab até um campo fora da viewport também move a rolagem."""
        if not self._scrollable or not widget.winfo_exists():
            return
        top = widget.winfo_rooty() - self.canvas.winfo_rooty()
        bottom = top + widget.winfo_height()
        viewport = self.canvas.winfo_height()
        if top < 10:
            change = top - 14
        elif bottom > viewport - 10:
            change = bottom - viewport + 14
        else:
            return
        region = self.canvas.cget('scrollregion').split()
        if len(region) != 4:
            return
        total_height = float(region[3]) - float(region[1])
        if total_height <= 0:
            return
        current_offset = self.canvas.canvasy(0)
        self.canvas.yview_moveto(max(0.0, min(1.0, (current_offset + change) / total_height)))
