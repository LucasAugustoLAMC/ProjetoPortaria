"""Casos de uso de registros e tipos de acesso, independentes da UI."""
from datetime import datetime, timedelta
import uuid
from ..config import (TIPOS_ACESSO, VALIDADE_TEMPORARIO, FORMATO_DATA_HORA, FORMATO_CRIACAO)
from ..domain.validation import (ValidationError, PermissionDenied, novo_id, converter_data_hora,
                                 validar_ordem, normalizar)
from ..infrastructure.storage import StorageError
from ..infrastructure.vault import FILES


class AccessOperations:
    """Operações ligadas ao contexto PortariaService."""

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
        self.exigir('cadastrar')
        if not isinstance(nome, str) or len(nome) > 60 or any(ord(c) < 32 for c in nome):
            raise ValidationError('Tipo de acesso inválido (máximo 60 caracteres).')
        nome = ' '.join(nome.split())
        if not nome:
            raise ValidationError('Informe o nome do tipo temporário.')
        for tipo in TIPOS_ACESSO + self.tipos_temporarios_ativos():
            if normalizar(tipo) == normalizar(nome):
                return tipo
        novo = self.tipos_temporarios + [{'Tipo': nome, 'CriadoEm': datetime.now().strftime(FORMATO_CRIACAO)}]
        evento = {'Quando': datetime.now().strftime(FORMATO_CRIACAO), 'Acao': 'TIPO DE ACESSO',
                  'Id': '', 'Nome': nome, 'Campo': 'Tipo temporário', 'Anterior': '—',
                  'Novo': nome, 'Usuario': self.nome_sessao()}
        if self.cofre.unlocked:
            self.cofre.save_sections({FILES[2]: novo, FILES[1]: self.auditoria + [evento]})
            self.auditoria = self.auditoria + [evento]
        else:
            self.tipos_repo.save(novo)
        self.tipos_temporarios = novo
        return nome

    def _validar_registro(self, reg):
        if not isinstance(reg['Nome'], str) or not reg['Nome'].strip():
            raise ValidationError('Informe o nome da pessoa.')
        if any(ord(c) < 32 or ord(c) == 127 for c in reg['Nome']):
            raise ValidationError('O nome contém caracteres de controle inválidos.')
        if len(reg['Nome']) > 100:
            raise ValidationError('O nome deve conter no máximo 100 caracteres.')
        if not reg['Tipo'].strip():
            raise ValidationError('Informe um tipo de acesso.')
        if converter_data_hora(reg['Entrada']) is None:
            raise ValidationError('Data ou hora de entrada inválida.')
        if reg['Saida'] and converter_data_hora(reg['Saida']) is None:
            raise ValidationError('Data ou hora de saída inválida.')
        erro = validar_ordem(reg['Entrada'], reg['Saida'])
        if erro:
            raise ValidationError(erro)

    def cadastrar(self, nome, tipo, entrada, saida='', *, operation_id=None):
        self.exigir('cadastrar')
        if tipo not in TIPOS_ACESSO + self.tipos_temporarios_ativos():
            raise ValidationError('Selecione um tipo de acesso válido (temporários expiram em 24 horas).')
        novo = {'Id': novo_id(), 'Nome': nome.strip(), 'Tipo': tipo,
                'Entrada': entrada, 'Saida': saida}
        self._validar_registro(novo)
        if operation_id is not None:
            # Identificador determinado pelo token do comando e persistido no Id
            # existente, sem alterar o esquema ou o formato do cofre v2.
            try:
                token = str(uuid.UUID(str(operation_id)))
            except (ValueError, AttributeError, TypeError) as exc:
                raise ValidationError('Identificador de operação inválido.') from exc
            novo['Id'] = uuid.uuid5(uuid.NAMESPACE_URL, 'portaria/registro/' + token).hex
            existente = self.buscar_registro(novo['Id'])
            if existente:
                if all(existente.get(k) == novo[k] for k in ('Nome', 'Tipo', 'Entrada', 'Saida')):
                    return existente
                raise ValidationError('A operação já foi processada com outros dados.')
            if any(e['Id'] == novo['Id'] and e['Acao'] == 'EXCLUSÃO' for e in self.auditoria):
                raise ValidationError('A operação já foi concluída e seu registro foi excluído.')
        while operation_id is None and self.buscar_registro(novo['Id']):
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

    def atualizar_registro(self, id_registro, alteracoes):
        """Edição multicoluna em um único commit (incluindo todos os eventos)."""
        reg = self.buscar_registro(id_registro)
        if not reg:
            raise ValidationError('Registro não encontrado.')
        if not isinstance(alteracoes, dict) or not set(alteracoes).issubset({'Nome','Tipo','Entrada','Saida'}):
            raise ValidationError('Campos de edição inválidos.')
        updates = {campo: valor for campo, valor in alteracoes.items() if reg[campo] != valor}
        if not updates:
            return False
        if set(updates) == {'Saida'} and not reg['Saida']:
            self.exigir('saida')
        else:
            self.exigir('editar')
        novo = {**reg, **updates}
        if 'Tipo' in updates and novo['Tipo'] not in TIPOS_ACESSO + self.tipos_temporarios_ativos():
            raise ValidationError('Tipo de acesso inválido ou expirado.')
        self._validar_registro(novo)
        rotulos = {'Nome':'Nome', 'Tipo':'Tipo de acesso','Entrada':'Entrada','Saida':'Saída'}
        eventos = [self._evento('EDIÇÃO', reg, rotulos[campo], reg[campo], valor)
                   for campo, valor in updates.items() if campo != 'Saida' or reg['Saida']]
        self._persistir_registros_auditoria(
            [novo if r['Id'] == id_registro else r for r in self.registros], eventos)
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

