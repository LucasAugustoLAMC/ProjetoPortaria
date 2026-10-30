"""Máscaras incrementais para data e hora, sem dependência de Tkinter.

Aceitam prefixos válidos durante edição, mas rejeitam letras, emojis,
separadores fora de posição, números fora de faixa e datas completas impossíveis.
"""
from datetime import datetime

MASCARA_DATA = 'dd/mm/aaaa'
MASCARA_HORA = 'hh:mm'


def corresponde_mascara(texto, mascara):
    """Verifica um valor parcial ou completo (os números devem ser ASCII)."""
    if not isinstance(texto, str) or len(texto) > len(mascara):
        return False
    for caractere, posicao in zip(texto, mascara):
        if posicao in 'dmah':
            if caractere not in '0123456789':
                return False
        elif caractere != posicao:
            return False

    if mascara == MASCARA_DATA:
        dia = texto[:2]
        mes = texto[3:5] if len(texto) > 3 else ''
        if dia and int(dia) > (31 if len(dia) == 2 else 3):
            return False
        if len(dia) == 2 and int(dia) == 0:
            return False
        if mes and int(mes) > (12 if len(mes) == 2 else 1):
            return False
        if len(mes) == 2 and int(mes) == 0:
            return False
        if len(texto) == len(mascara):
            try:
                datetime.strptime(texto, '%d/%m/%Y')
            except ValueError:
                return False
    elif mascara == MASCARA_HORA:
        hora = texto[:2]
        minuto = texto[3:5] if len(texto) > 3 else ''
        if hora and int(hora) > (23 if len(hora) == 2 else 2):
            return False
        if minuto and int(minuto) > (59 if len(minuto) == 2 else 5):
            return False
    else:
        raise ValueError('Máscara não suportada')
    return True
