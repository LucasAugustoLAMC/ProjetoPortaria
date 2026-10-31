"""Inicialização, carregamento/migração e desbloqueio do cofre legado v2."""
from ..config import CABECALHO, CABECALHO_AUDITORIA, CABECALHO_TIPOS_TEMP, CARGO_FINAL, ITERACOES_SENHA
from ..domain.security import conferir_hash
from ..domain.validation import ValidationError, novo_id
from ..infrastructure.storage import StorageError
from ..infrastructure.vault import FILES, VaultCsvRepository, VaultJsonRepository, VaultLockedError


class VaultLifecycle:
    """Operações ligadas ao contexto PortariaService."""

    @property
    def cofre_existe(self):
        return self.cofre.exists()

    def desbloquear_cofre(self, senha, *, recuperacao=False):
        if recuperacao:
            self.cofre.unlock_recovery(senha)
        else:
            self.cofre.unlock(senha)
        self._usar_cofre()
        self._eliminar_legados_residuais()

    def _usar_cofre(self):
        self.registros_repo = VaultCsvRepository(self.cofre, FILES[0], CABECALHO, ('Id',))
        self.auditoria_repo = VaultCsvRepository(self.cofre, FILES[1], CABECALHO_AUDITORIA, ('Usuario',))
        self.tipos_repo = VaultCsvRepository(self.cofre, FILES[2], CABECALHO_TIPOS_TEMP)
        self.usuarios_repo = VaultJsonRepository(self.cofre, FILES[3])

    def _eliminar_legados_residuais(self):
        # A migração sempre grava o cofre íntegro antes de apagar textos puros.
        # Após interrupção, o cofre é fonte da verdade e a limpeza pode ser repetida.
        for path in self._plain_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise StorageError(f'Cofre válido, mas não foi possível remover {path.name}. '
                                   'Remova a cópia em texto puro antes de continuar: {exc}') from exc

    def ativar_criptografia(self, senha):
        """Migra CSV/JSON legados sem alterar os registros ou credenciais."""
        if self.cofre_existe:
            raise StorageError('O cofre já existe.')
        admin = next((u for u in self.usuarios if u['Cargo'] == CARGO_FINAL), None)
        if not admin:
            raise StorageError('Cadastre o Admin Final antes de ativar o cofre.')
        try:
            correto = conferir_hash(senha, admin['SenhaSalt'], admin['SenhaHash'], ITERACOES_SENHA)
        except (KeyError, ValueError, TypeError) as exc:
            raise StorageError('Credenciais do Admin Final inválidas.') from exc
        if not correto:
            raise ValidationError('Senha do Admin Final incorreta.')
        dados = dict(zip(FILES, (self.registros, self.auditoria, self.tipos_temporarios, self.usuarios)))
        self.chave_recuperacao = self.cofre.create(senha, dados)
        self._usar_cofre()
        self._eliminar_legados_residuais()

    def carregar(self):
        if self.cofre_existe and not self.cofre.unlocked:
            raise VaultLockedError('O cofre está bloqueado; desbloqueie antes de carregar.')
        # Carregar tudo em temporários: uma falha não deixa estado parcialmente válido.
        registros = self.registros_repo.load()
        auditoria = self.auditoria_repo.load()
        tipos = self.tipos_repo.load()
        usuarios = self.usuarios_repo.load()
        ids = set()
        precisa_migrar = False
        for reg in registros:
            if not reg['Id']:
                reg['Id'] = novo_id()
                while reg['Id'] in ids:
                    reg['Id'] = novo_id()
                precisa_migrar = True
            if reg['Id'] in ids:
                raise StorageError('IDs repetidos em registros_portaria.csv; corrija antes de iniciar.')
            ids.add(reg['Id'])
        if len({u['Id'] for u in usuarios}) != len(usuarios):
            raise StorageError('IDs repetidos em usuarios_portaria.json.')
        if precisa_migrar:
            self.registros_repo.save(registros)
        self.registros, self.auditoria, self.tipos_temporarios, self.usuarios = registros, auditoria, tipos, usuarios

