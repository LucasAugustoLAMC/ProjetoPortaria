"""Validações independentes de interface e disco."""
import re
import unicodedata
import uuid
from datetime import datetime
from ..config import FORMATO_DATA, FORMATO_DATA_HORA, FORMATO_HORA

class ValidationError(ValueError):
    pass

class PermissionDenied(ValidationError):
    pass

def novo_id():
    return uuid.uuid4().hex[:8]

def agora_data():
    return datetime.now().strftime(FORMATO_DATA)

def agora_hora():
    return datetime.now().strftime(FORMATO_HORA)

def converter_data_hora(texto):
    if not isinstance(texto, str) or re.fullmatch(
        r'(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/[0-9]{4} '
        r'([01][0-9]|2[0-3]):[0-5][0-9]', texto) is None:
        return None
    try:
        return datetime.strptime(texto, FORMATO_DATA_HORA)
    except ValueError:
        return None

def normalizar(texto):
    decomposto = unicodedata.normalize('NFD', str(texto).lower())
    return ''.join(c for c in decomposto if unicodedata.category(c) != 'Mn')

def validar_ordem(entrada, saida):
    if not saida:
        return None
    dt_entrada, dt_saida = converter_data_hora(entrada), converter_data_hora(saida)
    if dt_entrada and dt_saida and dt_saida < dt_entrada:
        return 'A saída não pode ser anterior à entrada.'
    return None

def so_digitos(texto):
    return re.sub(r'\D', '', texto)

def cpf_valido(cpf):
    d = so_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10 % 11) % 10 != int(d[n]):
            return False
    return True

def formatar_cpf(texto):
    d = so_digitos(texto)[:11]
    resultado = '.'.join(p for p in (d[0:3], d[3:6], d[6:9]) if p)
    if len(d) > 9:
        resultado += '-' + d[9:]
    return resultado

def mascarar_cpf(d):
    return '***.***.%s-%s' % (d[6:9], d[9:11]) if len(d) == 11 else '—'

def email_valido(email):
    return re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$', email) is not None

def erro_senha(senha):
    if not isinstance(senha, str) or len(senha) > 128:
        return 'A senha deve conter no máximo 128 caracteres.'
    if len(senha) < 8 or not re.search(r'[A-Za-zÀ-ÿ]', senha) or not re.search(r'\d', senha):
        return 'A senha deve ter pelo menos 8 caracteres, com letras e números.'
    return None

from ..config import TIPOS_ACESSO

def eh_temporario(tipo):
    return tipo not in TIPOS_ACESSO
