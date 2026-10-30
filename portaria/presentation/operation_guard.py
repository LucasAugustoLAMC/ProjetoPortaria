"""Proteção da UI contra comandos de escrita reentrantes (duplo clique/Enter)."""
from functools import wraps


def proteger_operacao_registro(func):
    """Uma operação de registro por vez, incluindo enquanto um diálogo está aberto.

    O Tkinter permite reentrância quando uma janela modal executa um loop aninhado.
    O sinalizador, além do estado visual dos botões, protege esses callbacks.
    """
    @wraps(func)
    def executar(self, *args, **kwargs):
        if getattr(self, '_registro_ocupado', False):
            return None
        self._registro_ocupado = True
        estados = []
        try:
            botoes = [getattr(self, nome, None) for nome in ('btn_cadastrar', 'btn_saida', 'btn_excluir')]
            estados = [(botao, botao.cget('state')) for botao in botoes
                       if botao is not None and botao.winfo_exists()]
            for botao, _estado in estados:
                botao.configure(state='disabled')
            return func(self, *args, **kwargs)
        finally:
            try:
                for botao, estado in estados:
                    if botao.winfo_exists():
                        botao.configure(state=estado)
            finally:
                self._registro_ocupado = False
    return executar
