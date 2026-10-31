# Decisões arquiteturais

## Escopo

O código entregue é um aplicativo de **cadastro de portaria**, não um pipeline de OCR. O objetivo foi separar a aplicação recebida em módulos, sem migrar de Tkinter nem mudar o contrato persistido dos usuários.

## Dependências entre camadas

- `presentation`: conhece `application`, modelos e componentes visuais.
- `application`: conhece validações, segurança e contratos concretos simples de persistência. Pode ser testada sem UI.
- `domain`: regras puras e geração/validação dos dados; desconhece Tkinter e repositórios.
- `infrastructure`: conhece caminhos e formatos; desconhece Tkinter e o fluxo de telas.
- `config`: valores compartilhados que exigem compatibilidade.

A UI está dividida em **mixins por funcionalidade** (`AccessMixin`, `UsersMixin`, etc.) agregados no `PortariaApp`. É uma estratégia de extração incremental para preservar eventos/layout com risco controlado; não é uma arquitetura de plugins nem microserviços. A implementação nova de casos de uso está na `PortariaService`.

## Principais mudanças de comportamento defensivo

1. **Fail closed em corrupção:** um arquivo existente com dados inválidos não é silenciosamente ignorado. Evita que novas operações sobrescrevam histórico preexistente.
2. **Write before publish:** a aplicação não altera os registros de trabalho antes de uma gravação bem-sucedida. Isso corrige situações em que o usuário receberia confirmação apesar de falha de I/O.
3. **Gravação atômica por arquivo:** escreve na mesma pasta, sincroniza e substitui o alvo de uma vez.
4. **Autorizações no caso de uso:** evita que uma chamada acidental por outra tela ignore as permissões.
5. **Observabilidade:** callback inesperado produz log local em vez de falhar silenciosamente.
6. **Máscaras incrementais:** regras puras em `domain/input_masks.py`, aplicadas pelo `Entry` em `presentation/components.py`; entrada manual aceita apenas dígitos ASCII, separadores nos locais corretos e datas/horários possíveis. As regras definitivas do registro continuam no serviço.
7. **Reentrância de registro:** `presentation/operation_guard.py` impede callbacks duplicados ou concorrentes da mesma tela, inclusive durante loops de diálogos do Tkinter. Desabilita botões temporariamente e restaura o estado anterior, inclusive permissões do cargo, em `finally`.

## Decisões preservadas

- Não trocar para SQL, ORM, API, `requests`, bibliotecas de UI ou frameworks externos.
- Não alterar a lógica de hash PBKDF2/iterações/salt, pois os usuários existentes precisam continuar autenticando.
- Não alterar os nomes, colunas ou formatos dos arquivos persistidos.
- Não alterar as permissões entre os três cargos.
- Não auditar a primeira saída, conforme regra anterior; mudanças posteriores e exclusões são auditadas.

## Risco residual

Uma transação entre `registros_portaria.csv` e `auditoria_portaria.csv` não pode ser garantida apenas com `os.replace`. A tentativa de compensação cobre falhas detectadas em execução, mas não desligamento inesperado entre gravações. Sem introduzir uma tecnologia transacional, esse limite permanece. Também não foi implementado bloqueio entre processos. A proteção contra clique repetido não é uma chave de idempotência persistida, portanto não coordena instâncias diferentes e não substitui banco transacional.

## Extensão de segurança: cofre criptografado (posterior à refatoração)

A versão atual **altera intencionalmente o formato persistido** após uma migração: em vez de quatro arquivos legíveis, mantém um único `dados_portaria.enc`. O serviço ainda lê CSV/JSON antigos para migração, preservando os dados, IDs, hashes e regras de autorização.

- **Confidencialidade e integridade:** AES-256-GCM implementado pela biblioteca auditada `cryptography`. O Python padrão não fornece criptografia autenticada equivalente; a nova dependência é necessária para não inventar um algoritmo próprio.
- **Gerenciamento de chave:** uma chave aleatória de 256 bits cifra o cofre. Sua cópia fica protegida por PBKDF2-HMAC-SHA256 derivada da senha do Admin Final; uma segunda cópia é protegida por código de recuperação aleatório, exibido uma vez.
- **Desbloqueio antes do login:** o Admin Final deve fornecer a senha (ou código de recuperação) no início do processo. Só então os usuários se autenticam individualmente; os demais não precisam conhecer a senha do Admin Final durante a sessão aberta. Esse requisito operacional é intencional.
- **Rotação:** redefinir a senha do Admin Final reenvolve a chave de dados e atualiza o hash do usuário no mesmo commit. O código de recuperação continua válido.
- **Migração:** o cofre é escrito primeiro e só depois os arquivos legados são removidos. Um processo interrompido antes da limpeza é retomado no próximo desbloqueio.
- **Atomicidade:** operações que alteram registros e auditoria gravam ambos no mesmo arquivo, eliminando o intervalo de inconsistência da compensação CSV anterior.
- **Limitações:** nenhum mecanismo puramente local impede exclusão, rollback de backups válidos, manipulação do código Python pelo proprietário da máquina ou leitura de dados já desbloqueados em memória. Sem bloqueio entre processos, o cofre não é multiusuário concorrente. Cópias legadas/backup requerem proteção separada.
