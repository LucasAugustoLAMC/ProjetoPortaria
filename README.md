# Portaria 2.0 — controle de acessos

Aplicativo desktop para controlar entradas e saídas de pessoas, consultar auditoria e administrar usuários. **Redesenho da interface e reorganização das regras de negócio**, mantendo o formato do cofre criptografado (`dados_portaria.enc`) da versão anterior.

**Stack:** Python 3.10+, Tk/ttk (biblioteca padrão), `cryptography` para AES-256-GCM. Sem servidor ou banco de dados. Não é necessário substituir o cofre existente.

> Esta versão mantém o núcleo Tk/ttk, agora com widgets nativos e um sistema de design próprio. A adoção de um toolkit de terceiros não era necessária para atingir a refatoração e dificultaria testar a interface integralmente no ambiente de desenvolvimento. **Responsividade aqui significa redimensionamento adaptativo em desktop**, não uma interface web/mobile.

## Instalar e executar

1. Instale Python 3.10 ou superior, com Tkinter. No Ubuntu/Debian: `sudo apt install python3-tk`.
2. Extraia o ZIP e execute na pasta onde está `cadastro_portaria.py`:

```bash
python -m pip install -r requirements.txt
python cadastro_portaria.py
```

No Windows, se necessário, use `py` em vez de `python`.

Para escolher uma pasta de dados separada do código:

```bash
python cadastro_portaria.py --data-dir "C:\\DadosPortaria"
```

Também é possível definir a variável de ambiente `PORTARIA_DATA_DIR`. **Sem essa configuração, o padrão continua sendo a pasta do projeto**, para manter compatibilidade com os dados atuais.

Instale as dependências de desenvolvimento e execute os testes:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

`pytest` é utilizado apenas nos testes. No Linux headless, execute os testes de interface com `xvfb-run -a python -m pytest -q`. Se não houver display, os testes gráficos serão pulados; os testes de domínio, aplicação e criptografia continuam disponíveis.


### Ajuste 2.0.1 — primeiro acesso em telas menores

A versão 2.0 inicial usava um `Canvas` sem rolagem na primeira configuração, o que ocultava o botão **Criar Admin Final** em monitores de menor altura ou com escala de exibição elevada. A correção adiciona uma área rolável e reestrutura o formulário quando a largura é reduzida. A janela **Novo usuário** recebe o mesmo tratamento; não é necessário aumentar a resolução do monitor.

**Limites:** este é um aplicativo desktop adaptativo, não uma interface para smartphones. O comportamento visual foi verificado em um display virtual Linux e deve ser confirmado no Windows com a escala de exibição utilizada na instalação.

## O que mudou

### Interface e experiência de uso

- Layout de painel com barra lateral, hierarquia visual clara, histórico de acessos, área de cadastro, auditoria, usuários e configurações.
- Três temas: **Claro**, **Escuro** e **Floresta**, selecionáveis em *Aparência e sistema*. Preferência persistida em `ui_settings.json` (sem dados pessoais).
- Layout adaptativo: em janelas amplas, cadastro e histórico lado a lado; em janelas menores, alternativas *Nova entrada* / *Ver histórico*, com rolagem do formulário e da tabela.
- **Primeiro acesso e gestão de usuários adaptativos:** formulários com duas colunas em janelas largas e uma coluna nas estreitas; rolagem vertical por mouse, barra e avanço de foco com Tab. O botão final permanece acessível mesmo quando a altura da janela é pequena. Capturas: [tela ampla](docs/setup_amplo.png), [tela compacta](docs/setup_compacto.png) e [final do formulário compacto](docs/setup_compacto_final.png).
- Pesquisa sem diferenciar acentos/maiúsculas, filtro de pessoas sem saída, contadores e confirmação antes de exclusões.
- Mensagens de erro objetivas e confirmação de sucesso em área de status; diálogos para ações que precisam de atenção.
- Nomes limitados a **100 caracteres** tanto na entrada quanto no caso de uso; campos de **data/hora com máscara**, inserção dos separadores e validação de datas de calendário.
- Seletores de calendário e horário, edição de múltiplos campos em um único salvamento, entrada e saída, tipos de acesso temporários com validade de 24 horas.
- Autenticação, primeiro acesso, abertura do cofre, recuperação de senha e gestão de usuários refeitos.

### Arquitetura

```text
cadastro_portaria.py                ponto de entrada, lock de processo, configuração
requirements.txt
requirements-dev.txt               dependências apenas de testes
portaria/
  config.py                         formatos, caminhos e valores legados
  domain/
    permissions.py                  política RBAC por capacidade
    validation.py                   campos, CPF, datas, regras
    input_masks.py                  validador de prefixos de data/hora
    security.py                     PBKDF2 e opções de recuperação legadas
  application/
    service.py                      fachada PortariaService e estado
    vault_lifecycle.py             abrir, carregar e migrar cofre
    access_operations.py           registro, saída, edição e auditoria
    identity_operations.py         login, usuários, papéis, recuperação
  infrastructure/
    vault.py                        AES-GCM, derivação, integridade, gravação atômica
    storage.py                      importação CSV/JSON legada
    instance_lock.py                bloqueio de instância via sistema operacional
  presentation_v2/
    app.py                          composição, navegação e temas
    theme.py                        sistema de design (tokens e widgets)
    auth.py                         login, primeiro acesso, recuperação, desbloqueio
    records.py                      cadastro e histórico
    users.py                        usuários e papéis
    audit.py                        auditoria e filtros
    fields.py                       máscaras, calendário, horário
  tests/
    test_service.py
    test_vault.py
    test_input_masks.py
    test_security_v2.py
    test_ui_v2.py
docs/
  ARQUITETURA_V2.md
  SEGURANCA_E_LIMITACOES.md
  DECISOES_REFATORACAO_ANTERIOR.md
  UX_HEURISTICAS.md
  ui_claro.png, ui_escuro.png, ui_compacto.png (capturas sintéticas)
Cadastro_de_Portaria_SRS.md      documento acadêmico histórico, NÃO a especificação atual
```

`PortariaService` é o ponto de entrada das operações para a interface. As operações estão separadas em classes de casos de uso que compartilham o contexto da fachada. Os serviços não importam Tkinter. A persistência mantém as estruturas existentes para **evitar uma migração incompatível do cofre**.

### Segurança e confiabilidade

- **Autorização no back-end local, não apenas escondendo menus:** apenas usuários com a capacidade necessária podem executar cada operação. Admin Final é único e não pode ser excluído/rebaixado pelo fluxo da aplicação.
- **Idempotência de entrada persistente:** o formulário gera um UUID por tentativa de cadastro; o serviço utiliza esse token para determinar o ID de forma estável. Repetições do mesmo token e conteúdo não criam outra entrada, inclusive após reinicializar. O token é renovado após sucesso/limpeza.
- **Edição em lote atômica:** todas as alterações de campos e respectivos eventos são gravadas juntas. Evita um registro parcialmente atualizado quando o usuário edita vários campos.
- **Guard de reentrância da UI:** callbacks de escrita ignoram ações repetidas enquanto a operação está em andamento, inclusive durante diálogos modais.
- **Lock entre processos:** apenas uma instância pelo mesmo diretório de dados consegue abrir a aplicação para escrita.
- **Controle de concorrência otimista:** antes de gravar o cofre, compara a revisão lida com o arquivo atual e impede substituição de versão alterada externamente.
- **Auditoria ampliada:** além das edições/exclusões, registra criação e alteração de contas, papéis, desbloqueios e tipos temporários. No cofre, mudanças de dados e auditoria usam um commit.
- **Recuperação protegida:** valida três desafios no serviço, registra falhas com bloqueio temporário e emite autorização de recuperação de uso único, válida por cinco minutos. Não é possível solicitar diretamente a redefinição de outra conta sem a autorização correspondente.
- **Proteção em repouso:** cofre AES-256-GCM com PBKDF2 para senha do Admin Final; hash das credenciais individuais permanece compatível com usuários anteriores. Escrita com arquivo temporário criptografado + `os.replace` e `fsync`.

## Permissões por papel

| Funcionalidade | Admin Final | Adm | Usuário |
|---|:---:|:---:|:---:|
| Consultar e pesquisar registros | Sim | Sim | Sim |
| Cadastrar entrada e tipo temporário | Sim | Sim | Sim |
| Registrar saída ainda vazia | Sim | Sim | Sim |
| Editar dados / corrigir saída já preenchida | Sim | Sim | Não |
| Excluir registros | Sim | Sim | Não |
| Consultar auditoria | Sim | Sim | Não |
| Criar/excluir contas, alterar papéis, desbloquear | Sim | Não | Não |
| Mudar tema da própria interface | Sim | Sim | Sim |

Papel do usuário é obtido da conta autenticada, nunca de uma opção escolhida no login.

## Dados, abertura do cofre e migração

- A aplicação usa `dados_portaria.enc` com **quatro conjuntos de dados lógicos** (registros, auditoria, tipos temporários e usuários), preservando o **formato binário v2 anterior**.
- O Admin Final desbloqueia o cofre ao iniciar; depois os funcionários entram usando suas próprias credenciais. O sistema não grava a senha de desbloqueio em claro.
- O código de recuperação aleatório é mostrado **uma única vez**, na criação/migração; guarde-o fora do computador. Recuperação de senha de usuários continua separada do desbloqueio do cofre.
- Em uma instalação antiga **sem cofre**, faça backup dos quatro arquivos `registros_portaria.csv`, `auditoria_portaria.csv`, `tipos_temporarios.csv`, `usuarios_portaria.json`, coloque-os no diretório de dados e escolha migrar. A criptografia exige a senha atual do Admin Final; os originais legíveis são removidos da pasta ativa após o commit do cofre.
- Em instalação com cofre existente, **copie apenas o cofre válido para o diretório de dados**, sem os CSV/JSON legíveis, e informe a senha ou o código de recuperação ao abrir. Não é necessária conversão adicional.
- `dados_portaria.lock` é um arquivo auxiliar para o bloqueio entre processos; pode permanecer depois de uma execução. O bloqueio é do sistema operacional e é liberado ao encerrar o processo. **Não apague ou edite o cofre enquanto estiver aberto.**
- `ui_settings.json` guarda somente o tema. `portaria.log` registra erros técnicos. Esses arquivos não fazem parte do cofre.

**Backup obrigatório:** copie `dados_portaria.enc` regularmente para armazenamento seguro e externo, com a aplicação fechada. Guarde a senha/código de recuperação separadamente. Uma gravação atômica evita arquivo parcialmente escrito, mas não substitui backups.

## Limitações conhecidas

1. **Não é um servidor nem uma solução de segurança contra administradores da máquina.** Quem pode modificar scripts Python, copiar ou substituir arquivos locais pode negar serviço ou restaurar um cofre antigo. O sistema não impede rollback de backup, cópia da base ou ataques ao próprio computador. Use permissões de pasta do SO e backup externo.
2. **O desbloqueio pelo Admin Final é exigido a cada abertura** (concepção mantida por compatibilidade). Não é ideal para múltiplos turnos independentes e não há acesso simultâneo em rede. A chave fica na memória do processo enquanto a aplicação está aberta.
3. A recuperação por três palavras em múltipla escolha é uma funcionalidade **legada com entropia limitada**. O bloqueio por tentativas e o token de recuperação reduzem, mas não eliminam, o risco. Em ambiente real, preferir recuperação independente, MFA e política de credenciais mais forte.
4. Tk/ttk é um toolkit **desktop**. Esta versão se adapta às dimensões da janela, mas não é uma interface mobile, nem garante equivalência pixel a pixel em Windows/Linux/macOS. Testes gráficos automatizados foram feitos em display virtual Linux; faça aceite visual e de acessibilidade no Windows de destino.
5. O cofre regrava o documento criptografado inteiro em cada operação. Essa arquitetura, deliberadamente preservada, terá gargalos conforme a base e a auditoria crescerem. O lock entre instâncias evita competição apenas entre aplicações que respeitem o mesmo arquivo de lock.
6. O projeto acadêmico não foi submetido a auditoria de segurança independente nem tem contrato de suporte de produção.

## Histórico e autoria

Evolução posterior ao projeto acadêmico **Cadastro de Portaria v6**, desenvolvido para Teoria da Computação e Compiladores, Faculdade UNA, por **Lucas Augusto Morais Carvalho** e **Lucas Andrian Pieroni** (Prof.ª Cíntia Silvana de Souza). O SRS na raiz e o arquivo `docs/DECISOES_REFATORACAO_ANTERIOR.md` são referências históricas, não especificações da v2.

As decisões de arquitetura e ameaças residuais estão detalhadas em `docs/ARQUITETURA_V2.md` e `docs/SEGURANCA_E_LIMITACOES.md`. A verificação das dez heurísticas está em `docs/UX_HEURISTICAS.md`.
