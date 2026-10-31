"""Fachada de aplicação: composição das operações e estado de execução.

A UI depende apenas de PortariaService. As capacidades são verificadas aqui,
não dependem da visibilidade de botões ou menus.
"""
from pathlib import Path
from ..config import (ARQUIVO, ARQUIVO_AUDITORIA, ARQUIVO_TIPOS_TEMP, ARQUIVO_USUARIOS,
                      CABECALHO, CABECALHO_AUDITORIA, CABECALHO_TIPOS_TEMP)
from ..domain.permissions import allowed
from ..domain.validation import PermissionDenied
from ..infrastructure.storage import CsvRepository, JsonRepository
from ..infrastructure.vault import EncryptedVault
from .vault_lifecycle import VaultLifecycle
from .access_operations import AccessOperations
from .identity_operations import IdentityOperations


class PortariaService(VaultLifecycle, AccessOperations, IdentityOperations):
    """Fachada compatível com chamadas da versão anterior."""

    def __init__(self, data_dir=None):
        if data_dir:
            from pathlib import Path
            base = Path(data_dir)
            paths = [base / x.name for x in (ARQUIVO, ARQUIVO_AUDITORIA, ARQUIVO_TIPOS_TEMP, ARQUIVO_USUARIOS)]
        else:
            paths = [ARQUIVO, ARQUIVO_AUDITORIA, ARQUIVO_TIPOS_TEMP, ARQUIVO_USUARIOS]
        self._plain_paths = paths
        self.cofre = EncryptedVault(paths[0].parent / 'dados_portaria.enc')
        self.registros_repo = CsvRepository(paths[0], CABECALHO, optional_columns=('Id',))
        self.auditoria_repo = CsvRepository(paths[1], CABECALHO_AUDITORIA, optional_columns=('Usuario',))
        self.tipos_repo = CsvRepository(paths[2], CABECALHO_TIPOS_TEMP)
        self.usuarios_repo = JsonRepository(paths[3])
        self.registros = []
        self.auditoria = []
        self.tipos_temporarios = []
        self.usuarios = []
        self.sessao = {'usuario': None}
        self.chave_recuperacao = None  # exibida apenas uma vez; nunca persiste em texto puro
        self._recovery_grants = {}

    def pode(self, acao):
        u = self.sessao['usuario']
        return bool(u and allowed(u.get('Cargo'), acao))

    def exigir(self, acao):
        if not self.pode(acao):
            raise PermissionDenied('Seu cargo não tem permissão para esta ação.')

    def nome_sessao(self):
        u = self.sessao['usuario']
        return u.get('NomeExibicao', '') if u else ''

