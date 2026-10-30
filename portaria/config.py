"""Constantes e formato de armazenamento preservados da versão original."""
from datetime import timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
FORMATO_DATA = "%d/%m/%Y"
FORMATO_HORA = "%H:%M"
FORMATO_DATA_HORA = FORMATO_DATA + " " + FORMATO_HORA
FORMATO_CRIACAO = "%d/%m/%Y %H:%M:%S"
TIPOS_ACESSO = ["Visitante", "Morador", "Entregador", "Funcionário"]
OPCAO_NOVO = "+ Novo tipo temporário..."
VALIDADE_TEMPORARIO = timedelta(hours=24)
CABECALHO = ["Id", "Nome", "Tipo", "Entrada", "Saida"]
CABECALHO_AUDITORIA = ["Quando", "Acao", "Id", "Nome", "Campo", "Anterior", "Novo", "Usuario"]
CABECALHO_TIPOS_TEMP = ["Tipo", "CriadoEm"]
ARQUIVO = DATA_DIR / 'registros_portaria.csv'
ARQUIVO_AUDITORIA = DATA_DIR / 'auditoria_portaria.csv'
ARQUIVO_TIPOS_TEMP = DATA_DIR / 'tipos_temporarios.csv'
ARQUIVO_USUARIOS = DATA_DIR / 'usuarios_portaria.json'
COLUNAS = ["Nome", "Tipo", "Entrada", "Saida"]
ROTULOS = {"Nome": "Nome", "Tipo": "Tipo de acesso", "Entrada": "Entrada", "Saida": "Saída"}
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
CARGO_FINAL, CARGO_ADM, CARGO_USUARIO = "Admin Final", "Adm", "Usuário"
CARGOS = [CARGO_FINAL, CARGO_ADM, CARGO_USUARIO]
PERMISSOES = {
    CARGO_FINAL: {"cadastrar": True, "saida": True, "editar": True, "excluir": True, "auditoria": True, "usuarios": True},
    CARGO_ADM: {"cadastrar": True, "saida": True, "editar": True, "excluir": True, "auditoria": True, "usuarios": False},
    CARGO_USUARIO: {"cadastrar": True, "saida": True, "editar": False, "excluir": False, "auditoria": False, "usuarios": False},
}
MAX_TENTATIVAS = 5
MINUTOS_BLOQUEIO = 5
ITERACOES_SENHA = 200000
ITERACOES_PALAVRA = 50000

# Tema original
BARRA_TITULO_PERSONALIZADA = True
COR_FUNDO = '#F3EFE2'
COR_CARTAO = '#FCFAF3'
COR_CREME = '#EFE8CD'
COR_BORDA = '#D2CBB0'
COR_TITULO = '#2E3A28'
COR_TEXTO_SUAVE = '#7A7864'
COR_INATIVO = '#9A9A86'
COR_PISTACHE_CLARO = '#DCE6C8'
COR_NEUTRO = '#E6E0C8'
COR_PENDENTE = '#F6EBC0'
COR_VERDE = '#7C9A64'
COR_AZUL = '#5F7350'
COR_VERMELHO = '#A8513E'
COR_LARANJA = '#B8862F'
COR_CINZA = '#7A7563'
COR_TEMPORARIO = '#9B5A2E'
COR_TEAL = '#4F6B4A'
COR_MENU = '#4A5A3E'
COR_MENU_BTN = '#5E7050'
COR_MENU_BORDA = '#EDE6CB'
COR_MENU_ATIVO = '#EDE6CB'
COR_MENU_HOVER = '#71855F'
import sys
EH_WINDOWS = sys.platform.startswith('win')
LARGURA_PADRAO, ALTURA_PADRAO = 1100, 720
LARGURA_MINIMA, ALTURA_MINIMA = 980, 640
PAGINAS = [
    ('portaria', '🏠  Portaria', 'Portaria — controle de entrada e saída', None),
    ('usuarios', '👥  Usuários', 'Usuários do sistema', 'usuarios'),
    ('auditoria', '📋  Registro de auditoria', 'Registro de auditoria', 'auditoria'),
    ('novo', '➕  Cadastro de novos administradores', 'Cadastro de novos administradores', 'usuarios'),
]
