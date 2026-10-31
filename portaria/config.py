"""Contratos legados de dados e regras operacionais compartilhadas.

Temas e navegação pertencem à apresentação; papéis/capacidades pertencem a
portaria.domain.permissions. Não mantenha duas tabelas de permissões.
"""
from datetime import timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
FORMATO_DATA = '%d/%m/%Y'
FORMATO_HORA = '%H:%M'
FORMATO_DATA_HORA = FORMATO_DATA + ' ' + FORMATO_HORA
FORMATO_CRIACAO = '%d/%m/%Y %H:%M:%S'
TIPOS_ACESSO = ['Visitante', 'Morador', 'Entregador', 'Funcionário']
VALIDADE_TEMPORARIO = timedelta(hours=24)
CABECALHO = ['Id', 'Nome', 'Tipo', 'Entrada', 'Saida']
CABECALHO_AUDITORIA = ['Quando', 'Acao', 'Id', 'Nome', 'Campo', 'Anterior', 'Novo', 'Usuario']
CABECALHO_TIPOS_TEMP = ['Tipo', 'CriadoEm']
ARQUIVO = DATA_DIR / 'registros_portaria.csv'
ARQUIVO_AUDITORIA = DATA_DIR / 'auditoria_portaria.csv'
ARQUIVO_TIPOS_TEMP = DATA_DIR / 'tipos_temporarios.csv'
ARQUIVO_USUARIOS = DATA_DIR / 'usuarios_portaria.json'
CARGO_FINAL, CARGO_ADM, CARGO_USUARIO = 'Admin Final', 'Adm', 'Usuário'
CARGOS = [CARGO_FINAL, CARGO_ADM, CARGO_USUARIO]
MAX_TENTATIVAS = 5
MINUTOS_BLOQUEIO = 5
# Valores de PBKDF2 mantidos para verificação de hashes de contas existentes.
ITERACOES_SENHA = 200_000
ITERACOES_PALAVRA = 50_000
