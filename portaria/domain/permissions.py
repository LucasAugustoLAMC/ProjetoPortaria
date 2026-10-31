"""Permissões por capacidade, não por visibilidade da tela.

Estas permissões são verificadas nos casos de uso. A interface apenas reflete
as capacidades da sessão, sem substituir a autorização no serviço.
"""
from enum import Enum


class Action(str, Enum):
    VIEW_RECORDS = 'consultar'
    CREATE_RECORD = 'cadastrar'
    CHECKOUT = 'saida'
    EDIT_RECORD = 'editar'
    DELETE_RECORD = 'excluir'
    VIEW_AUDIT = 'auditoria'
    MANAGE_USERS = 'usuarios'


ROLE_ACTIONS = {
    'Admin Final': frozenset(Action),
    'Adm': frozenset(Action) - {Action.MANAGE_USERS},
    'Usuário': frozenset({Action.VIEW_RECORDS, Action.CREATE_RECORD, Action.CHECKOUT}),
}


def allowed(role: str, action: str | Action) -> bool:
    try:
        return Action(action) in ROLE_ACTIONS.get(role, frozenset())
    except ValueError:
        return False
