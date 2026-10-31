# Segurança — modelo de ameaças e limites

**O cofre v2 não é um banco multiusuário nem um mecanismo contra administradores do sistema operacional.**

## Garantias implementadas

- Dados de registros, auditoria, tipos e usuários protegidos em repouso por AES-256-GCM; derivações PBKDF2 e wrapping da chave já existentes.
- Autenticação por credenciais individuais, bloqueio por tentativas e permissão por papel validada nos métodos de aplicação.
- Submissões de cadastro idempotentes mediante UUIDv4 do comando; token renovado em novo cadastro.
- Auditoria de operações de registro e administração de usuários; dados e auditoria persistem juntos no cofre.
- Escrita atômica do cofre e detecção de mudança externa entre leitura e gravação.
- Bloqueio local de instância com flock/locking, para evitar duas aplicações oficiais gravando na mesma base.
- Redefinição não autenticada exige token efêmero após três desafios e não usa apenas uma checagem visual.

## O que não pode ser garantido

- Não há proteção contra edição do próprio executável ou scripts, injeção no processo, administrador/root local, vazamento de memória ou exportação do cofre para força bruta offline.
- A criptografia autenticada detecta alteração de bytes, mas **não detecta rollback de um arquivo antigo válido**.
- A configuração de autenticação por palavras-chave em 4 alternativas tem baixa entropia; o bloqueio de 5 tentativas por 5 minutos é limitado contra adversários persistentes e não impede ataques offline ao arquivo.
- AES-GCM não é backup nem controle de disponibilidade. Apagamento ou corrupção deliberada do arquivo pode indisponibilizar a aplicação.
- A chave de dados permanece na memória após desbloqueio. Funcionários compartilham a instância já desbloqueada, com separação apenas nas operações da aplicação.
- `os.replace` é atômico no mesmo volume conforme o sistema de arquivos, mas não constitui transação entre volumes nem garantia absoluta contra falha física de disco.
- APIs locais e testes diretos podem contornar a UI; as regras de autorização devem continuar na aplicação.

## Operação recomendada

1. Restrinja permissão de leitura e escrita da pasta dos dados pelo SO; evite executar a aplicação com privilégio administrativo.
2. Proteja o acesso ao código-fonte e ao ambiente Python nas estações de uso.
3. Faça backups periódicos do cofre **com a aplicação fechada** e teste periodicamente a restauração.
4. Guarde senha administrativa e código de recuperação em locais distintos e protegidos.
5. Não publique `dados_portaria.enc`, os CSV/JSON legados, logs ou backups no Git.
6. Valide a interface em Windows com contas e dados de teste antes de atualizar um ambiente real.
