"""Ações e eventos de access.py na interface Tkinter."""
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
from .operation_guard import proteger_operacao_registro


class AccessMixin:
    def pedir_texto(self, titulo, instrucao):
        """Pergunta um texto dentro da janela. Retorna o texto digitado ou None se cancelado."""
        ov = Sobreposicao(self.janela)
        tk.Label(ov, text=titulo, font=('Segoe UI', 12, 'bold'), bg=COR_CARTAO, fg=COR_TITULO).pack(anchor='w')
        tk.Label(ov, text=instrucao, font=('Segoe UI', 10), bg=COR_CARTAO, justify='left', wraplength=380).pack(anchor='w', pady=(4, 8))
        entrada = tk.Entry(ov, font=('Segoe UI', 11), width=38)
        entrada.pack(fill='x', ipady=3)
        barra = tk.Frame(ov, bg=COR_CARTAO)
        barra.pack(anchor='e', pady=(12, 0))
        Botao(barra, text='Cancelar', bg=COR_NEUTRO, bd=0, padx=14, pady=6, cursor='hand2', command=ov.fechar).pack(side='left', padx=4)
        Botao(barra, text='OK', bg=COR_AZUL, fg='white', bd=0, padx=18, pady=6, font=('Segoe UI', 10, 'bold'), cursor='hand2', command=lambda: ov.fechar(entrada.get())).pack(side='left')
        entrada.bind('<Return>', lambda _e: ov.fechar(entrada.get()))
        ov.foco = entrada
        ov.exibir()
        return ov.valor

    def criar_tipo_temporario(self):
        """Pergunta o nome do tipo temporário e o disponibiliza por 24 horas.
        Retorna o nome a usar, ou None se cancelado."""
        nome = self.pedir_texto('Tipo de acesso temporário', 'Descreva o tipo (ex.: Mecânico, Técnico de internet).\nEle ficará disponível na lista por 24 horas.')
        if nome is None:
            return None
        nome = ' '.join(nome.split())
        if nome == '':
            self.messagebox.showwarning('Atenção', 'Informe o nome do tipo temporário.')
            return None
        try:
            novo = self.service.criar_tipo_temporario(nome)
        except ValidationError as exc:
            self.messagebox.showwarning('Atenção', str(exc))
            return None
        self.atualizar_opcoes_tipo()
        return novo

    def atualizar_opcoes_tipo(self):
        """Remonta a lista do campo Tipo: fixos + temporários ativos + opção 'Novo'.
        Tipos temporários com mais de 24 h somem da lista (ficam arquivados no CSV)."""
        valores = TIPOS_ACESSO + self.service.tipos_temporarios_ativos() + [OPCAO_NOVO]
        self.campo_tipo['values'] = valores
        if self.campo_tipo.get() not in valores or self.campo_tipo.get() == OPCAO_NOVO:
            self.campo_tipo.set(TIPOS_ACESSO[0])
            self.ultimo_tipo['valor'] = TIPOS_ACESSO[0]

    def ao_selecionar_tipo(self, _evento=None):
        if self.campo_tipo.get() == OPCAO_NOVO:
            novo = self.criar_tipo_temporario()
            self.campo_tipo.set(novo if novo else self.ultimo_tipo['valor'])
        self.ultimo_tipo['valor'] = self.campo_tipo.get()

    def verificar_expiracao(self):
        """Roda a cada minuto para retirar da lista os tipos temporários vencidos."""
        self.atualizar_opcoes_tipo()
        self.janela.after(60000, self.verificar_expiracao)

    def editar_para_temporario(self, reg):
        novo = self.criar_tipo_temporario()
        if novo:
            self.aplicar_edicao(reg, 'Tipo', novo)

    def atualizar_tabela(self):
        """Redesenha a tabela aplicando a pesquisa e o filtro de pendentes."""
        selecionados = set(self.tabela.selection())
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        termos = normalizar(self.var_busca.get().strip()).split()
        so_pendentes = self.var_pendentes.get()
        exibidos = 0
        for reg in reversed(self.service.registros):
            if so_pendentes and reg['Saida']:
                continue
            if termos:
                texto = normalizar(' '.join([reg['Nome'], reg['Tipo'], reg['Entrada'], reg['Saida'], 'temporario' if eh_temporario(reg['Tipo']) else '']))
                if not all((t in texto for t in termos)):
                    continue
            tags = []
            if not reg['Saida']:
                tags.append('pendente')
            tipo_exibido = reg['Tipo']
            if eh_temporario(reg['Tipo']):
                tipo_exibido += ' *'
                tags.append('temporario')
            self.tabela.insert('', 'end', iid=reg['Id'], values=(reg['Nome'], tipo_exibido, reg['Entrada'], reg['Saida'] or '—'), tags=tuple(tags))
            exibidos += 1
        for iid in selecionados:
            if self.tabela.exists(iid):
                self.tabela.selection_add(iid)
        pendentes = sum((1 for r in self.service.registros if not r['Saida']))
        self.lbl_contagem.config(text='Exibindo %d de %d registro(s)  |  Sem saída: %d' % (exibidos, len(self.service.registros), pendentes))

    def limpar_filtro(self):
        self.var_busca.set('')
        self.var_pendentes.set(False)
        self.campo_busca.focus()

    @proteger_operacao_registro
    def cadastrar(self):
        if not self.exigir('cadastrar'):
            return
        nome_pessoa = self.campo_nome.get().strip()
        tipo_acesso = self.campo_tipo.get().strip()
        if nome_pessoa == '':
            self.messagebox.showwarning('Atenção', 'Informe o nome da pessoa.')
            self.campo_nome.focus()
            return
        if tipo_acesso not in TIPOS_ACESSO + self.service.tipos_temporarios_ativos():
            self.messagebox.showwarning('Atenção', 'Selecione um tipo de acesso válido.\n(Um tipo temporário pode ter passado de 24 horas.)')
            return
        entrada = converter_data_hora(self.campo_ent_data.get() + ' ' + self.campo_ent_hora.get())
        if entrada is None:
            self.messagebox.showwarning('Atenção', 'Data ou hora de entrada inválida.\nUse dd/mm/aaaa e hh:mm (ou escolha pelo calendário e pelo relógio).')
            self.campo_ent_data.entry.focus()
            return
        texto_entrada = entrada.strftime(FORMATO_DATA_HORA)
        texto_saida = ''
        data_sai, hora_sai = (self.campo_sai_data.get(), self.campo_sai_hora.get())
        if data_sai or hora_sai:
            if not (data_sai and hora_sai):
                self.messagebox.showwarning('Atenção', 'Preencha a data e a hora da saída, ou deixe os dois em branco.')
                return
            saida = converter_data_hora(data_sai + ' ' + hora_sai)
            if saida is None:
                self.messagebox.showwarning('Atenção', 'Data ou hora de saída inválida.\nUse dd/mm/aaaa e hh:mm.')
                self.campo_sai_data.entry.focus()
                return
            texto_saida = saida.strftime(FORMATO_DATA_HORA)
        erro = validar_ordem(texto_entrada, texto_saida)
        if erro:
            self.messagebox.showwarning('Atenção', erro)
            return
        self.service.cadastrar(nome_pessoa, tipo_acesso, texto_entrada, texto_saida)
        self.atualizar_tabela()
        self.messagebox.showinfo('Cadastro', 'Registro cadastrado com sucesso!')
        self.limpar()

    def limpar(self):
        """Limpa o formulário e restaura a data/hora atual na entrada."""
        self.campo_nome.delete(0, tk.END)
        self.campo_tipo.set(TIPOS_ACESSO[0])
        self.ultimo_tipo['valor'] = TIPOS_ACESSO[0]
        self.campo_ent_data.set(agora_data())
        self.campo_ent_hora.set(agora_hora())
        self.campo_sai_data.clear()
        self.campo_sai_hora.clear()
        self.campo_nome.focus()

    @proteger_operacao_registro
    def registrar_saida(self):
        """Registra a saída do registro selecionado na tabela (use a pesquisa para achá-lo).
        Usa a data/hora de saída do formulário; se estiverem vazias, usa o momento atual."""
        if not self.exigir('saida'):
            return
        selecionados = self.tabela.selection()
        if len(selecionados) != 1:
            self.messagebox.showwarning('Atenção', 'Selecione na tabela UM registro para registrar a saída.\nDica: use a pesquisa para localizar quem entrou dias atrás.')
            return
        reg = self.service.buscar_registro(selecionados[0])
        if reg is None:
            return
        if reg['Saida']:
            self.messagebox.showwarning('Atenção', 'Este registro já possui saída (%s).\nPara corrigir, dê um duplo clique na célula Saída (a alteração ficará na Auditoria).' % reg['Saida'])
            return
        data_sai, hora_sai = (self.campo_sai_data.get(), self.campo_sai_hora.get())
        if not data_sai and (not hora_sai):
            data_sai, hora_sai = (agora_data(), agora_hora())
        elif not (data_sai and hora_sai):
            self.messagebox.showwarning('Atenção', 'Preencha a data e a hora da saída, ou deixe os dois em branco para usar o momento atual.')
            return
        saida = converter_data_hora(data_sai + ' ' + hora_sai)
        if saida is None:
            self.messagebox.showwarning('Atenção', 'Data ou hora de saída inválida.')
            return
        texto_saida = saida.strftime(FORMATO_DATA_HORA)
        erro = validar_ordem(reg['Entrada'], texto_saida)
        if erro:
            self.messagebox.showwarning('Atenção', erro + '\nEntrada deste registro: ' + reg['Entrada'])
            return
        if self.aplicar_edicao(reg, 'Saida', texto_saida):
            self.campo_sai_data.clear()
            self.campo_sai_hora.clear()

    def aplicar_edicao(self, reg, campo, novo):
        """Aplica uma alteração em um campo do registro.
        - Primeiro preenchimento da saída: apenas grava (não vai para a auditoria).
        - Qualquer outra alteração: grava, registra na auditoria e mostra o valor anterior."""
        if campo == 'Saida' and reg['Saida'] == '':
            if not self.exigir('saida'):
                return False
        elif not self.exigir('editar'):
            return False
        anterior = reg[campo]
        if anterior == novo:
            return False
        self.service.editar(reg['Id'], campo, novo)
        self.atualizar_tabela()
        self.atualizar_auditoria()
        if campo == 'Saida' and anterior == '':
            self.messagebox.showinfo('Saída registrada', 'Saída de %s registrada em %s.' % (reg['Nome'], novo))
            return True
        self.messagebox.showinfo('Registro alterado', 'Campo alterado: %s\nValor anterior: %s\nNovo valor: %s\n\nA alteração foi guardada na Auditoria.' % (ROTULOS[campo], anterior or '(vazio)', novo or '(vazio)'))
        return True

    @proteger_operacao_registro
    def excluir_selecionado(self):
        if not self.exigir('excluir'):
            return
        selecionados = self.tabela.selection()
        if not selecionados:
            self.messagebox.showwarning('Atenção', 'Selecione um registro na tabela para excluir.')
            return
        if not self.messagebox.askyesno('Confirmar', 'Excluir %d registro(s)?\nA exclusão ficará guardada na Auditoria.' % len(selecionados)):
            return
        self.service.excluir(selecionados)
        self.atualizar_tabela()
        self.atualizar_auditoria()

    def iniciar_edicao(self, evento):
        if self.tabela.identify_region(evento.x, evento.y) != 'cell':
            return
        iid = self.tabela.identify_row(evento.y)
        coluna = self.tabela.identify_column(evento.x)
        reg = self.service.buscar_registro(iid) if iid else None
        if reg is None:
            return
        campo = COLUNAS[int(coluna[1:]) - 1]
        if campo == 'Saida' and (not reg['Saida']):
            if not self.exigir('saida'):
                return
        elif not self.exigir('editar', 'Seu cargo só pode preencher a saída de registros que ainda não têm saída.'):
            return
        if campo == 'Nome':
            self.editar_texto(iid, coluna, reg)
        elif campo == 'Tipo':
            menu = tk.Menu(self.janela, tearoff=0)
            for tipo in TIPOS_ACESSO + self.service.tipos_temporarios_ativos():
                rotulo = tipo + ' *' if eh_temporario(tipo) else tipo
                menu.add_command(label=rotulo, command=lambda t=tipo: self.aplicar_edicao(reg, 'Tipo', t))
            menu.add_separator()
            menu.add_command(label=OPCAO_NOVO, command=lambda: self.editar_para_temporario(reg))
            menu.tk_popup(evento.x_root, evento.y_root)
            menu.grab_release()
        else:
            self.editar_data_hora(reg, campo, (evento.x_root, evento.y_root))

    def editar_texto(self, iid, coluna, reg):
        caixa = self.tabela.bbox(iid, coluna)
        if not caixa:
            return
        x, y, largura, altura = caixa
        editor = tk.Entry(self.tabela, font=('Segoe UI', 10))
        editor.place(x=x, y=y, width=largura, height=altura)
        editor.insert(0, reg['Nome'])
        editor.select_range(0, tk.END)
        editor.focus_set()
        estado = {'fim': False}

        def confirmar(_e=None):
            if estado['fim']:
                return 'break'
            estado['fim'] = True
            novo = editor.get().strip()
            editor.destroy()
            if novo == '':
                self.messagebox.showwarning('Atenção', 'O nome não pode ficar vazio.')
            else:
                self.aplicar_edicao(reg, 'Nome', novo)
            return 'break'

        def cancelar(_e=None):
            if not estado['fim']:
                estado['fim'] = True
                editor.destroy()
            return 'break'
        editor.bind('<Return>', confirmar)
        editor.bind('<Escape>', cancelar)
        editor.bind('<FocusOut>', confirmar)

    def editar_data_hora(self, reg, campo, posicao):
        """Abre o calendário e depois o relógio para alterar Entrada ou Saída."""
        atual = converter_data_hora(reg[campo]) if reg[campo] else None
        base = atual or datetime.now()
        seletor_data = SeletorData(self.janela, base.date(), posicao, permitir_limpar=campo == 'Saida')
        if seletor_data.resultado is None:
            return
        if seletor_data.resultado == '':
            novo = ''
        else:
            seletor_hora = SeletorHora(self.janela, base, posicao)
            if seletor_hora.resultado is None:
                return
            novo = '%s %s' % (seletor_data.resultado.strftime(FORMATO_DATA), seletor_hora.resultado)
        if campo == 'Entrada':
            erro = validar_ordem(novo, reg['Saida'])
        else:
            erro = validar_ordem(reg['Entrada'], novo)
        if erro:
            self.messagebox.showwarning('Atenção', erro)
            return
        self.aplicar_edicao(reg, campo, novo)
