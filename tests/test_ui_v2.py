"""Smoke tests gráficos reais com Tk; pulam sem display gráfico (CI headless)."""
from types import SimpleNamespace
import tempfile
import tkinter as tk
import unittest

from portaria.presentation_v2.app import PortariaApp
from portaria.presentation_v2.auth import AuthView
from portaria.presentation_v2.users import UserForm, UserDialog
from portaria.presentation_v2.records import RecordsView
from portaria.presentation_v2.fields import MaskedEntry
from portaria.config import CARGO_FINAL, CARGO_USUARIO


def display_available():
    try:
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(display_available(), 'Tk requer display (use xvfb-run)')
class UiV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = PortariaApp(data_dir=self.tmp.name)
        self.addCleanup(self.app.destroy)
        self.app.update()
        self.app.service.cadastrar_usuario('Admin Principal', 'Admin', 'admin@teste.com',
            '52998224725', CARGO_FINAL, 'Abc12345!', ['banana','cavalo','janela'])
        self.app.service.chave_recuperacao = None
        self.app.show_auth('login')
        self.app.update()

    def login(self):
        auth = next(w for w in self.app.winfo_children() if isinstance(w, AuthView))
        auth.login.insert(0, 'admin@teste.com')
        auth.password.insert(0, 'Abc12345!')
        auth.sign_in()
        self.app.update()
        self.assertTrue(self.app._dashboard)
        return next(w for w in self.app.content.winfo_children() if isinstance(w, RecordsView))

    def test_primeiro_acesso_cabe_e_pode_rolar_ate_salvar(self):
        self.app.show_auth('setup')
        self.app.geometry('1000x700')
        self.app.update()
        auth = next(w for w in self.app.winfo_children() if isinstance(w, AuthView))
        form = next(w for w in auth.inner.winfo_children() if isinstance(w, UserForm))
        self.assertTrue(auth.scroller._scrollable)
        self.assertFalse(form._narrow)
        self.assertTrue(auth.scroller.scrollbar.winfo_ismapped())
        auth.scroller.ensure_visible(form.save_btn)
        self.app.update()
        self.assertGreater(auth.scroller.canvas.yview()[0], 0)
        bottom = auth.scroller.canvas.winfo_rooty() + auth.scroller.canvas.winfo_height()
        self.assertLessEqual(form.save_btn.winfo_rooty() + form.save_btn.winfo_height(), bottom)
        auth.scroller.canvas.yview_moveto(0)
        self.app.update()
        form.name.event_generate('<MouseWheel>', delta=-120)
        self.app.update()
        self.assertGreater(auth.scroller.canvas.yview()[0], 0)

    def test_primeiro_acesso_estreito_uma_coluna_sem_corte(self):
        self.app.show_auth('setup')
        self.app.geometry('550x520')
        self.app.update()
        auth = next(w for w in self.app.winfo_children() if isinstance(w, AuthView))
        form = next(w for w in auth.inner.winfo_children() if isinstance(w, UserForm))
        self.assertTrue(form._narrow)
        self.assertLessEqual(auth.inner.winfo_width(), auth.scroller.canvas.winfo_width())
        self.assertEqual(form.name.winfo_width(), form.display.winfo_width())
        auth.scroller.canvas.yview_moveto(1)
        self.app.update()
        self.assertLessEqual(
            form.save_btn.winfo_rooty() + form.save_btn.winfo_height(),
            auth.scroller.canvas.winfo_rooty() + auth.scroller.canvas.winfo_height(),
        )
        self.app.geometry('1100x760')
        self.app.update()
        self.assertFalse(form._narrow)

    def test_novo_usuario_em_dialogo_pequeno_tem_rolagem(self):
        dialog = UserDialog(self.app, self.app, lambda _u: None)
        try:
            dialog.geometry('490x470')
            self.app.update()
            scroller = next(w for w in dialog.winfo_children()
                            if w.__class__.__name__ == 'ScrollableCard')
            form = next(w for w in scroller.content.winfo_children() if isinstance(w, UserForm))
            self.assertTrue(form._narrow)
            self.assertTrue(scroller._scrollable)
            scroller.ensure_visible(form.save_btn)
            self.app.update()
            self.assertGreater(scroller.canvas.yview()[0], 0)
        finally:
            dialog.destroy()

    def test_cadastro_navegacao_e_temas(self):
        view = self.login()
        view.name.insert(0, 'Pessoa Valida')
        view.create()
        self.app.update()
        self.assertEqual(len(self.app.service.registros), 1)
        self.app.show_page('audit')
        self.app.show_page('users')
        self.app.show_page('settings')
        self.app.change_theme('Escuro')
        self.app.update()
        self.assertEqual(self.app.theme_name, 'Escuro')
        self.app.change_theme('Floresta')
        self.app.update()
        self.assertEqual(self.app.theme_name, 'Floresta')

    def test_mask_rejeita_emoji_e_valor_impossivel(self):
        from portaria.presentation_v2.theme import THEMES
        w = MaskedEntry(self.app, THEMES['Claro'], 'dd/mm/aaaa')
        w._replace_digits('31102026', 8)
        self.assertEqual(w.get(), '31/10/2026')
        w._replace_digits('32102026', 8)
        self.assertEqual(w.get(), '31/10/2026')
        w._key(SimpleNamespace(state=0, keysym='x', char='X'))
        self.assertEqual(w.get(), '31/10/2026')
        w._key(SimpleNamespace(state=0, keysym='smile', char='🙂'))
        self.assertEqual(w.get(), '31/10/2026')
        w.destroy()

    def test_janela_compacta_modo_alternavel(self):
        view = self.login()
        self.app.geometry('820x660')
        self.app.update()
        self.assertTrue(view._narrow)
        self.assertFalse(self.app._nav_visible)
        view._select_mobile('form')
        self.app.update()
        self.assertTrue(view.form_holder.winfo_ismapped())
        view._select_mobile('records')
        self.app.update()
        self.assertTrue(view.list_card.winfo_ismapped())

    def test_guarda_de_reentrancia_de_interface(self):
        self.login()
        calls = []
        def nested():
            calls.append(1)
            self.assertFalse(self.app.execute(lambda: calls.append(2)))
        self.assertTrue(self.app.execute(nested))
        self.assertEqual(calls, [1])

    def test_permissoes_refletidas_na_navegacao(self):
        self.login()
        self.app.service.cadastrar_usuario('Operador Segundo','Ope','ope@teste.com',
            '11144477735', CARGO_USUARIO, 'Abc12345!', ['banana','cavalo','janela'])
        self.app.logout()
        self.app.service.autenticar('ope@teste.com','Abc12345!')
        self.app.show_dashboard()
        self.app.update()
        self.assertNotIn('users', self.app.nav_buttons)
        self.assertNotIn('audit', self.app.nav_buttons)


if __name__ == '__main__':
    unittest.main()
