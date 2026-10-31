"""Validação da criptografia, migração, rotação de senha e integridade."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from portaria.application.service import PortariaService
from portaria.config import CARGO_FINAL
from portaria.domain.security import montar_usuario
from portaria.domain.validation import ValidationError
from portaria.infrastructure.storage import StorageError
from portaria.infrastructure.vault import EncryptedVault, FILES

PASSWORD = 'Seguranca123!'
NEW_PASSWORD = 'Seguranca987!'
CPF = '52998224725'


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.service = PortariaService(self.base)
        self.service.carregar()
        self.service.cadastrar_usuario('Admin Principal', 'Admin', 'admin@teste.com', CPF,
                                       CARGO_FINAL, PASSWORD, ['banana', 'cavalo', 'janela'])
        self.recovery = self.service.chave_recuperacao
        self.vault_path = self.base / 'dados_portaria.enc'
        self.service.autenticar('admin@teste.com', PASSWORD)

    def test_base_vazia_cria_cofre_sem_csv_ou_json_legivel(self):
        self.assertTrue(self.vault_path.is_file())
        self.assertTrue(self.recovery)
        self.assertFalse(any((self.base / name).exists() for name in FILES))
        body = self.vault_path.read_bytes()
        self.assertNotIn(b'admin@teste.com', body)
        self.assertNotIn(b'Admin Principal', body)
        self.assertNotIn(b'Nome,Tipo', body)

    def test_senha_correta_abre_e_errada_nao_altera_dados(self):
        self.service.cadastrar('Pessoa Teste', 'Visitante', '29/10/2026 10:00')
        original = self.vault_path.read_bytes()
        outro = PortariaService(self.base)
        with self.assertRaises(StorageError):
            outro.carregar()
        with self.assertRaises(StorageError):
            outro.desbloquear_cofre('senha-errada')
        self.assertEqual(original, self.vault_path.read_bytes())
        outro.desbloquear_cofre(PASSWORD)
        outro.carregar()
        self.assertEqual(outro.registros[0]['Nome'], 'Pessoa Teste')

    def test_adulteracao_no_cofre_impede_leitura_e_nao_sobrescreve(self):
        original = bytearray(self.vault_path.read_bytes())
        original[-4] ^= 0xFF
        self.vault_path.write_bytes(original)
        novo = PortariaService(self.base)
        with self.assertRaises(StorageError):
            novo.desbloquear_cofre(PASSWORD)
        self.assertEqual(self.vault_path.read_bytes(), original)

    def test_redefinicao_admin_rota_senha_preservando_codigo_recuperacao(self):
        registro = self.service.cadastrar('Pessoa Teste', 'Visitante', '29/10/2026 10:00')
        admin = self.service.achar_usuario_por_login('admin@teste.com')
        self.service.redefinir_senha(admin, NEW_PASSWORD)
        novo = PortariaService(self.base)
        with self.assertRaises(StorageError):
            novo.desbloquear_cofre(PASSWORD)
        novo.desbloquear_cofre(NEW_PASSWORD)
        novo.carregar()
        self.assertEqual(novo.registros[0]['Id'], registro['Id'])
        outro = PortariaService(self.base)
        outro.desbloquear_cofre(self.recovery, recuperacao=True)
        outro.carregar()
        self.assertEqual(outro.usuarios[0]['Email'], 'admin@teste.com')

    def test_codigo_recuperacao_incorreto_falha(self):
        outro = PortariaService(self.base)
        with self.assertRaises(StorageError):
            outro.desbloquear_cofre('codigo-invalido', recuperacao=True)
        self.assertFalse(outro.cofre.unlocked)

    def test_registro_e_auditoria_gravados_num_unico_commit(self):
        r = self.service.cadastrar('Pessoa Teste', 'Visitante', '29/10/2026 10:00')
        with patch.object(self.service.cofre, 'save_sections', wraps=self.service.cofre.save_sections) as save:
            self.service.editar(r['Id'], 'Nome', 'Pessoa Alterada')
            save.assert_called_once()
            sections = save.call_args.args[0]
            self.assertIn(FILES[0], sections)
            self.assertIn(FILES[1], sections)
        outro = PortariaService(self.base)
        outro.desbloquear_cofre(PASSWORD)
        outro.carregar()
        self.assertEqual(outro.registros[0]['Nome'], 'Pessoa Alterada')
        self.assertEqual(len(outro.auditoria), 1)

    def test_falha_escrita_cofre_nao_altera_estado_ou_arquivo(self):
        original = self.vault_path.read_bytes()
        with patch('portaria.infrastructure.vault.os.replace', side_effect=OSError('disco cheio')):
            with self.assertRaises(StorageError):
                self.service.cadastrar('Pessoa Teste', 'Visitante', '29/10/2026 10:00')
        self.assertEqual(original, self.vault_path.read_bytes())
        self.assertFalse(self.service.registros)
        self.assertEqual(sorted(x.name for x in self.base.iterdir()), ['dados_portaria.enc'])

    def test_falha_rotacao_nao_modifica_senha(self):
        original = self.vault_path.read_bytes()
        admin = self.service.achar_usuario_por_login('admin@teste.com')
        with patch('portaria.infrastructure.vault.os.replace', side_effect=OSError('sem espaço')):
            with self.assertRaises(StorageError):
                self.service.redefinir_senha(admin, NEW_PASSWORD)
        self.assertEqual(original, self.vault_path.read_bytes())
        novo = PortariaService(self.base)
        novo.desbloquear_cofre(PASSWORD)
        novo.carregar()
        self.assertEqual(novo.usuarios[0]['SenhaHash'], admin['SenhaHash'])

    def test_migracao_senha_incorreta_nao_apaga_arquivos_legados(self):
        legacy = self.base / 'legado'
        legacy.mkdir()
        user = montar_usuario('Admin Principal', 'Admin', 'admin@teste.com', CPF,
                               CARGO_FINAL, PASSWORD, ['banana', 'cavalo', 'janela'])
        (legacy / 'usuarios_portaria.json').write_text(json.dumps([user]), encoding='utf-8')
        (legacy / 'registros_portaria.csv').write_text(
            'Id,Nome,Tipo,Entrada,Saida\naa123456,Pessoa,Visitante,29/10/2026 10:00,\n', encoding='utf-8-sig')
        antigo = PortariaService(legacy)
        antigo.carregar()
        with self.assertRaises(ValidationError):
            antigo.ativar_criptografia('senha-errada')
        self.assertFalse(antigo.cofre_existe)
        self.assertTrue((legacy / 'usuarios_portaria.json').is_file())
        antigo.ativar_criptografia(PASSWORD)
        self.assertFalse(any((legacy / f).exists() for f in FILES))
        self.assertTrue((legacy / 'dados_portaria.enc').exists())
        novo = PortariaService(legacy)
        novo.desbloquear_cofre(PASSWORD)
        novo.carregar()
        self.assertEqual(novo.registros[0]['Id'], 'aa123456')

    def test_interrupcao_limpeza_migracao_e_retomada(self):
        legacy = self.base / 'legado_interrompido'
        legacy.mkdir()
        user = montar_usuario('Admin Principal', 'Admin', 'admin@teste.com', CPF,
                               CARGO_FINAL, PASSWORD, ['banana', 'cavalo', 'janela'])
        (legacy / 'usuarios_portaria.json').write_text(json.dumps([user]), encoding='utf-8')
        antigo = PortariaService(legacy)
        antigo.carregar()
        with patch.object(antigo, '_eliminar_legados_residuais', side_effect=StorageError('falha na limpeza')):
            with self.assertRaises(StorageError):
                antigo.ativar_criptografia(PASSWORD)
        self.assertTrue((legacy / 'dados_portaria.enc').exists())
        self.assertTrue((legacy / 'usuarios_portaria.json').exists())
        novo = PortariaService(legacy)
        novo.desbloquear_cofre(PASSWORD)
        novo.carregar()
        self.assertFalse((legacy / 'usuarios_portaria.json').exists())
        self.assertEqual(len(novo.usuarios), 1)


if __name__ == '__main__':
    unittest.main()
