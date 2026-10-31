"""Regressões de autorização, idempotência e integridade do cofre v2."""
import tempfile
import unittest
from uuid import uuid4
from pathlib import Path
from unittest.mock import patch

from portaria.application.service import PortariaService
from portaria.config import CARGO_FINAL, CARGO_USUARIO
from portaria.domain.security import conferir_hash
from portaria.domain.validation import ValidationError, PermissionDenied, normalizar
from portaria.infrastructure.instance_lock import InstanceLock
from portaria.infrastructure.storage import StorageError
from portaria.config import ITERACOES_PALAVRA


class SecurityV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = PortariaService(self.temp.name)
        self.service.carregar()
        self.service.cadastrar_usuario('Admin Principal', 'Admin', 'admin@teste.com',
                                       '52998224725', CARGO_FINAL, 'Abc12345!',
                                       ['banana','cavalo','janela'])
        self.service.autenticar('admin@teste.com', 'Abc12345!')

    def test_login_inexistente_nao_gera_erro_de_armazenamento(self):
        with self.assertRaises(ValidationError) as ctx:
            self.service.autenticar('inexistente@teste.com', 'Abc12345!')
        self.assertNotIsInstance(ctx.exception, StorageError)

    def test_idempotencia_persistida_e_conflito(self):
        token = str(uuid4())
        one = self.service.cadastrar('Pessoa Um', 'Visitante', '30/10/2026 10:00', operation_id=token)
        two = self.service.cadastrar('Pessoa Um', 'Visitante', '30/10/2026 10:00', operation_id=token)
        self.assertEqual(one['Id'], two['Id'])
        self.assertEqual(len(self.service.registros), 1)
        reopened = PortariaService(self.temp.name)
        reopened.desbloquear_cofre('Abc12345!')
        reopened.carregar()
        reopened.autenticar('admin@teste.com', 'Abc12345!')
        reopened.cadastrar('Pessoa Um', 'Visitante', '30/10/2026 10:00', operation_id=token)
        self.assertEqual(len(reopened.registros), 1)
        with self.assertRaises(ValidationError):
            reopened.cadastrar('Pessoa Dois', 'Visitante', '30/10/2026 10:00', operation_id=token)
        reopened.excluir([one['Id']])
        with self.assertRaises(ValidationError):
            reopened.cadastrar('Pessoa Um', 'Visitante', '30/10/2026 10:00', operation_id=token)

    def test_edicao_multicampo_atomica_e_auditoria(self):
        record = self.service.cadastrar('Pessoa Um', 'Visitante', '30/10/2026 10:00')
        with patch.object(self.service.cofre, 'save_sections', wraps=self.service.cofre.save_sections) as save:
            self.assertTrue(self.service.atualizar_registro(record['Id'], {
                'Nome': 'Pessoa Alterada', 'Entrada': '30/10/2026 09:00', 'Saida':'30/10/2026 11:00'}))
            save.assert_called_once()
        self.assertEqual(len(self.service.auditoria), 2)
        self.assertEqual(self.service.buscar_registro(record['Id'])['Nome'],'Pessoa Alterada')
        self.assertFalse(self.service.atualizar_registro(record['Id'], {'Nome': 'Pessoa Alterada'}))

    def test_multicampo_invalido_nao_persiste_nada(self):
        record = self.service.cadastrar('Pessoa Um', 'Visitante', '30/10/2026 10:00')
        with self.assertRaises(ValidationError):
            self.service.atualizar_registro(record['Id'], {'Nome':'Pessoa Dois','Saida':'29/10/2026 10:00'})
        self.assertEqual(self.service.registros[0]['Nome'],'Pessoa Um')
        self.assertFalse(self.service.auditoria)

    def test_correcao_de_cargo_e_criacao_de_tipo_exigem_permissao(self):
        reg = self.service.cadastrar('Pessoa Um', 'Visitante', '30/10/2026 10:00')
        self.service.cadastrar_usuario('Outro Usuário', 'Outro', 'outro@teste.com',
                                      '11144477735', CARGO_USUARIO, 'Abc12345!',
                                      ['banana', 'cavalo', 'janela'])
        self.service.sair()
        with self.assertRaises(PermissionDenied):
            self.service.criar_tipo_temporario('Sem sessao')
        self.service.autenticar('outro@teste.com','Abc12345!')
        with self.assertRaises(PermissionDenied):
            self.service.atualizar_registro(reg['Id'], {'Nome':'Inválido'})
        with self.assertRaises(PermissionDenied):
            self.service.desbloquear_usuario(self.service.sessao['usuario'])
        with self.assertRaises(PermissionDenied):
            self.service.alterar_cargo(self.service.sessao['usuario'], CARGO_FINAL)

    def test_recuperacao_exige_prova_valida_expira_e_uso_unico(self):
        admin = self.service.achar_usuario_por_login('admin@teste.com')
        self.service.sair()
        with self.assertRaises(PermissionDenied):
            self.service.redefinir_senha(admin, 'NovaSenha123!')
        resposta = []
        for p in admin['Palavras']:
            resposta.append(next(op for op in p['Opcoes'] if
                conferir_hash(normalizar(op), p['Salt'], p['Hash'], ITERACOES_PALAVRA)))
        with self.assertRaises(ValidationError):
            self.service.solicitar_recuperacao(admin['CPF'], admin['Email'], ['erro']*3)
        token = self.service.solicitar_recuperacao(admin['CPF'], admin['Email'], resposta)
        self.service.redefinir_senha(admin, 'NovaSenha123!', recovery_token=token)
        with self.assertRaises(PermissionDenied):
            self.service.redefinir_senha(admin, 'OutraSenha123!', recovery_token=token)
        reopened = PortariaService(self.temp.name)
        reopened.desbloquear_cofre('NovaSenha123!')
        reopened.carregar()
        reopened.autenticar('admin@teste.com','NovaSenha123!')

    def test_detecta_adulteracao_entre_leitura_e_gravacao(self):
        path = Path(self.temp.name)/'dados_portaria.enc'
        blob = path.read_bytes()
        path.write_bytes(blob + b'EXTRA')
        with self.assertRaises(StorageError):
            self.service.cadastrar('Pessoa Um','Visitante','30/10/2026 10:00')
        self.assertEqual(path.read_bytes(), blob + b'EXTRA')
        self.assertFalse(self.service.registros)

    def test_lock_da_instancia(self):
        path = Path(self.temp.name) / 'dados_portaria.lock'
        with InstanceLock(path):
            with self.assertRaises(StorageError):
                with InstanceLock(path):
                    pass
        with InstanceLock(path):
            pass


if __name__ == '__main__':
    unittest.main()
