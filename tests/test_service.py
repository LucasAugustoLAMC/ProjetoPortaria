"""Regressões que não exigem display nem dependências externas."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from portaria.application.service import PortariaService
from portaria.config import CARGO_FINAL, CARGO_ADM, CARGO_USUARIO
from portaria.domain.validation import ValidationError, PermissionDenied
from portaria.infrastructure.storage import StorageError

CPF = '52998224725'
CPF2 = '11144477735'

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.s = PortariaService(self.base)
        self.s.carregar()
        self.s.cadastrar_usuario('Admin Inicial', 'Inicial', 'admin@teste.com', CPF,
                                  CARGO_FINAL, 'Abc12345!', ['banana','cavalo','janela'])
        self.s.autenticar('admin@teste.com', 'Abc12345!')

    def test_crud_auditoria_e_releitura(self):
        r = self.s.cadastrar('João da Silva', 'Visitante', '29/10/2026 10:00')
        self.assertEqual(self.s.buscar_registro(r['Id'])['Saida'], '')
        self.s.editar(r['Id'], 'Saida', '29/10/2026 10:15')
        self.assertEqual(len(self.s.auditoria), 0)  # primeira saída não audita
        self.s.editar(r['Id'], 'Nome', 'João da Luz')
        self.assertEqual(self.s.auditoria[0]['Anterior'], 'João da Silva')
        self.assertEqual(self.s.auditoria[0]['Usuario'], 'Inicial')
        self.s.excluir([r['Id']])
        self.assertEqual([e['Acao'] for e in self.s.auditoria], ['EDIÇÃO', 'EXCLUSÃO'])
        s2 = PortariaService(self.base)
        s2.desbloquear_cofre('Abc12345!')
        s2.carregar()
        self.assertFalse(s2.registros)
        self.assertEqual(len(s2.auditoria), 2)

    def test_validacao_e_permissoes(self):
        with self.assertRaises(ValidationError):
            self.s.cadastrar('Teste', 'Visitante', '31/10/2026 13:00', '30/10/2026 14:00')
        with self.assertRaises(ValidationError):
            self.s.cadastrar('Teste', 'Visitante', 'invalido')
        self.s.cadastrar_usuario('Operador Segunda', 'Operador', 'ope@teste.com', CPF2,
                                  CARGO_USUARIO, 'Abc12345!', ['banana','cavalo','janela'])
        self.s.sair()
        self.s.autenticar('ope@teste.com', 'Abc12345!')
        r = self.s.cadastrar('Outra Pessoa', 'Visitante', '29/10/2026 10:00')
        self.s.editar(r['Id'], 'Saida', '29/10/2026 11:00')
        with self.assertRaises(PermissionDenied):
            self.s.editar(r['Id'], 'Nome', 'Invasão')
        with self.assertRaises(PermissionDenied):
            self.s.excluir([r['Id']])
        with self.assertRaises(PermissionDenied):
            self.s.cadastrar_usuario('Outro Usuário', 'Novo', 'x@teste.com', CPF2,
                                     CARGO_ADM, 'Abc12345!', ['banana','cavalo','janela'])

    def test_temporario_arquiva_e_preserva(self):
        self.assertEqual(self.s.criar_tipo_temporario('Mecânico'), 'Mecânico')
        self.assertEqual(self.s.criar_tipo_temporario('mecanico'), 'Mecânico')
        self.assertEqual(len(self.s.tipos_temporarios), 1)
        self.assertIn('Mecânico', self.s.tipos_temporarios_ativos())
        self.s.cadastrar('Pessoa Teste', 'Mecânico', '28/10/2026 10:00')
        self.s.tipos_temporarios[0]['CriadoEm'] = '01/01/2020 00:00:00'
        self.assertNotIn('Mecânico', self.s.tipos_temporarios_ativos())
        with self.assertRaises(ValidationError):
            self.s.cadastrar('Pessoa Teste', 'Mecânico', '28/10/2026 10:00')
        self.assertEqual(self.s.registros[0]['Tipo'], 'Mecânico')

    def test_falha_na_gravacao_nao_confirma_operacao(self):
        original = self.s.registros[:]
        with patch.object(self.s.cofre, 'save_sections', side_effect=StorageError('disco indisponível')):
            with self.assertRaises(StorageError):
                self.s.cadastrar('Pessoa Teste', 'Visitante', '29/10/2026 10:00')
        self.assertEqual(self.s.registros, original)
        r = self.s.cadastrar('Teste', 'Visitante', '29/10/2026 10:00')
        with patch.object(self.s.cofre, 'save_sections', side_effect=StorageError('disco indisponível')):
            with self.assertRaises(StorageError):
                self.s.editar(r['Id'], 'Nome', 'Alterado')
        self.assertEqual(self.s.registros[0]['Nome'], 'Teste')
        self.assertEqual(self.s.auditoria, [])

    def test_json_legado_corrompido_bloqueia_migracao_sem_sobrescrever(self):
        pasta = self.base / 'legado_invalido'
        pasta.mkdir()
        arquivo = pasta / 'usuarios_portaria.json'
        arquivo.write_text('{arquivo inválido', encoding='utf-8')
        s2 = PortariaService(pasta)
        with self.assertRaises(StorageError):
            s2.carregar()
        self.assertFalse(s2.cofre_existe)
        self.assertEqual(arquivo.read_text(encoding='utf-8'), '{arquivo inválido')

    def test_login_bloqueio_e_redefinicao(self):
        for _ in range(5):
            with self.assertRaises(ValidationError):
                self.s.autenticar('admin@teste.com', 'errada')
        u = self.s.achar_usuario_por_login('admin@teste.com')
        self.assertGreater(self.s.minutos_bloqueio_restantes(u), 0)
        with self.assertRaises(ValidationError):
            self.s.autenticar('admin@teste.com', 'Abc12345!')
        self.s.limpar_falhas(u)
        self.s.redefinir_senha(self.s.achar_usuario_por_login('admin@teste.com'), 'NovaSenha123!')
        self.s.autenticar('admin@teste.com', 'NovaSenha123!')

    def test_csv_legado_sem_id_e_auditoria_sem_usuario(self):
        from portaria.domain.security import montar_usuario
        legacy = self.base / 'legado'
        legacy.mkdir()
        (legacy / 'registros_portaria.csv').write_text(
            'Nome,Tipo,Entrada,Saida\nJosé,Visitante,29/10/2026 10:00,\n', encoding='utf-8-sig')
        (legacy / 'auditoria_portaria.csv').write_text(
            'Quando,Acao,Id,Nome,Campo,Anterior,Novo\n'
            '29/10/2026 10:00,EDIÇÃO,abc123,José,Nome,Jo,José\n', encoding='utf-8-sig')
        users = [montar_usuario('Admin Inicial', 'Inicial', 'admin@teste.com', CPF,
                                CARGO_FINAL, 'Abc12345!', ['banana', 'cavalo', 'janela'])]
        (legacy / 'usuarios_portaria.json').write_text(json.dumps(users), encoding='utf-8')
        outro = PortariaService(legacy)
        outro.carregar()
        self.assertTrue(outro.registros[0]['Id'])
        self.assertEqual(outro.auditoria[0]['Usuario'], '')
        outro.ativar_criptografia('Abc12345!')
        self.assertFalse((legacy / 'registros_portaria.csv').exists())
        outro2 = PortariaService(legacy)
        outro2.desbloquear_cofre('Abc12345!')
        outro2.carregar()
        self.assertEqual(outro2.registros, outro.registros)

    def test_falha_gravacao_auditoria_mantem_registro(self):
        r = self.s.cadastrar('Teste', 'Visitante', '29/10/2026 10:00')
        with patch.object(self.s.cofre, 'save_sections', side_effect=StorageError('falha de auditoria')):
            with self.assertRaises(StorageError):
                self.s.editar(r['Id'], 'Nome', 'Outro Nome')
        self.assertEqual(self.s.buscar_registro(r['Id'])['Nome'], 'Teste')
        self.assertFalse(self.s.auditoria)

if __name__ == '__main__':
    unittest.main()
