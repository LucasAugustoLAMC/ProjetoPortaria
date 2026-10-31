"""Repositórios CSV/JSON com escrita atômica e leitura fail-closed.

Nenhuma falha de parsing deve ser confundida com uma base vazia: isso poderia
fazer o próximo cadastro sobrescrever dados válidos.
"""
import csv
import json
import os
import tempfile
from pathlib import Path

class StorageError(RuntimeError):
    pass


def _atomic_write(path, writer, *, encoding='utf-8'):
    path = Path(path)
    tmp_name = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', newline='', encoding=encoding,
                                         dir=path.parent, prefix=f'.{path.name}.',
                                         suffix='.tmp', delete=False) as stream:
            tmp_name = stream.name
            writer(stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
    except (OSError, ValueError, TypeError) as exc:
        raise StorageError(f'Falha ao salvar {path.name}: {exc}') from exc
    finally:
        if tmp_name is not None and os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


class CsvRepository:
    def __init__(self, path, columns, optional_columns=()):
        self.path = Path(path)
        self.columns = tuple(columns)
        self.optional_columns = frozenset(optional_columns)

    def load(self):
        if not self.path.exists():
            return []
        try:
            with self.path.open(newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError('cabeçalho ausente')
                # Legado de registros anterior à coluna Id é aceito.
                mandatory = set(self.columns) - self.optional_columns
                if not mandatory.issubset(reader.fieldnames):
                    raise ValueError('colunas obrigatórias ausentes')
                if set(reader.fieldnames) - set(self.columns):
                    raise ValueError('colunas desconhecidas; importação interrompida para evitar perda de dados')
                result = []
                for row in reader:
                    if None in row:  # colunas adicionais: dado possivelmente truncado/corrompido
                        raise ValueError('linha com colunas extras')
                    result.append({col: (row.get(col) or '').strip() for col in self.columns})
                return result
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            raise StorageError(f'Falha ao ler {self.path.name}: {exc}') from exc

    def save(self, rows):
        def writer(f):
            out = csv.DictWriter(f, fieldnames=self.columns)
            out.writeheader()
            out.writerows(rows)
        _atomic_write(self.path, writer, encoding='utf-8-sig')


class JsonRepository:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return []
        try:
            with self.path.open(encoding='utf-8') as f:
                result = json.load(f)
            if not isinstance(result, list) or not all(isinstance(row, dict) for row in result):
                raise ValueError('estrutura de usuários inválida')
            required = {'Id', 'NomeCompleto', 'NomeExibicao', 'Email', 'CPF', 'Cargo',
                        'SenhaSalt', 'SenhaHash', 'Palavras'}
            if any(not required.issubset(row) for row in result):
                raise ValueError('campos de usuário obrigatórios ausentes')
            return result
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise StorageError(f'Falha ao ler {self.path.name}: {exc}') from exc

    def save(self, rows):
        _atomic_write(self.path, lambda f: json.dump(rows, f, ensure_ascii=False, indent=2))
