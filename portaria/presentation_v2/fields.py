"""Entradas mascaradas acessíveis: digitação, substituição, colagem e seleção."""
import calendar
from datetime import date, datetime
import tkinter as tk
from tkinter import ttk
from .theme import FONT, entry, button, text
from ..domain.input_masks import corresponde_mascara


class MaskedEntry(tk.Entry):
    def __init__(self, master, palette, mask, **kwargs):
        self.mask = mask
        validator = master.register(lambda proposed: corresponde_mascara(proposed, mask))
        super().__init__(master, relief='flat', borderwidth=0, bg=palette.field,
                         fg=palette.text, insertbackground=palette.text, highlightthickness=1,
                         highlightbackground=palette.border, highlightcolor=palette.primary,
                         font=(FONT, 11), validate='key',
                         validatecommand=(validator, '%P'), **kwargs)
        self.bind('<KeyPress>', self._key)
        self.bind('<<Paste>>', self._paste)
        self.bind('<Control-v>', self._paste)
        self.bind('<Control-V>', self._paste)

    def _format(self, digits):
        out = ''
        di = 0
        for ch in self.mask:
            if ch in '/:':
                if di < len(digits):
                    out += ch
            elif di < len(digits):
                out += digits[di]
                di += 1
            else:
                break
        return out

    def set(self, value):
        value = str(value)
        if not corresponde_mascara(value, self.mask) and value:
            raise ValueError(f'Formato incorreto: {value}')
        self.delete(0, 'end')
        self.insert(0, value)

    def _replace_digits(self, digits, caret_digit):
        if len(digits) > sum(c not in '/:' for c in self.mask):
            self.bell()
            return
        candidate = self._format(digits)
        if not corresponde_mascara(candidate, self.mask):
            self.bell()
            return
        self.delete(0, 'end')
        self.insert(0, candidate)
        index = 0
        count = 0
        while index < len(candidate) and count < caret_digit:
            if candidate[index].isascii() and candidate[index].isdigit():
                count += 1
            index += 1
        self.icursor(index)

    def _key(self, event):
        if event.state & 0x4 and event.keysym.lower() in ('a', 'c', 'x', 'v'):
            if event.keysym.lower() == 'v':
                return self._paste(event)
            return 'break' if event.keysym.lower() == 'x' else None
        if event.keysym in ('Left', 'Right', 'Home', 'End', 'Tab', 'ISO_Left_Tab'):
            return None
        if event.keysym in ('Return', 'KP_Enter'):
            return None
        value = self.get()
        at = self.index('insert')
        try:
            left, right = self.index('sel.first'), self.index('sel.last')
        except tk.TclError:
            left = right = at
        digits = ''.join(c for c in value if c in '0123456789')
        before = sum(c in '0123456789' for c in value[:left])
        after = sum(c in '0123456789' for c in value[:right])
        if event.keysym in ('BackSpace', 'Delete'):
            if before == after:
                if event.keysym == 'BackSpace':
                    before = max(0, before - 1)
                else:
                    after = min(len(digits), after + 1)
            self._replace_digits(digits[:before] + digits[after:], before)
            return 'break'
        if event.char not in '0123456789' or not event.char:
            self.bell()
            return 'break'
        self._replace_digits(digits[:before] + event.char + digits[after:], before + 1)
        return 'break'

    def _paste(self, _event=None):
        try:
            clip = self.clipboard_get()
        except tk.TclError:
            return 'break'
        if not (corresponde_mascara(clip, self.mask) or
                (clip.isascii() and clip.isdigit() and len(clip) <= sum(c not in '/:' for c in self.mask))):
            self.bell()
            return 'break'
        digits = ''.join(ch for ch in clip if ch in '0123456789')
        self._replace_digits(digits, len(digits))
        return 'break'


class DateTimeInput(tk.Frame):
    """Componente reutilizável com seletor nativo, máscara e campo vazio opcional."""
    def __init__(self, parent, palette, *, initial='', optional=False):
        super().__init__(parent, bg=palette.card)
        self.palette = palette
        self.date = MaskedEntry(self, palette, 'dd/mm/aaaa', width=11)
        self.time = MaskedEntry(self, palette, 'hh:mm', width=6)
        self.date.grid(row=0, column=0, sticky='ew')
        button(self, palette, 'Calendário', self.choose_date, kind='secondary', padx=8, pady=6).grid(row=0, column=1, padx=(5, 13))
        self.time.grid(row=0, column=2, sticky='ew')
        button(self, palette, 'Hora', self.choose_time, kind='secondary', padx=10, pady=6).grid(row=0, column=3, padx=(5, 0))
        self.columnconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)
        if initial:
            self.set(initial)
        self.optional = optional

    def set(self, value):
        if not value:
            self.date.set('')
            self.time.set('')
            return
        data, hora = value.split(' ')
        self.date.set(data)
        self.time.set(hora)

    def get(self):
        data, hora = self.date.get(), self.time.get()
        if not data and not hora:
            return ''
        return data + ' ' + hora

    def set_now(self):
        self.set(datetime.now().strftime('%d/%m/%Y %H:%M'))

    def choose_date(self):
        picker = CalendarDialog(self, self.palette, self.date.get())
        if picker.result:
            self.date.set(picker.result)

    def choose_time(self):
        picker = ClockDialog(self, self.palette, self.time.get())
        if picker.result:
            self.time.set(picker.result)


class CalendarDialog(tk.Toplevel):
    def __init__(self, parent, p, initial):
        super().__init__(parent)
        self.title('Selecionar data')
        self.configure(bg=p.card)
        self.resizable(False, False)
        self.result = None
        try:
            selected = datetime.strptime(initial, '%d/%m/%Y').date()
        except ValueError:
            selected = date.today()
        self.current = selected
        self.palette = p
        head = tk.Frame(self, bg=p.card)
        head.pack(fill='x', padx=16, pady=(12, 6))
        button(head, p, '<', lambda: self.move(-1), kind='secondary').pack(side='left')
        self.month_label = text(head, p, '', size=12, weight='bold')
        self.month_label.pack(side='left', expand=True, padx=12)
        button(head, p, '>', lambda: self.move(1), kind='secondary').pack(side='right')
        self.days = tk.Frame(self, bg=p.card)
        self.days.pack(padx=18, pady=8)
        self.draw()
        button(self, p, 'Hoje', lambda: self.select(date.today()), kind='secondary').pack(fill='x', padx=18, pady=(4, 14))
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.wait_window()

    def move(self, delta):
        y = self.current.year
        m = self.current.month + delta
        if m > 12:
            m, y = 1, y + 1
        elif m < 1:
            m, y = 12, y - 1
        if 1 <= y <= 9999:
            self.current = self.current.replace(year=y, month=m, day=1)
            self.draw()

    def draw(self):
        for c in self.days.winfo_children():
            c.destroy()
        self.month_label.configure(text=self.current.strftime('%m/%Y'))
        for col, day in enumerate(['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']):
            text(self.days, self.palette, day, size=9).grid(row=0, column=col, padx=5)
        weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(self.current.year, self.current.month)
        for r, week in enumerate(weeks, 1):
            for c, d in enumerate(week):
                if d:
                    button(self.days, self.palette, f'{d:02}',
                           lambda n=d: self.select(date(self.current.year, self.current.month, n)),
                           kind='secondary', padx=7, pady=6).grid(row=r, column=c, padx=2, pady=2)

    def select(self, day):
        self.result = day.strftime('%d/%m/%Y')
        self.destroy()


class ClockDialog(tk.Toplevel):
    def __init__(self, parent, p, initial):
        super().__init__(parent)
        self.title('Selecionar horário')
        self.configure(bg=p.card)
        self.resizable(False, False)
        self.result = None
        try:
            time = datetime.strptime(initial, '%H:%M')
        except ValueError:
            time = datetime.now()
        text(self, p, 'Escolha o horário', size=14, weight='bold').pack(padx=22, pady=(18, 8))
        box = tk.Frame(self, bg=p.card)
        box.pack(padx=22, pady=12)
        self.hour = tk.Spinbox(box, from_=0, to=23, wrap=True, width=3, format='%02.0f',
                               font=(FONT, 19), bg=p.field, fg=p.text, justify='center')
        self.hour.delete(0, 'end'); self.hour.insert(0, str(time.hour))
        self.hour.pack(side='left')
        text(box, p, ':', size=22).pack(side='left', padx=9)
        self.minute = tk.Spinbox(box, from_=0, to=59, wrap=True, width=3, format='%02.0f',
                                 font=(FONT, 19), bg=p.field, fg=p.text, justify='center')
        self.minute.delete(0, 'end'); self.minute.insert(0, str(time.minute))
        self.minute.pack(side='left')
        button(self, p, 'Confirmar', self.confirm).pack(fill='x', padx=22, pady=(6, 18))
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.wait_window()

    def confirm(self):
        try:
            h, m = int(self.hour.get()), int(self.minute.get())
            if not (0 <= h < 24 and 0 <= m < 60):
                raise ValueError()
        except ValueError:
            from tkinter import messagebox
            messagebox.showwarning('Horário inválido', 'Escolha uma hora de 00 a 23 e minutos de 00 a 59.', parent=self)
            return
        self.result = f'{h:02}:{m:02}'
        self.destroy()
