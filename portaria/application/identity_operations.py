"""Casos de uso de identidade, autorização e recuperação protegida."""
from datetime import datetime, timedelta
import math
import secrets
from ..config import (CARGO_FINAL, CARGO_ADM, CARGO_USUARIO, CARGOS, FORMATO_CRIACAO,
                      MAX_TENTATIVAS, MINUTOS_BLOQUEIO, ITERACOES_SENHA, ITERACOES_PALAVRA)
from ..domain.validation import (ValidationError, PermissionDenied, normalizar,
                                 cpf_valido, email_valido, erro_senha)
from ..domain.security import conferir_hash, criar_hash, montar_usuario
from ..infrastructure.storage import StorageError
from ..infrastructure.vault import FILES


class IdentityOperations:
    """Operações ligadas ao contexto PortariaService."""

    def _evento_usuario(self, acao, usuario, campo, anterior, novo):
        return {'Quando': datetime.now().strftime(FORMATO_CRIACAO), 'Acao': acao,
                'Id': usuario['Id'], 'Nome': usuario['NomeExibicao'], 'Campo': campo,
                'Anterior': anterior, 'Novo': novo, 'Usuario': self.nome_sessao()}

    def _persistir_usuarios_auditoria(self, novos_usuarios, eventos):
        if self.cofre.unlocked:
            self.cofre.save_sections({FILES[3]: novos_usuarios,
                                     FILES[1]: self.auditoria + eventos})
            self.usuarios = novos_usuarios
            self.auditoria = self.auditoria + eventos
        else:
            # Fluxo de legado; a UI exige migração antes de autenticar.
            self.usuarios_repo.save(novos_usuarios)
            self.usuarios = novos_usuarios

    def achar_usuario_por_login(self, texto):
        t = texto.strip()
        if '@' in t:
            return next((u for u in self.usuarios if u.get('Email', '').lower() == t.lower()), None)
        from ..domain.validation import so_digitos
        d = so_digitos(t)
        return next((u for u in self.usuarios if d and u.get('CPF') == d), None)

    def achar_usuario_por_cpf(self, cpf):
        from ..domain.validation import so_digitos
        d = so_digitos(cpf)
        return next((u for u in self.usuarios if d and u.get('CPF') == d), None)

    def achar_usuario_por_id(self, id_usuario):
        return next((u for u in self.usuarios if u['Id'] == id_usuario), None)

    def minutos_bloqueio_restantes(self, u):
        if not u.get('BloqueadoAte'):
            return 0
        try:
            ate = datetime.strptime(u['BloqueadoAte'], FORMATO_CRIACAO)
        except (ValueError, TypeError):
            return 0
        segundos = (ate - datetime.now()).total_seconds()
        return int(math.ceil(segundos / 60)) if segundos > 0 else 0

    def _atualizar_usuario(self, usuario, **alteracoes):
        novos = [{**u, **alteracoes} if u['Id'] == usuario['Id'] else u for u in self.usuarios]
        self.usuarios_repo.save(novos)
        self.usuarios = novos
        atualizado = self.achar_usuario_por_id(usuario['Id'])
        if self.sessao['usuario'] and self.sessao['usuario']['Id'] == usuario['Id']:
            self.sessao['usuario'] = atualizado
        return atualizado

    def registrar_falha(self, u):
        tentativas = int(u.get('Tentativas', 0)) + 1
        bloqueado = u.get('BloqueadoAte', '')
        if tentativas >= MAX_TENTATIVAS:
            tentativas = 0
            bloqueado = (datetime.now() + timedelta(minutes=MINUTOS_BLOQUEIO)).strftime(FORMATO_CRIACAO)
        return self._atualizar_usuario(u, Tentativas=tentativas, BloqueadoAte=bloqueado)

    def limpar_falhas(self, u):
        return self._atualizar_usuario(u, Tentativas=0, BloqueadoAte='')

    def autenticar(self, login, senha):
        u = self.achar_usuario_por_login(login)
        if u and self.minutos_bloqueio_restantes(u):
            raise ValidationError('Conta bloqueada. Tente novamente mais tarde.')
        if u is None:
            raise ValidationError('E-mail/CPF ou senha incorretos.')
        try:
            credenciais_ok = bool(
                conferir_hash(senha, u['SenhaSalt'], u['SenhaHash'], ITERACOES_SENHA))
        except (ValueError, TypeError, KeyError) as exc:
            raise StorageError('Dados de credenciais inválidos no arquivo de usuários.') from exc
        if not credenciais_ok:
            if u:
                self.registrar_falha(u)
            raise ValidationError('E-mail/CPF ou senha incorretos.')
        self.sessao['usuario'] = self.limpar_falhas(u)
        return self.sessao['usuario']

    def cadastrar_usuario(self, nome, exibicao, email, cpf, cargo, senha, palavras):
        from ..domain.validation import so_digitos
        nome = ' '.join(nome.split())
        exibicao = ' '.join(exibicao.split())
        email = email.strip().lower()
        cpf = so_digitos(cpf)
        if not (2 <= len(nome.split()) and len(nome) <= 100) or any(ord(c) < 32 for c in nome):
            raise ValidationError('Nome completo inválido (até 100 caracteres).')
        if len(email) > 150:
            raise ValidationError('E-mail com mais de 150 caracteres.')
        if self.usuarios:
            self.exigir('usuarios')
        elif cargo != CARGO_FINAL:
            raise PermissionDenied('O primeiro usuário deve ser Admin Final.')
        if len(nome.split()) < 2 or not exibicao.strip() or len(exibicao) > 25:
            raise ValidationError('Informe nome completo e nome para exibição (até 25 caracteres).')
        if not email_valido(email) or any(u['Email'].lower() == email.lower() for u in self.usuarios):
            raise ValidationError('E-mail inválido ou já cadastrado.')
        if not cpf_valido(cpf) or any(u['CPF'] == cpf for u in self.usuarios):
            raise ValidationError('CPF inválido ou já cadastrado.')
        if cargo not in CARGOS or (self.usuarios and cargo == CARGO_FINAL):
            raise ValidationError('Cargo inválido.')
        if erro_senha(senha):
            raise ValidationError(erro_senha(senha))
        import re
        if len(palavras) != 3 or any(re.fullmatch(r'[a-zà-ÿ]{4,20}', p) is None for p in palavras) or len({normalizar(p) for p in palavras}) < 3:
            raise ValidationError('Informe 3 palavras-chave diferentes, somente letras (4 a 20).')
        novo = montar_usuario(nome, exibicao, email, cpf, cargo, senha, palavras)
        novos = self.usuarios + [novo]
        if not self.usuarios and cargo == CARGO_FINAL:
            # Nunca gravar a senha ou dados do primeiro Admin Final em JSON claro.
            dados = dict(zip(FILES, (self.registros, self.auditoria, self.tipos_temporarios, novos)))
            self.chave_recuperacao = self.cofre.create(senha, dados)
            self._usar_cofre()
            self._eliminar_legados_residuais()
        else:
            evento = self._evento_usuario('USUÁRIO', novo, 'Cadastro', '—', novo['Cargo'])
            self._persistir_usuarios_auditoria(novos, [evento])
        if cargo == CARGO_FINAL:
            self.usuarios = novos
        return novo

    def solicitar_recuperacao(self, cpf, email, respostas):
        """Valida os três desafios, com rate limit durável e autorização efêmera."""
        u = self.achar_usuario_por_cpf(cpf)
        if not u or u.get('Email', '').casefold() != email.strip().casefold():
            if u and not self.minutos_bloqueio_restantes(u):
                self.registrar_falha(u)
            raise ValidationError('Dados de recuperação não conferem.')
        if self.minutos_bloqueio_restantes(u):
            raise ValidationError('Conta temporariamente bloqueada.')
        if not isinstance(respostas, (list, tuple)) or len(respostas) != 3:
            raise ValidationError('Responda às três perguntas.')
        from ..config import ITERACOES_PALAVRA
        if len(u.get('Palavras', ())) != 3:
            raise StorageError('Desafios de recuperação incompletos.')
        corretas = False
        try:
            corretas = all(conferir_hash(normalizar(r), p['Salt'], p['Hash'], ITERACOES_PALAVRA)
                           for r, p in zip(respostas, u['Palavras']))
        except (KeyError, ValueError, TypeError) as exc:
            raise StorageError('Desafios de recuperação inválidos.') from exc
        if not corretas:
            self.registrar_falha(u)
            raise ValidationError('Respostas incorretas. Tentativa registrada.')
        token = secrets.token_urlsafe(32)
        self._recovery_grants[token] = (u['Id'], datetime.now() + timedelta(minutes=5))
        return token

    def redefinir_senha(self, u, nova, *, recovery_token=None):
        atual = self.achar_usuario_por_id(u.get('Id', '')) if isinstance(u, dict) else None
        if atual is None:
            raise ValidationError('Usuário não encontrado.')
        autorizado = bool(self.sessao['usuario'] and self.sessao['usuario']['Id'] == atual['Id'])
        if recovery_token:
            grant = self._recovery_grants.get(recovery_token)
            autorizado = autorizado or bool(grant and grant[0] == atual['Id'] and datetime.now() <= grant[1])
        if not autorizado:
            raise PermissionDenied('Recuperação de senha não autorizada.')
        u = atual
        if erro_senha(nova):
            raise ValidationError(erro_senha(nova))
        salt, hash_ = criar_hash(nova, ITERACOES_SENHA)
        if u['Cargo'] == CARGO_FINAL and self.cofre.unlocked:
            # Redefinição de senha do Admin Final recriptografa todo o cofre.
            novos = [{**x, 'SenhaSalt': salt, 'SenhaHash': hash_, 'Tentativas': 0,
                      'BloqueadoAte': ''} if x['Id'] == u['Id'] else x for x in self.usuarios]
            self.cofre.rekey(nova, {FILES[3]: novos})
            self.usuarios = novos
            if self.sessao['usuario'] and self.sessao['usuario']['Id'] == u['Id']:
                self.sessao['usuario'] = self.achar_usuario_por_id(u['Id'])
        else:
            self._atualizar_usuario(u, SenhaSalt=salt, SenhaHash=hash_, Tentativas=0, BloqueadoAte='')
        if recovery_token:
            self._recovery_grants.pop(recovery_token, None)

    def desbloquear_usuario(self, usuario):
        self.exigir('usuarios')
        atual = self.achar_usuario_por_id(usuario.get('Id', ''))
        if atual is None:
            raise ValidationError('Usuário não encontrado.')
        novos = [{**x, 'Tentativas': 0, 'BloqueadoAte': ''} if x['Id'] == atual['Id'] else x
                 for x in self.usuarios]
        self._persistir_usuarios_auditoria(novos, [self._evento_usuario(
            'DESBLOQUEIO', atual, 'Bloqueio', atual.get('BloqueadoAte', '') or '—', 'Conta ativa')])
        return self.achar_usuario_por_id(atual['Id'])

    def alterar_cargo(self, u, cargo):
        self.exigir('usuarios')
        u = self.achar_usuario_por_id(u.get('Id', '')) if isinstance(u, dict) else None
        if u is None:
            raise ValidationError('Usuário não encontrado.')
        if u['Cargo'] == CARGO_FINAL or cargo not in (CARGO_ADM, CARGO_USUARIO):
            raise ValidationError('Não é permitido alterar esse cargo.')
        novos = [{**x, 'Cargo': cargo} if x['Id'] == u['Id'] else x for x in self.usuarios]
        self._persistir_usuarios_auditoria(novos, [self._evento_usuario(
            'PAPEL', u, 'Papel de acesso', u['Cargo'], cargo)])

    def excluir_usuario(self, u):
        self.exigir('usuarios')
        u = self.achar_usuario_por_id(u.get('Id', '')) if isinstance(u, dict) else None
        if u is None:
            raise ValidationError('Usuário não encontrado.')
        if u['Cargo'] == CARGO_FINAL:
            raise ValidationError('O Admin Final não pode ser excluído.')
        novos = [x for x in self.usuarios if x['Id'] != u['Id']]
        self._persistir_usuarios_auditoria(novos, [self._evento_usuario(
            'EXCLUSÃO DE USUÁRIO', u, 'Conta', u['Cargo'], 'Excluída')])

    def sair(self):
        self.sessao['usuario'] = None
        self._recovery_grants.clear()

