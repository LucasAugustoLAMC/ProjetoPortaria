"""Cofre local criptografado; os quatro conjuntos de dados são gravados juntos.

AES-256-GCM (criptografia autenticada) + PBKDF2-HMAC-SHA256.
Cada gravação troca o arquivo inteiro com os.replace; nenhum texto puro é
escrito como arquivo temporário pelo cofre.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile

from .storage import StorageError

try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None
    InvalidTag = Exception


# Formato local v2: o segredo de dados é aleatório e pode ser desbloqueado
# com a senha do Admin Final ou com um código de recuperação de uso offline.
MAGIC = b'PORTARIA-COFRE-v2\x00'
SALT_LENGTH = 16
NONCE_LENGTH = 12
KEY_LENGTH = 32
WRAPPED_LENGTH = KEY_LENGTH + 16
ITERATIONS = 600_000
FILES = ('registros_portaria.csv', 'auditoria_portaria.csv',
         'tipos_temporarios.csv', 'usuarios_portaria.json')


class VaultLockedError(StorageError):
    pass


def require_crypto():
    if AESGCM is None:
        raise StorageError('A criptografia exige a biblioteca cryptography. '
                           'Instale com: python -m pip install -r requirements.txt')


def _write_bytes(path, content):
    """Substituição atômica; texto puro não é materializado em disco."""
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            if os.name == 'posix':
                os.chmod(temporary, 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise StorageError(f'Falha ao salvar cofre criptografado: {exc}') from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


class EncryptedVault:
    def __init__(self, path):
        self.path = Path(path)
        self._key = None
        self._pw_wrap = None
        self._rc_wrap = None
        self._data = None
        self._revision = None

    @property
    def unlocked(self):
        return self._data is not None

    def exists(self):
        return self.path.exists()

    @staticmethod
    def _derive(secret, salt):
        if not secret:
            raise StorageError('Informe a senha do Admin Final ou o código de recuperação.')
        return hashlib.pbkdf2_hmac('sha256', secret.encode('utf-8'), salt,
                                   ITERATIONS, dklen=KEY_LENGTH)

    @staticmethod
    def _validate(data):
        if (not isinstance(data, dict) or set(data) != set(FILES) or
                any(not isinstance(data[name], list) or
                    not all(isinstance(row, dict) for row in data[name]) for name in FILES)):
            raise StorageError('Estrutura interna do cofre inválida; dados não serão sobrescritos.')

    @staticmethod
    def _wrap_key(data_key, secret):
        salt = secrets.token_bytes(SALT_LENGTH)
        nonce = secrets.token_bytes(NONCE_LENGTH)
        wrapped = AESGCM(EncryptedVault._derive(secret, salt)).encrypt(
            nonce, data_key, MAGIC + salt)
        return salt + nonce + wrapped

    @staticmethod
    def _encode(data, data_key, pw_wrap, rc_wrap):
        EncryptedVault._validate(data)
        nonce = secrets.token_bytes(NONCE_LENGTH)
        header = MAGIC + pw_wrap + rc_wrap + nonce
        plaintext = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        return header + AESGCM(data_key).encrypt(nonce, plaintext, header)

    def create(self, password, data):
        require_crypto()
        if self.exists():
            raise StorageError('O cofre já existe; a criação não pode substituí-lo.')
        self._validate(data)
        key = secrets.token_bytes(KEY_LENGTH)
        recovery_code = secrets.token_urlsafe(32)
        pw_wrap = self._wrap_key(key, password)
        rc_wrap = self._wrap_key(key, recovery_code)
        blob = self._encode(data, key, pw_wrap, rc_wrap)
        _write_bytes(self.path, blob)
        self._revision = hashlib.sha256(blob).digest()
        self._key, self._pw_wrap, self._rc_wrap, self._data = key, pw_wrap, rc_wrap, deepcopy(data)
        return recovery_code

    def _open(self, secret, recovery=False):
        require_crypto()
        if not self.exists():
            raise StorageError('Cofre criptografado não encontrado.')
        try:
            blob = self.path.read_bytes()
            wrap_size = SALT_LENGTH + NONCE_LENGTH + WRAPPED_LENGTH
            header_size = len(MAGIC) + wrap_size * 2 + NONCE_LENGTH
            if len(blob) < header_size + 16 or not blob.startswith(MAGIC):
                raise StorageError('Formato do cofre inválido ou arquivo truncado.')
            pw_wrap = blob[len(MAGIC):len(MAGIC) + wrap_size]
            rc_wrap = blob[len(MAGIC) + wrap_size:len(MAGIC) + wrap_size * 2]
            wrapped = rc_wrap if recovery else pw_wrap
            salt = wrapped[:SALT_LENGTH]
            nonce = wrapped[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
            sealed_key = wrapped[SALT_LENGTH + NONCE_LENGTH:]
            try:
                key = AESGCM(self._derive(secret, salt)).decrypt(nonce, sealed_key, MAGIC + salt)
                header = blob[:header_size]
                data = json.loads(AESGCM(key).decrypt(
                    header[-NONCE_LENGTH:], blob[header_size:], header).decode('utf-8'))
            except InvalidTag as exc:
                raise StorageError('Credencial incorreta ou cofre alterado/corrompido. '
                                   'Os arquivos não foram modificados.') from exc
            self._validate(data)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise StorageError(f'Falha ao ler o cofre: {exc}') from exc
        self._key, self._pw_wrap, self._rc_wrap, self._data = key, pw_wrap, rc_wrap, data
        self._revision = hashlib.sha256(blob).digest()

    def unlock(self, password):
        self._open(password)

    def unlock_recovery(self, recovery_code):
        self._open(recovery_code, recovery=True)

    def section(self, name):
        if not self.unlocked:
            raise VaultLockedError('Cofre bloqueado. Informe a senha do Admin Final.')
        return deepcopy(self._data[name])

    def _check_revision(self):
        try:
            current = hashlib.sha256(self.path.read_bytes()).digest()
        except OSError as exc:
            raise StorageError('Não foi possível verificar a versão atual do cofre.') from exc
        if current != self._revision:
            raise StorageError('O cofre foi alterado externamente; recarregue a aplicação para evitar sobrescrever dados.')

    def save_sections(self, updates):
        if not self.unlocked:
            raise VaultLockedError('Cofre bloqueado.')
        if not set(updates).issubset(FILES):
            raise StorageError('Seção de armazenamento desconhecida.')
        candidate = deepcopy(self._data)
        for name, value in updates.items():
            candidate[name] = deepcopy(value)
        self._check_revision()
        blob = self._encode(candidate, self._key, self._pw_wrap, self._rc_wrap)
        _write_bytes(self.path, blob)
        self._data = candidate
        self._revision = hashlib.sha256(blob).digest()

    def rekey(self, new_password, updates=None):
        """Altera senha, mantém o código de recuperação e grava todos os dados atomicamente."""
        if not self.unlocked:
            raise VaultLockedError('Cofre bloqueado.')
        candidate = deepcopy(self._data)
        for name, value in (updates or {}).items():
            if name not in FILES:
                raise StorageError('Seção de armazenamento desconhecida.')
            candidate[name] = deepcopy(value)
        pw_wrap = self._wrap_key(self._key, new_password)
        self._check_revision()
        blob = self._encode(candidate, self._key, pw_wrap, self._rc_wrap)
        _write_bytes(self.path, blob)
        self._pw_wrap, self._data = pw_wrap, candidate
        self._revision = hashlib.sha256(blob).digest()


class VaultCsvRepository:
    def __init__(self, vault, filename, columns, optional_columns=()):
        self.vault, self.filename = vault, filename
        self.columns = tuple(columns)
        self.optional_columns = frozenset(optional_columns)

    def load(self):
        rows = self.vault.section(self.filename)
        mandatory = set(self.columns) - self.optional_columns
        for row in rows:
            if not mandatory.issubset(row) or not set(row).issubset(self.columns):
                raise StorageError(f'Colunas inválidas no cofre: {self.filename}')
        return [{col: (row.get(col) or '').strip() for col in self.columns} for row in rows]

    def save(self, rows):
        self.vault.save_sections({self.filename: rows})


class VaultJsonRepository:
    def __init__(self, vault, filename):
        self.vault, self.filename = vault, filename

    def load(self):
        rows = self.vault.section(self.filename)
        required = {'Id', 'NomeCompleto', 'NomeExibicao', 'Email', 'CPF', 'Cargo',
                    'SenhaSalt', 'SenhaHash', 'Palavras'}
        if any(not required.issubset(row) for row in rows):
            raise StorageError('Campos de usuários obrigatórios ausentes no cofre.')
        return rows

    def save(self, rows):
        self.vault.save_sections({self.filename: rows})
