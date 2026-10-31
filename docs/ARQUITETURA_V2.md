# Arquitetura — Portaria 2.0

## Objetivo

UI independente de domínio e persistência; preservar **cofre v2 binário** e os dados antigos. Não alterar o mecanismo criptográfico sem uma migração explícita e testada.

## Dependências

```text
Presentation (Tk/ttk)
    |
    v
Application (PortariaService: fachada)
    |-- AccessOperations
    |-- IdentityOperations
    |-- VaultLifecycle
    |
    +----> Domain (validadores, políticas RBAC, hash)
    |
    +----> Infrastructure (EncryptedVault, adaptadores CSV/JSON, lock)
```

- `PortariaService`: estado em memória, sessão e dependências dos repositórios. É uma fachada de compatibilidade. Usa classes de operações separadas por responsabilidade, sem herança de widgets.
- `AccessOperations`: casos de uso de cadastro, saída, edição em lote, exclusão e tipos de acesso. A atualização multicoluna é persistida em um único commit junto com os eventos gerados.
- `IdentityOperations`: login, tentativas/bloqueio, cadastro e manutenção de usuários, recuperação com grant efêmero e auditoria da gestão de identidades.
- `VaultLifecycle`: desbloqueio, migração legada, montagem dos repositórios e carregamento fail-closed.
- `Domain`: regras puras de CPF, datas/horas, validação e mapeamento das capacidades de cada papel.
- `Infrastructure`: protege a base local, verifica a revisão e grava criptografia autenticada sem criar plaintext temporário.

## Fluxos críticos

### Cadastro idempotente

1. Tela cria UUIDv4 para a intenção de cadastro.
2. Serviço valida sessão/permissão, campos e tipo.
3. UUIDv5 determinístico gera o `Id` a partir do token (o token **não** é conteúdo de nome/data).
4. Requisição repetida com mesmos campos retorna o registro anterior; com campos diferentes gera erro. Após exclusão, auditoria com ID impede reintroduzir a mesma intenção.
5. Em sucesso, a tela limpa o formulário e cria **novo token**. Falha mantém token para repetição sem duplicação.

A idempotência é garantida **para uma mesma chave de operação**; duas ações distintas com chaves diferentes ainda podem gerar registros iguais. Isso é proposital: duas entradas legítimas podem ter o mesmo nome e horário.

### Persistência e concorrência

1. O executável adquire um lock do SO sobre `dados_portaria.lock` antes de abrir a UI.
2. Na abertura, o cofre é autenticado por AES-GCM e a revisão (SHA-256 dos bytes) é retida na memória.
3. Antes de cada escrita, a revisão em disco é comparada; divergência cancela a operação.
4. Candidatos são serializados e cifrados em memória. Arquivo temporário **criptografado** é sincronizado e substitui o cofre por rename atômico.
5. Estado da aplicação só é publicado após commit. Registros e auditoria, ou usuários e auditoria, são salvos como um conjunto.

Limite: não há transação entre cofre e arquivos legados durante importação. O processo de migração salva o cofre íntegro antes da limpeza dos originais. O lock só vale para aplicações que o respeitam, e revisão + replace não são um mecanismo CAS do SO.

### Autorização

Permissões `Action` são enums em `domain/permissions.py`, mapeadas a papeis. `PortariaService.exigir()` é invocado dentro de **todas as operações sensíveis**. A barra lateral reflete permissões, mas não é o controle de segurança.

## Por que Tk/ttk nesta edição?

Mudança de toolkit não é uma condição para desacoplar a UI. A versão 2 mantém widgets nativos, elimina o título de janela customizado, moderniza cores, dimensões e disposição, permite três temas e pode ser testada em display virtual sem instalar bibliotecas gráficas externas. A eventual adoção de Qt seria substituição da camada `presentation_v2`, sem mudanças no contrato dos casos de uso.

## Próximos passos opcionais

- Isolar operações em objetos injetados (eliminar mixins compartilhando `self` da fachada).
- Evitar recifrar o cofre inteiro em toda operação: migrar explicitamente para um formato transacional caso o volume cresça.
- Recuperação de contas com fator independente, troca de senha por fluxo autenticado e modelo de ameaças atualizado.
- Testes end-to-end adicionais com Windows e validação de leitores de tela/alto contraste.
