"""Teste integrado da interface. Use xvfb-run no Linux headless."""
import os
import tempfile
import unittest
from portaria.application.service import PortariaService
from portaria.config import CARGO_FINAL, CARGO_ADM
from portaria.domain.security import conferir_hash
from portaria.domain.validation import normalizar
from portaria.config import ITERACOES_PALAVRA
from portaria.presentation.app import PortariaApp
from portaria.presentation.user_forms import FormularioUsuario, RecuperarSenha

@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Tkinter precisa de display')
class UiFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = PortariaApp(PortariaService(self.tmp.name))
        self.addCleanup(self._destruir_janela)
        self.app.service.carregar()
        self.app.atualizar_opcoes_tipo()
        self.app.atualizar_tabela()
        self.app.mostrar_login()
        self.dialogs = []
        class FakeDialog:
            def showinfo(_, title, text, **kw): self.dialogs.append(('info', title, text))
            def showwarning(_, title, text, **kw): self.dialogs.append(('warning', title, text))
            def showerror(_, title, text, **kw): self.dialogs.append(('error', title, text))
            def askyesno(_, title, text, **kw): return True
        self.app.messagebox = FakeDialog()
        # O aviso de recuperação exige uma confirmação humana e é testado separadamente.
        self.app._mostrar_codigo_recuperacao = lambda: setattr(
            self.app.service, 'chave_recuperacao', None)
        self.app.janela.update()

    def _destruir_janela(self):
        raiz = self.app.janela
        if raiz.winfo_exists():
            # Cada teste cria um Tk novo; cancele os callbacks pendentes do anterior.
            for token in raiz.tk.call('after', 'info'):
                raiz.after_cancel(token)
            raiz.destroy()

    def test_desbloqueio_inicial_com_senha_ou_codigo_recuperacao(self):
        app = self.app
        app.service.cadastrar_usuario(
            'Admin Principal', 'Admin', 'admin@teste.com', '52998224725',
            CARGO_FINAL, 'Seguranca123!', ['banana', 'cavalo', 'janela'])
        codigo = app.service.chave_recuperacao
        app.service = PortariaService(self.tmp.name)
        app._pedir_senha_admin = lambda *args, **kwargs: ('senha', 'Seguranca123!')
        self.assertTrue(app._inicializar_cofre())
        self.assertEqual(len(app.service.usuarios), 1)
        app.service = PortariaService(self.tmp.name)
        app._pedir_senha_admin = lambda *args, **kwargs: ('recuperacao', codigo)
        self.assertTrue(app._inicializar_cofre())
        self.assertEqual(len(app.service.usuarios), 1)
        self.assertTrue(any(d[0] == 'info' for d in self.dialogs))

    def test_dialogo_codigo_recuperacao_apenas_uma_exibicao(self):
        app = self.app
        app._mostrar_codigo_recuperacao = type(app)._mostrar_codigo_recuperacao.__get__(app)
        app.service.chave_recuperacao = 'CODIGO-TESTE-NAO-REAL'

        def confirmar():
            from portaria.presentation.components import Sobreposicao, Botao
            import tkinter as tk
            sobreposicao = next(w for w in app.janela.winfo_children()
                                if isinstance(w, Sobreposicao))
            check = next(w for w in sobreposicao.winfo_children()
                         if isinstance(w, tk.Checkbutton))
            check.invoke()
            concluir = next(w for w in sobreposicao.winfo_children()
                            if isinstance(w, Botao))
            concluir.invoke()

        app.janela.after(60, confirmar)
        app._mostrar_codigo_recuperacao()
        self.assertIsNone(app.service.chave_recuperacao)

    def test_full_ui_workflow(self):
        app = self.app
        form = next(w for w in app.area_login.winfo_children() if isinstance(w, FormularioUsuario))
        for field, val in [(form.e_nome, 'Admin Inicial'), (form.e_exibicao, 'Inicial'),
                           (form.e_email, 'admin@teste.com'), (form.e_cpf, '52998224725'),
                           (form.e_senha, 'Abc12345!'), (form.e_conf, 'Abc12345!')]:
            field.insert(0,val)
        for field, val in zip(form.e_palavras, ['banana','cavalo','janela']):
            field.insert(0,val)
        form.salvar()
        self.assertEqual(len(app.service.usuarios), 1)
        app.entrada_login.insert(0, 'admin@teste.com')
        app.entrada_senha.insert(0, 'Abc12345!')
        app.entrar()
        self.assertEqual(app.service.sessao['usuario']['Cargo'], CARGO_FINAL)
        self.assertEqual(app.estado_menu['pagina'], 'portaria')
        app.campo_nome.insert(0, 'Teste Pessoa')
        app.cadastrar()
        r = app.service.registros[0]
        self.assertEqual(len(app.tabela.get_children()), 1)
        app.tabela.selection_set(r['Id'])
        app.registrar_saida()
        self.assertTrue(app.service.buscar_registro(r['Id'])['Saida'])
        app.aplicar_edicao(app.service.buscar_registro(r['Id']), 'Nome', 'Pessoa Alterada')
        self.assertEqual(len(app.service.auditoria), 1)
        app.ir_para('auditoria')
        self.assertEqual(len(app.tabela_aud.get_children()), 1)
        app.ir_para('portaria')
        app.tabela.selection_set(r['Id'])
        app.excluir_selecionado()
        self.assertEqual(len(app.service.auditoria), 2)
        self.assertEqual(len(app.service.registros), 0)
        app.pedir_texto = lambda *args: 'Mecânico'
        self.assertEqual(app.criar_tipo_temporario(), 'Mecânico')
        self.assertIn('Mecânico', app.campo_tipo['values'])
        app.ir_para('novo')
        novo = next(w for w in app.moldura_novo.winfo_children() if isinstance(w, FormularioUsuario))
        for field, val in [(novo.e_nome, 'Pessoa Segunda'), (novo.e_exibicao, 'Segunda'),
                           (novo.e_email, 'segunda@teste.com'), (novo.e_cpf, '11144477735'),
                           (novo.e_senha, 'Abc12345!'), (novo.e_conf, 'Abc12345!')]:
            field.insert(0,val)
        for field,val in zip(novo.e_palavras, ['banana','cavalo','janela']):
            field.insert(0,val)
        novo.salvar()
        self.assertEqual(len(app.service.usuarios),2)
        app.ir_para('usuarios')
        u = app.service.achar_usuario_por_login('segunda@teste.com')
        app.tabela_usr.selection_set(u['Id'])
        app.alterar_cargo()
        self.assertEqual(app.service.achar_usuario_por_id(u['Id'])['Cargo'], 'Usuário')
        app.tabela_usr.selection_set(u['Id'])
        app.desbloquear_usuario()
        app.tabela_usr.selection_set(u['Id'])
        app.excluir_usuario()
        self.assertEqual(len(app.service.usuarios), 1)
        app.sair()
        app.montar_recuperacao()
        rec = next(w for w in app.area_login.winfo_children() if isinstance(w, RecuperarSenha))
        rec.e_cpf.insert(0, '52998224725')
        rec.e_email.insert(0, 'admin@teste.com')
        rec.verificar_dados()
        self.assertEqual(len(rec.variaveis), 3)
        for i, p in enumerate(rec.usuario['Palavras']):
            j = next(j for j,txt in enumerate(rec.ordem[i]) if conferir_hash(normalizar(txt),p['Salt'],p['Hash'],ITERACOES_PALAVRA))
            rec.variaveis[i].set(j)
        rec.verificar_palavras()
        rec.e_nova.insert(0,'NovaSenha123!')
        rec.e_conf.insert(0,'NovaSenha123!')
        rec.salvar_nova()
        self.assertEqual(app.service.usuarios[0]['Tentativas'],0)
        self.assertFalse([x for x in self.dialogs if x[0]=='error'])
        app.janela.update()

    def _autenticar_para_operacoes(self):
        self.app.service.cadastrar_usuario('Admin Inicial', 'Inicial', 'admin@teste.com',
                                           '52998224725', CARGO_FINAL, 'Abc12345!',
                                           ['banana', 'cavalo', 'janela'])
        self.app.service.autenticar('admin@teste.com', 'Abc12345!', CARGO_FINAL)
        self.app.mostrar_app()

    def test_campos_rejeitam_input_invalido_e_colagem(self):
        self._autenticar_para_operacoes()
        app = self.app
        for campo, valido, invalidos in (
            (app.campo_ent_data, '30/10/2026', ('30/02/2026', 'abc', '😀', '30-10-2026')),
            (app.campo_ent_hora, '23:59', ('24:00', '99:01', 'texto', '📅')),
            (app.campo_sai_data, '29/02/2024', ('29/02/2025', '30/1x/2026')),
            (app.campo_sai_hora, '00:00', ('23:60', '12:3😀')),
        ):
            campo.clear()
            for invalido in invalidos:
                with self.subTest(mascara=campo.mascara, invalido=invalido):
                    campo.entry.insert(0, invalido)
                    self.assertEqual(campo.get(), '')
            campo.entry.insert(0, valido)
            self.assertEqual(campo.get(), valido)
            campo.clear()
        self.assertEqual(app.campo_ent_data.entry.cget('validate'), 'key')
        app.campo_ent_data.entry.focus_force()
        app.janela.update()
        for digito in '30102026':
            app.campo_ent_data.entry.focus_force()
            app.campo_ent_data.entry.event_generate('<KeyPress>', keysym=digito)
            app.campo_ent_data.entry.event_generate('<KeyRelease>', keysym=digito)
            app.janela.update_idletasks()
        self.assertEqual(app.campo_ent_data.get(), '30/10/2026')
        app.campo_ent_hora.entry.focus_force()
        app.janela.update()
        for digito in '2359':
            app.campo_ent_hora.entry.focus_force()
            app.campo_ent_hora.entry.event_generate('<KeyPress>', keysym=digito)
            app.campo_ent_hora.entry.event_generate('<KeyRelease>', keysym=digito)
            app.janela.update_idletasks()
        self.assertEqual(app.campo_ent_hora.get(), '23:59')
        app.campo_ent_data.set('31/12/2026')
        self.assertEqual(app.campo_ent_data.get(), '31/12/2026')
        with self.assertRaises(ValueError):
            app.campo_ent_data.set('😄')

    def test_cadastro_reentrante_nao_gera_duplicatas(self):
        from unittest.mock import patch
        from portaria.infrastructure.storage import StorageError
        self._autenticar_para_operacoes()
        app = self.app
        app.campo_nome.insert(0, 'Pessoa Unica')
        exibicoes = []
        def modal(titulo, texto, **kw):
            exibicoes.append(titulo)
            self.assertEqual(app.btn_cadastrar.cget('state'), 'disabled')
            self.assertEqual(app.btn_saida.cget('state'), 'disabled')
            app.cadastrar()  # callback reentrante disparado dentro do diálogo
            app.btn_cadastrar.invoke()  # simula duplo clique no botão
            app.registrar_saida()  # outra operação enquanto está ocupado
            self.assertEqual(len(app.service.registros), 1)
            return 'ok'
        app.messagebox.showinfo = modal
        app.cadastrar()
        self.assertEqual(exibicoes, ['Cadastro'])
        self.assertEqual(len(app.service.registros_repo.load()), 1)
        self.assertEqual(app.btn_cadastrar.cget('state'), 'normal')
        app.messagebox.showinfo = lambda *args, **kw: 'ok'
        app.cadastrar()  # formulário foi limpo; não deve duplicar
        self.assertEqual(len(app.service.registros_repo.load()), 1)
        app.campo_nome.insert(0, 'Falha que permite tentar de novo')
        with patch.object(app.service.registros_repo, 'save', side_effect=StorageError('Disco cheio')):
            with self.assertRaises(StorageError):
                app.cadastrar()
        self.assertEqual(app.btn_cadastrar.cget('state'), 'normal')
        self.assertEqual(len(app.service.registros_repo.load()), 1)
        # A falha não deve manter a operação bloqueada.
        app.cadastrar()
        self.assertEqual(len(app.service.registros_repo.load()), 2)

    def test_guard_restaura_permissoes_originais(self):
        from portaria.config import CARGO_USUARIO
        self._autenticar_para_operacoes()
        app = self.app
        app.service.cadastrar_usuario('Porteiro Teste', 'Porteiro', 'porteiro@teste.com',
                                       '11144477735', CARGO_USUARIO, 'Abc12345!',
                                       ['banana', 'cavalo', 'janela'])
        app.service.sair()
        app.service.autenticar('porteiro@teste.com', 'Abc12345!', CARGO_USUARIO)
        app.mostrar_app()
        self.assertEqual(app.btn_excluir.cget('state'), 'disabled')
        app.campo_nome.insert(0, 'Morador')
        app.cadastrar()
        self.assertEqual(app.btn_excluir.cget('state'), 'disabled')
        self.assertEqual(len(app.service.registros_repo.load()), 1)

    def test_saida_e_exclusao_reentrantes(self):
        self._autenticar_para_operacoes()
        app = self.app
        reg = app.service.cadastrar('Nome Teste', 'Visitante', '30/10/2026 09:00')
        app.atualizar_tabela()
        app.tabela.selection_set(reg['Id'])
        mensagem = app.messagebox.showinfo
        def modal_saida(titulo, texto, **kw):
            self.assertEqual(app.btn_saida.cget('state'), 'disabled')
            app.registrar_saida()
            return mensagem(titulo, texto, **kw)
        app.messagebox.showinfo = modal_saida
        app.registrar_saida()
        self.assertTrue(app.service.buscar_registro(reg['Id'])['Saida'])
        self.assertEqual(app.btn_saida.cget('state'), 'normal')
        self.assertEqual(len(app.service.auditoria), 0)
        def confirmacao(titulo, texto, **kw):
            self.assertEqual(app.btn_excluir.cget('state'), 'disabled')
            app.excluir_selecionado()
            return True
        app.messagebox.askyesno = confirmacao
        app.excluir_selecionado()
        self.assertEqual(len(app.service.registros), 0)
        self.assertEqual(len(app.service.auditoria), 1)
        self.assertEqual(len(app.service.auditoria_repo.load()), 1)
        self.assertEqual(app.btn_excluir.cget('state'), 'normal')

if __name__=='__main__':
    unittest.main()
