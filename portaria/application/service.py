"""Casos de uso e estado da aplicação, sem dependência de Tkinter.

As operações de um arquivo persistem uma cópia antes de publicar o estado.
"""
from copy import deepcopy
from datetime import datetime, timedelta
import math
from ..config import (ARQUIVO, ARQUIVO_AUDITORIA, ARQUIVO_TIPOS_TEMP, ARQUIVO_USUARIOS,
                      CABECALHO, CABECALHO_AUDITORIA, CABECALHO_TIPOS_TEMP,
                      FORMATO_DATA_HORA, FORMATO_CRIACAO, TIPOS_ACESSO,
                      VALIDADE_TEMPORARIO, CARGO_FINAL, CARGO_ADM, CARGO_USUARIO, CARGOS,
                      PERMISSOES, MAX_TENTATIVAS, MINUTOS_BLOQUEIO, ITERACOES_SENHA)
from ..domain.validation import (ValidationError, PermissionDenied, novo_id, converter_data_hora,
                                 validar_ordem, normalizar, cpf_valido, email_valido, erro_senha)
from ..domain.security import criar_hash, conferir_hash, montar_usuario
from ..infrastructure.storage import CsvRepository, JsonRepository, StorageError
from ..infrastructure.vault import EncryptedVault, VaultCsvRepository, VaultJsonRepository, FILES, VaultLockedError


class PortariaService:
    def __init__(self, data_dir=None):
        if data_dir:
            from pathlib import Path
            base = Path(data_dir)
            paths = [base / x.name for x in (ARQUIVO, ARQUIVO_AUDITORIA, ARQUIVO_TIPOS_TEMP, ARQUIVO_USUARIOS)]
        else:
            paths = [ARQUIVO, ARQUIVO_AUDITORIA, ARQUIVO_TIPOS_TEMP, ARQUIVO_USUARIOS]
        self._plain_paths = paths
        self.cofre = EncryptedVault(paths[0].parent / 'dados_portaria.enc')
        self.registros_repo = CsvRepository(paths[0], CABECALHO, optional_columns=('Id',))
        self.auditoria_repo = CsvRepository(paths[1], CABECALHO_AUDITORIA, optional_columns=('Usuario',))
        self.tipos_repo = CsvRepository(paths[2], CABECALHO_TIPOS_TEMP)
        self.usuarios_repo = JsonRepository(paths[3])
        self.registros = []
        self.auditoria = []
        self.tipos_temporarios = []
        self.usuarios = []
        self.sessao = {'usuario': None}
        self.chave_recuperacao = None  # exibida apenas uma vez; nunca persiste em texto puro

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

    def pode(self, acao):
        u = self.sessao['usuario']
        return bool(u and PERMISSOES.get(u.get('Cargo'), {}).get(acao))

    def exigir(self, acao):
        if not self.pode(acao):
            raise PermissionDenied('Seu cargo não tem permissão para esta ação.')

    def nome_sessao(self):
        u = self.sessao['usuario']
        return u.get('NomeExibicao', '') if u else ''

    def buscar_registro(self, id_registro):
        return next((r for r in self.registros if r['Id'] == id_registro), None)

    def tipos_temporarios_ativos(self):
        now = datetime.now()
        result = []
        for t in self.tipos_temporarios:
            try:
                criado = datetime.strptime(t['CriadoEm'], FORMATO_CRIACAO)
            except (ValueError, KeyError, TypeError):
                continue
            if timedelta(0) <= now - criado < VALIDADE_TEMPORARIO and t['Tipo'] not in result:
                result.append(t['Tipo'])
        return result

    def criar_tipo_temporario(self, nome):
        nome = ' '.join(nome.split())
        if not nome:
            raise ValidationError('Informe o nome do tipo temporário.')
        for tipo in TIPOS_ACESSO + self.tipos_temporarios_ativos():
            if normalizar(tipo) == normalizar(nome):
                return tipo
        novo = self.tipos_temporarios + [{'Tipo': nome, 'CriadoEm': datetime.now().strftime(FORMATO_CRIACAO)}]
        self.tipos_repo.save(novo)
        self.tipos_temporarios = novo
        return nome

    def _validar_registro(self, reg):
        if not reg['Nome'].strip():
            raise ValidationError('Informe o nome da pessoa.')
        if not reg['Tipo'].strip():
            raise ValidationError('Informe um tipo de acesso.')
        if converter_data_hora(reg['Entrada']) is None:
            raise ValidationError('Data ou hora de entrada inválida.')
        if reg['Saida'] and converter_data_hora(reg['Saida']) is None:
            raise ValidationError('Data ou hora de saída inválida.')
        erro = validar_ordem(reg['Entrada'], reg['Saida'])
        if erro:
            raise ValidationError(erro)

    def cadastrar(self, nome, tipo, entrada, saida=''):
        self.exigir('cadastrar')
        if tipo not in TIPOS_ACESSO + self.tipos_temporarios_ativos():
            raise ValidationError('Selecione um tipo de acesso válido (temporários expiram em 24 horas).')
        novo = {'Id': novo_id(), 'Nome': nome.strip(), 'Tipo': tipo,
                'Entrada': entrada, 'Saida': saida}
        self._validar_registro(novo)
        while self.buscar_registro(novo['Id']):
            novo['Id'] = novo_id()
        atualizados = self.registros + [novo]
        self.registros_repo.save(atualizados)
        self.registros = atualizados
        return novo

    def _evento(self, acao, reg, campo, anterior, novo):
        return {'Quando': datetime.now().strftime(FORMATO_CRIACAO), 'Acao': acao,
                'Id': reg['Id'], 'Nome': reg['Nome'], 'Campo': campo,
                'Anterior': anterior, 'Novo': novo, 'Usuario': self.nome_sessao()}

    def _persistir_registros_auditoria(self, novos_registros, novos_eventos):
        # No cofre, registros e auditoria fazem parte do mesmo commit atômico.
        if self.cofre.unlocked:
            self.cofre.save_sections({FILES[0]: novos_registros,
                                     FILES[1]: self.auditoria + novos_eventos})
            self.registros = novos_registros
            self.auditoria = self.auditoria + novos_eventos
            return
        # Compatibilidade com testes/migração de legado ainda não criptografado.
        anterior = self.auditoria
        if novos_eventos:
            self.auditoria_repo.save(anterior + novos_eventos)
        try:
            self.registros_repo.save(novos_registros)
        except StorageError:
            if novos_eventos:
                try:
                    self.auditoria_repo.save(anterior)
                except StorageError as exc:
                    raise StorageError('Registros não salvos; reversão da auditoria também falhou. '
                                       'Verifique os arquivos antes de continuar.') from exc
            raise
        self.registros = novos_registros
        if novos_eventos:
            self.auditoria = anterior + novos_eventos

    def editar(self, id_registro, campo, novo):
        reg = self.buscar_registro(id_registro)
        if reg is None:
            raise ValidationError('Registro não encontrado.')
        if campo not in ('Nome', 'Tipo', 'Entrada', 'Saida'):
            raise ValidationError('Campo de edição inválido.')
        self.exigir('saida' if campo == 'Saida' and not reg['Saida'] else 'editar')
        anterior = reg[campo]
        if anterior == novo:
            return False
        if campo == 'Tipo' and novo not in TIPOS_ACESSO + self.tipos_temporarios_ativos():
            raise ValidationError('Tipo de acesso inválido ou expirado.')
        editado = {**reg, campo: novo}
        self._validar_registro(editado)
        evento = []
        if campo != 'Saida' or anterior != '':
            evento = [self._evento('EDIÇÃO', reg, {'Nome':'Nome','Tipo':'Tipo de acesso',
                         'Entrada':'Entrada','Saida':'Saída'}[campo], anterior, novo)]
        novos = [editado if r['Id'] == id_registro else r for r in self.registros]
        self._persistir_registros_auditoria(novos, evento)
        return True

    def excluir(self, ids):
        self.exigir('excluir')
        ids = set(ids)
        excluidos = [r for r in self.registros if r['Id'] in ids]
        eventos = []
        for r in excluidos:
            resumo = '%s | %s | Entrada: %s | Saída: %s' % (r['Nome'], r['Tipo'], r['Entrada'], r['Saida'] or '—')
            eventos.append(self._evento('EXCLUSÃO', r, 'Registro completo', resumo, '—'))
        if not excluidos:
            return 0
        self._persistir_registros_auditoria([r for r in self.registros if r['Id'] not in ids], eventos)
        return len(excluidos)

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

    def autenticar(self, login, senha, cargo):
        u = self.achar_usuario_por_login(login)
        if u and self.minutos_bloqueio_restantes(u):
            raise ValidationError('Conta bloqueada. Tente novamente mais tarde.')
        try:
            credenciais_ok = bool(u and u.get('Cargo') == cargo and
                                  conferir_hash(senha, u['SenhaSalt'], u['SenhaHash'], ITERACOES_SENHA))
        except (ValueError, TypeError, KeyError) as exc:
            raise StorageError('Dados de credenciais inválidos no arquivo de usuários.') from exc
        if not credenciais_ok:
            if u:
                self.registrar_falha(u)
            raise ValidationError('E-mail/CPF, senha ou cargo incorretos.')
        self.sessao['usuario'] = self.limpar_falhas(u)
        return self.sessao['usuario']

    def cadastrar_usuario(self, nome, exibicao, email, cpf, cargo, senha, palavras):
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
            self.usuarios_repo.save(novos)
        self.usuarios = novos
        return novo

    def redefinir_senha(self, u, nova):
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

    def alterar_cargo(self, u, cargo):
        self.exigir('usuarios')
        if u['Cargo'] == CARGO_FINAL or cargo not in (CARGO_ADM, CARGO_USUARIO):
            raise ValidationError('Não é permitido alterar esse cargo.')
        self._atualizar_usuario(u, Cargo=cargo)

    def excluir_usuario(self, u):
        self.exigir('usuarios')
        if u['Cargo'] == CARGO_FINAL:
            raise ValidationError('O Admin Final não pode ser excluído.')
        novos = [x for x in self.usuarios if x['Id'] != u['Id']]
        self.usuarios_repo.save(novos)
        self.usuarios = novos

    def sair(self):
        self.sessao['usuario'] = None
