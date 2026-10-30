"""Composição da interface e ponto central de inicialização (sem I/O no import)."""
import tkinter as tk
from tkinter import ttk
import logging, traceback
from pathlib import Path
from ..config import *
from ..application.service import PortariaService
from ..infrastructure.storage import StorageError
from ..infrastructure.vault import require_crypto
from ..domain.validation import *
from .components import Botao, Sobreposicao, SeletorData, SeletorHora, CampoData, CampoHora, _CaixaMensagem
from .user_forms import FormularioUsuario, RecuperarSenha
from .access import AccessMixin
from .audit import AuditMixin
from .users import UsersMixin
from .navigation import NavigationMixin
from .window_chrome import WindowChromeMixin

class PortariaApp(AccessMixin, AuditMixin, UsersMixin, NavigationMixin, WindowChromeMixin):
    def __init__(self, service=None):
        self.service = service or PortariaService()
        self._registro_ocupado = False
        self.ultimo_tipo = {'valor': TIPOS_ACESSO[0]}
        self.estado_menu = {'visivel': True, 'pagina': 'portaria', 'botoes': {}}
        self.estado_janela = {'maximizada': False, 'geometria': None, 'minimizado': False, 'arraste': (0, 0)}
        self.tabela_usr = None
        self.tabela_aud = None
        self.btn_maximizar = None
        self.grip = None
        self.moldura_novo = None
        self.janela = tk.Tk()
        self.messagebox = _CaixaMensagem(self)
        self.janela.report_callback_exception = self._on_error
        self.janela.title('Cadastro de Portaria')
        self.janela.configure(bg=COR_FUNDO)
        self.janela.option_add('*Frame.highlightColor', COR_BORDA)
        self.janela.option_add('*Label.foreground', COR_TITULO)
        self.janela.option_add('*Checkbutton.foreground', COR_TITULO)
        self.janela.option_add('*Radiobutton.foreground', COR_TITULO)
        self.janela.option_add('*Checkbutton.highlightThickness', 0)
        self.janela.option_add('*Radiobutton.highlightThickness', 0)
        self.janela.option_add('*Entry.background', '#FFFEF8')
        self.janela.option_add('*Entry.relief', 'flat')
        self.janela.option_add('*Entry.highlightThickness', 1)
        self.janela.option_add('*Entry.highlightBackground', COR_BORDA)
        self.janela.option_add('*Entry.highlightColor', COR_AZUL)
        self.janela.option_add('*Entry.selectBackground', COR_VERDE)
        self.janela.option_add('*Entry.selectForeground', 'white')
        self.janela.option_add('*TCombobox*Listbox.background', '#FFFEF8')
        self.janela.option_add('*TCombobox*Listbox.selectBackground', COR_AZUL)
        self.configurar_moldura_da_janela()
        estilo_ttk = ttk.Style()
        try:
            estilo_ttk.theme_use('clam')
        except tk.TclError:
            pass
        estilo_ttk.configure('Treeview', rowheight=28, font=('Segoe UI', 10), background=COR_CARTAO, fieldbackground=COR_CARTAO, foreground=COR_TITULO, bordercolor=COR_BORDA, lightcolor=COR_BORDA, darkcolor=COR_BORDA)
        estilo_ttk.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), background=COR_PISTACHE_CLARO, foreground=COR_TITULO, relief='flat', bordercolor=COR_BORDA)
        estilo_ttk.map('Treeview', background=[('selected', COR_AZUL)], foreground=[('selected', 'white')])
        estilo_ttk.map('Treeview.Heading', background=[('active', '#CBD7B2')])
        estilo_ttk.configure('TCombobox', fieldbackground='#FFFEF8', background=COR_PISTACHE_CLARO, foreground=COR_TITULO, bordercolor=COR_BORDA, arrowcolor=COR_AZUL)
        estilo_ttk.map('TCombobox', fieldbackground=[('readonly', '#FFFEF8')], foreground=[('readonly', COR_TITULO)])
        estilo_ttk.configure('Vertical.TScrollbar', background=COR_NEUTRO, troughcolor=COR_FUNDO, bordercolor=COR_BORDA, arrowcolor=COR_AZUL)
        self.app = tk.Frame(self.janela, bg=COR_FUNDO)
        self.sidebar = tk.Frame(self.app, bg=COR_MENU, width=250)
        self.sidebar.pack_propagate(False)
        self.sidebar.pack(side='left', fill='y')
        tk.Label(self.sidebar, text='🏠  Cadastro de Portaria', font=('Segoe UI', 11, 'bold'), bg=COR_MENU, fg='white', anchor='w').pack(fill='x', padx=16, pady=(18, 2))
        tk.Label(self.sidebar, text='Controle de entrada e saída', font=('Segoe UI', 9), bg=COR_MENU, fg='#D9DFC6', anchor='w').pack(fill='x', padx=16)
        self.lbl_usuario = tk.Label(self.sidebar, font=('Segoe UI', 10, 'bold'), bg='#3C4A32', fg=COR_CREME, justify='left', anchor='w', padx=12, pady=8)
        self.lbl_usuario.pack(fill='x', padx=12, pady=(16, 10))
        self.menu_itens = tk.Frame(self.sidebar, bg=COR_MENU)
        self.menu_itens.pack(fill='x')
        Botao(self.sidebar, text='⎋  Sair', font=('Segoe UI', 10, 'bold'), fg='white', bg='#9C4A3A', hover='#B5604D', borda=COR_MENU_BORDA, raio=12, pady=8, cursor='hand2', command=lambda: self.sair()).pack(side='bottom', fill='x', padx=12, pady=14)
        self.direita = tk.Frame(self.app, bg=COR_FUNDO)
        self.direita.pack(side='left', fill='both', expand=True)
        self.barra_topo = tk.Frame(self.direita, bg=COR_CARTAO, highlightbackground=COR_BORDA, highlightthickness=1)
        self.barra_topo.pack(fill='x')
        Botao(self.barra_topo, text='☰', font=('Segoe UI', 13), bg=COR_PISTACHE_CLARO, fg=COR_TITULO, raio=10, cursor='hand2', padx=12, pady=2, command=lambda: self.alternar_menu()).pack(side='left', padx=8, pady=7)
        self.lbl_titulo_pagina = tk.Label(self.barra_topo, font=('Segoe UI', 14, 'bold'), bg=COR_CARTAO, fg=COR_TITULO)
        self.lbl_titulo_pagina.pack(side='left', padx=6)
        self.conteudo = tk.Frame(self.direita, bg=COR_FUNDO)
        self.conteudo.pack(fill='both', expand=True)
        self.pagina_portaria = tk.Frame(self.conteudo, bg=COR_FUNDO)
        self.formulario = tk.Frame(self.pagina_portaria, bg=COR_CARTAO, padx=14, pady=12, highlightbackground=COR_BORDA, highlightthickness=1)
        self.formulario.pack(fill='x', padx=20, pady=6)
        for _c in range(4):
            self.formulario.columnconfigure(_c, weight=1, uniform='col')
        fonte_rotulo = ('Segoe UI', 10)
        tk.Label(self.formulario, text='Nome da pessoa:', font=fonte_rotulo, bg=COR_CARTAO).grid(row=0, column=0, columnspan=2, sticky='w', padx=6)
        tk.Label(self.formulario, text='Tipo de acesso:', font=fonte_rotulo, bg=COR_CARTAO).grid(row=0, column=2, columnspan=2, sticky='w', padx=6)
        self.campo_nome = tk.Entry(self.formulario, font=('Segoe UI', 11))
        self.campo_nome.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(2, 10), padx=6, ipady=3)
        self.campo_tipo = ttk.Combobox(self.formulario, values=TIPOS_ACESSO + [OPCAO_NOVO], state='readonly', font=('Segoe UI', 11))
        self.campo_tipo.grid(row=1, column=2, columnspan=2, sticky='ew', pady=(2, 10), padx=6, ipady=2)
        self.campo_tipo.set(TIPOS_ACESSO[0])
        self.campo_tipo.bind('<<ComboboxSelected>>', self.ao_selecionar_tipo)
        for _col, _texto in enumerate(['Data da entrada:', 'Hora da entrada:', 'Data da saída:', 'Hora da saída:']):
            tk.Label(self.formulario, text=_texto, font=fonte_rotulo, bg=COR_CARTAO).grid(row=2, column=_col, sticky='w', padx=6)
        self.campo_ent_data = CampoData(self.formulario)
        self.campo_ent_data.grid(row=3, column=0, sticky='ew', padx=6, pady=(2, 4))
        self.campo_ent_hora = CampoHora(self.formulario)
        self.campo_ent_hora.grid(row=3, column=1, sticky='ew', padx=6, pady=(2, 4))
        self.campo_sai_data = CampoData(self.formulario)
        self.campo_sai_data.grid(row=3, column=2, sticky='ew', padx=6, pady=(2, 4))
        self.campo_sai_hora = CampoHora(self.formulario)
        self.campo_sai_hora.grid(row=3, column=3, sticky='ew', padx=6, pady=(2, 4))
        self.campo_ent_data.set(agora_data())
        self.campo_ent_hora.set(agora_hora())
        tk.Label(self.formulario, text='Saída em branco = ainda no local. Para dar saída em registro antigo: pesquise, selecione e clique em Registrar saída.', font=('Segoe UI', 9), fg=COR_TEXTO_SUAVE, bg=COR_CARTAO, wraplength=780, justify='left').grid(row=4, column=0, columnspan=4, sticky='w', padx=6)
        barra_botoes = tk.Frame(self.pagina_portaria, bg=COR_FUNDO)
        barra_botoes.pack(fill='x', padx=20, pady=(10, 6))
        estilo_botao = dict(font=('Segoe UI', 10, 'bold'), fg='white', bd=0, padx=12, pady=7, cursor='hand2', activeforeground='white', disabledforeground='#F5F7FA')
        self.btn_cadastrar = Botao(barra_botoes, text='+  Cadastrar', bg=COR_VERDE, activebackground='#17724A', command=self.cadastrar, **estilo_botao)
        self.btn_cadastrar.pack(side='left')
        self.btn_limpar = Botao(barra_botoes, text='🗑  Limpar', bg=COR_AZUL, activebackground='#1859A8', command=self.limpar, **estilo_botao)
        self.btn_limpar.pack(side='left', padx=8)
        self.btn_saida = Botao(barra_botoes, text='⏏  Registrar saída', bg=COR_LARANJA, activebackground='#B96300', command=self.registrar_saida, **estilo_botao)
        self.btn_saida.pack(side='left')
        self.btn_excluir = Botao(barra_botoes, text='✕  Excluir selecionado', bg=COR_VERMELHO, activebackground='#B82B22', command=self.excluir_selecionado, **estilo_botao)
        self.btn_excluir.pack(side='right')
        barra_busca = tk.Frame(self.pagina_portaria, bg=COR_FUNDO)
        barra_busca.pack(fill='x', padx=20, pady=(8, 2))
        tk.Label(barra_busca, text='🔍 Pesquisar no histórico:', font=('Segoe UI', 10, 'bold'), bg=COR_FUNDO, fg=COR_TITULO).pack(side='left')
        self.var_busca = tk.StringVar()
        self.campo_busca = tk.Entry(barra_busca, textvariable=self.var_busca, font=('Segoe UI', 11), width=28)
        self.campo_busca.pack(side='left', padx=8, ipady=3)
        self.var_pendentes = tk.BooleanVar(value=False)
        tk.Checkbutton(barra_busca, text='Somente sem saída', variable=self.var_pendentes, bg=COR_FUNDO, font=('Segoe UI', 10), activebackground=COR_FUNDO, command=lambda: self.atualizar_tabela()).pack(side='left', padx=6)
        Botao(barra_busca, text='Limpar filtro', font=('Segoe UI', 9), bd=0, bg=COR_PISTACHE_CLARO, cursor='hand2', padx=10, pady=3, command=self.limpar_filtro).pack(side='left')
        area_tabela = tk.Frame(self.pagina_portaria, bg=COR_FUNDO)
        area_tabela.pack(fill='both', expand=True, padx=20, pady=(4, 2))
        self.tabela = ttk.Treeview(area_tabela, columns=tuple(COLUNAS), show='headings', selectmode='extended')
        self.tabela.heading('Nome', text='Nome')
        self.tabela.heading('Tipo', text='Tipo de acesso')
        self.tabela.heading('Entrada', text='Entrada')
        self.tabela.heading('Saida', text='Saída')
        self.tabela.column('Nome', width=240, anchor='w')
        self.tabela.column('Tipo', width=130, anchor='w')
        self.tabela.column('Entrada', width=150, anchor='w')
        self.tabela.column('Saida', width=150, anchor='w')
        self.tabela.tag_configure('pendente', background=COR_PENDENTE)
        self.tabela.tag_configure('temporario', foreground=COR_TEMPORARIO)
        rolagem = ttk.Scrollbar(area_tabela, orient='vertical', command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=rolagem.set)
        self.tabela.pack(side='left', fill='both', expand=True)
        rolagem.pack(side='right', fill='y')
        self.tabela.bind('<Double-1>', self.iniciar_edicao)
        self.lbl_contagem = tk.Label(self.pagina_portaria, font=('Segoe UI', 9, 'bold'), bg=COR_FUNDO, fg=COR_TITULO, anchor='w')
        self.lbl_contagem.pack(fill='x', padx=20)
        tk.Label(self.pagina_portaria, text='Dica: duplo clique em uma célula para editar. Amarelo = sem saída registrada. * (marrom) = tipo de acesso temporário.', font=('Segoe UI', 9), bg=COR_FUNDO, fg=COR_TEXTO_SUAVE, anchor='w').pack(fill='x', padx=20, pady=(0, 10))
        self.var_busca.trace_add('write', lambda *_args: self.atualizar_tabela())
        for _campo in (self.campo_nome, self.campo_ent_data.entry, self.campo_ent_hora.entry, self.campo_sai_data.entry, self.campo_sai_hora.entry):
            _campo.bind('<Return>', lambda _e: self.cadastrar())
        self.paginas = {'portaria': self.pagina_portaria, 'usuarios': self.construir_pagina_usuarios(self.conteudo), 'auditoria': self.construir_pagina_auditoria(self.conteudo), 'novo': self.construir_pagina_novo(self.conteudo)}
        self.login_frame = tk.Frame(self.janela, bg=COR_FUNDO)
        self.cartao = tk.Frame(self.login_frame, bg=COR_CARTAO, padx=36, pady=20, highlightbackground=COR_BORDA, highlightthickness=1)
        self.cartao.place(relx=0.5, rely=0.5, anchor='center')
        self.area_login = tk.Frame(self.cartao, bg=COR_CARTAO)
        self.area_login.pack()

    def _on_error(self, typ, exc, tb):
        logging.error('Falha na interface: %s', exc, exc_info=(typ, exc, tb))
        try:
            self.messagebox.showerror('Erro', str(exc) if isinstance(exc, (ValidationError, StorageError))
                                       else 'Ocorreu uma falha inesperada. Consulte portaria.log.')
        except tk.TclError:
            logging.error('Não foi possível exibir aviso de erro')

    def exigir(self, acao, mensagem=None):
        if self.service.pode(acao):
            return True
        self.messagebox.showwarning('Acesso negado', mensagem or 'Seu cargo não tem permissão para esta ação.')
        return False

    def avisar_bloqueio(self, u, pai=None):
        self.messagebox.showwarning('Conta bloqueada', 'Muitas tentativas incorretas. Tente novamente em %d minuto(s).'
                                    % self.service.minutos_bloqueio_restantes(u))

    def _mostrar_codigo_recuperacao(self):
        codigo = self.service.chave_recuperacao
        if not codigo:
            return
        ov = Sobreposicao(self.janela)
        tk.Label(ov, text='Código de recuperação do cofre',
                 font=('Segoe UI', 13, 'bold'), bg=COR_CARTAO,
                 fg=COR_TITULO).pack(anchor='w')
        tk.Label(ov, text=('Copie este código agora e guarde FORA do computador compartilhado. '
                          'Ele só será mostrado uma vez. Se esquecer a senha do Admin Final, '
                          'será necessário para abrir a base e redefinir a senha.'),
                 bg=COR_CARTAO, fg=COR_TITULO, wraplength=460,
                 justify='left').pack(anchor='w', pady=(10, 8))
        campo = tk.Entry(ov, width=52, font=('Consolas', 10), readonlybackground='#FFFEF8')
        campo.insert(0, codigo)
        campo.configure(state='readonly')
        campo.pack(fill='x', ipady=5)
        confirmacao = tk.BooleanVar(value=False)
        tk.Checkbutton(ov, text='Confirmei que guardei o código em local seguro.',
                       variable=confirmacao, bg=COR_CARTAO,
                       activebackground=COR_CARTAO).pack(anchor='w', pady=(12, 6))
        botao = Botao(ov, text='Concluir', bg=COR_VERDE, state='disabled',
                      command=lambda: ov.fechar(True))
        botao.pack(anchor='e')
        confirmacao.trace_add('write', lambda *_: botao.configure(
            state='normal' if confirmacao.get() else 'disabled'))
        ov.foco = campo
        ov.exibir()
        self.service.chave_recuperacao = None

    def _pedir_senha_admin(self, titulo, instrucao, *, permitir_recuperacao=False):
        """Solicita uma das credenciais sem usá-la como login de outro usuário."""
        ov = Sobreposicao(self.janela)
        tk.Label(ov, text=titulo, font=('Segoe UI', 13, 'bold'),
                 bg=COR_CARTAO, fg=COR_TITULO).pack(anchor='w')
        tk.Label(ov, text=instrucao, font=('Segoe UI', 10), bg=COR_CARTAO,
                 fg=COR_TITULO, wraplength=430, justify='left').pack(anchor='w', pady=(8, 10))
        modo = tk.StringVar(value='senha')
        if permitir_recuperacao:
            opcoes = tk.Frame(ov, bg=COR_CARTAO)
            opcoes.pack(anchor='w', pady=(0, 8))
            for texto, valor in [('Senha do Admin Final', 'senha'),
                                 ('Código de recuperação', 'recuperacao')]:
                tk.Radiobutton(opcoes, text=texto, value=valor, variable=modo,
                               bg=COR_CARTAO, activebackground=COR_CARTAO).pack(anchor='w')
        senha = tk.Entry(ov, show='•', font=('Segoe UI', 11), width=40)
        senha.pack(fill='x', ipady=4)
        botoes = tk.Frame(ov, bg=COR_CARTAO)
        botoes.pack(anchor='e', pady=(14, 0))
        Botao(botoes, text='Cancelar', bg=COR_NEUTRO,
              command=lambda: ov.fechar(None)).pack(side='left', padx=5)
        Botao(botoes, text='Desbloquear', bg=COR_VERDE,
              command=lambda: ov.fechar((modo.get(), senha.get()))).pack(side='left')
        senha.bind('<Return>', lambda _e: ov.fechar((modo.get(), senha.get())))
        ov.foco = senha
        ov.exibir()
        return ov.valor

    def _inicializar_cofre(self):
        require_crypto()
        if self.service.cofre_existe:
            titulo = 'Desbloquear base criptografada'
            instrucao = ('Digite a senha do Admin Final para abrir os dados. '
                         'Depois disso, cada usuário entra com a própria senha. '
                         'Sem a senha do Admin Final, o cofre não pode ser aberto.')
        else:
            self.service.carregar()
            if not self.service.usuarios:
                # No primeiro cadastro, o serviço cria o cofre diretamente.
                return True
            titulo = 'Proteger dados existentes'
            instrucao = ('Migração inicial: informe a senha do Admin Final. '
                         'Os quatro arquivos atuais serão criptografados juntos; '
                         'faça backup antes da primeira execução.')
        for _ in range(3):
            resposta = self._pedir_senha_admin(
                titulo, instrucao, permitir_recuperacao=self.service.cofre_existe)
            if resposta is None:
                return False
            modo, senha = resposta
            try:
                if self.service.cofre_existe:
                    self.service.desbloquear_cofre(senha, recuperacao=modo == 'recuperacao')
                    self.service.carregar()
                else:
                    self.service.ativar_criptografia(senha)
                    self._mostrar_codigo_recuperacao()
                if modo == 'recuperacao':
                    self.messagebox.showinfo('Cofre desbloqueado',
                        'Use a opção Esqueci minha senha no login para redefinir a senha '
                        'do Admin Final. O código de recuperação continuará válido.')
                return True
            except ValidationError as exc:
                self.messagebox.showwarning('Senha incorreta', str(exc))
            except StorageError as exc:
                # Senha incorreta e corrupção produzem falha indistinguível no GCM.
                if 'Credencial incorreta ou cofre alterado' in str(exc):
                    self.messagebox.showwarning('Cofre não desbloqueado', str(exc))
                else:
                    raise
        return False

    def run(self):
        try:
            if not self._inicializar_cofre():
                self.janela.destroy()
                return False
        except (StorageError, ValidationError) as exc:
            self.messagebox.showerror('Erro ao carregar dados', str(exc) + '\nNenhum arquivo será sobrescrito.')
            self.janela.destroy()
            return False
        self.atualizar_opcoes_tipo()
        self.verificar_expiracao()
        self.atualizar_tabela()
        self.mostrar_login()
        if BARRA_TITULO_PERSONALIZADA:
            self.grip.lift()
        self.janela.mainloop()
        return True
