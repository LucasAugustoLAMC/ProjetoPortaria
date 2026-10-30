# Cadastro de Portaria

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Interface](https://img.shields.io/badge/Interface-Tkinter-5F7350)
![Criptografia](https://img.shields.io/badge/criptografia-AES--256--GCM-7C9A64)
![Base](https://img.shields.io/badge/base-v6.0%20modularizada-B8862F)
![Status](https://img.shields.io/badge/status-projeto%20acad%C3%AAmico-lightgrey)

Aplicativo desktop para **controle de entrada e saída de pessoas em uma portaria**, incluindo visitantes, moradores, entregadores, funcionários e prestadores de serviço. Oferece autenticação por cargo, auditoria de alterações e interface em janela única.

A aplicação original (versão 6.0) foi **refatorada de um único arquivo para uma estrutura modular**, com separação entre interface, casos de uso, validação, segurança e persistência. Mantém as funcionalidades, as permissões e a leitura dos arquivos legados. **A persistência atual é um cofre local criptografado**, não CSV/JSON em texto puro. A criptografia exige a dependência `cryptography`, declarada em `requirements.txt`.

> Projeto desenvolvido na disciplina de **Teoria da Computação e Compiladores**, da Faculdade UNA, a partir do exercício *Cadastro de Portaria*. Esta edição mantém o contexto acadêmico e documenta a refatoração arquitetural.

## Funcionalidades

### Portaria

- Cadastro de pessoas com nome, tipo de acesso e data/hora de entrada e, opcionalmente, de saída.
- Calendário e relógio interativos integrados à janela.
- Campos de data e hora com **máscara durante a digitação**: `dd/mm/aaaa` e `hh:mm`, com inserção automática de `/` e `:`. Letras, emojis, dígitos não ASCII, colagens incompatíveis, horários fora de faixa e datas de calendário impossíveis são rejeitados.
- **Proteção contra duplo clique e Enter repetido** nas ações de cadastrar, registrar saída e excluir, para impedir múltiplas gravações do mesmo comando enquanto ele está em andamento.
- Registro de saída de pessoas cadastradas anteriormente.
- Pesquisa por nome, tipo e datas, ignorando maiúsculas e acentos, e filtro de registros sem saída.
- Edição por duplo clique na tabela e exclusão de registros conforme o cargo.
- Tipos de acesso predefinidos: **Visitante, Morador, Entregador e Funcionário**.
- Tipos temporários (por exemplo, *Mecânico*), disponíveis para novos cadastros por **24 horas** e preservados no histórico após expirarem.
- Destaque visual para registros sem saída e marcação `*` nos tipos temporários.

### Usuários e autenticação

- Primeiro acesso destinado ao cadastro do **Admin Final**.
- Login por CPF ou e-mail, com seleção do cargo.
- Cargos **Admin Final**, **Adm** e **Usuário**, com permissões distintas.
- Cadastro com validação de CPF, e-mail, senha e três palavras-chave de recuperação.
- Recuperação de senha por CPF, e-mail e perguntas de múltipla escolha baseadas nas palavras-chave.
- Hashes de senha e palavras-chave com **PBKDF2-HMAC-SHA256 e salt**, compatíveis com a versão anterior.
- Bloqueio por **5 minutos após 5 tentativas incorretas** de autenticação.
- **Cofre local AES-256-GCM:** protege registros, auditoria, tipos e usuários em um único arquivo criptografado com autenticação de integridade.
- **Desbloqueio na abertura** com a senha do Admin Final. Depois, cada funcionário realiza seu próprio login e segue as permissões existentes.
- **Código de recuperação de emergência:** gerado aleatoriamente, mostrado uma única vez ao ativar a proteção; permite abrir o cofre se a senha do Admin Final for esquecida.
- Ao redefinir a senha do Admin Final, o cofre passa a aceitar a nova senha; o código de recuperação continua válido.

### Digitação de datas e horas

Nos quatro campos da portaria (data/hora de entrada e de saída), é possível digitar **apenas números de 0 a 9**. Ao informar o próximo número, a interface preenche automaticamente os separadores obrigatórios (por exemplo, `30102026` digitado sequencialmente gera `30/10/2026`; `0930` gera `09:30`). Também é possível escolher pelo calendário ou pelo relógio.

A colagem deve conter a **data ou hora com os separadores nas posições corretas**; colar texto ou emojis não altera o campo. O campo aceita valores parciais durante a edição, mas o cadastro exige data e hora completas e válidas. Os dois campos de saída podem permanecer vazios.

### Auditoria e interface

- Auditoria das edições (valor anterior e novo) e exclusões (resumo do registro), com identificação do responsável.
- O **primeiro preenchimento da saída não gera evento de auditoria**, conforme a regra original.
- Interface em janela única, com diálogos internos, menu lateral recolhível, tema creme/verde e botões personalizados.
- Barra de título personalizada, opcional por configuração.

## Cargos e permissões

| Operação | Admin Final | Adm | Usuário |
|---|:---:|:---:|:---:|
| Cadastrar entrada | Sim | Sim | Sim |
| Registrar a primeira saída | Sim | Sim | Sim |
| Pesquisar e consultar registros | Sim | Sim | Sim |
| Editar registros, inclusive saída já preenchida | Sim | Sim | Não |
| Excluir registros | Sim | Sim | Não |
| Consultar auditoria | Sim | Sim | Não |
| Cadastrar e gerenciar usuários | Sim | Não | Não |

O **Admin Final** é criado no primeiro acesso. Pelo fluxo normal da aplicação, não pode ser excluído nem ter o cargo alterado. Ele gerencia as contas `Adm` e `Usuário`.

## Requisitos

- **Python 3.10 ou superior**, com suporte a **Tkinter/Tcl-Tk**.
- Windows 10/11 como ambiente principal; Linux com ambiente gráfico também é compatível com a interface Tkinter. **A apresentação e a barra personalizada devem ser verificadas no sistema operacional utilizado.**
- Permissão de leitura e escrita na pasta do projeto, onde ficam os dados e o log.
- **Uma dependência externa:** `cryptography` (AES-GCM autenticado), instalada via `requirements.txt`. Não é necessário banco de dados.

No Windows, o instalador padrão do Python normalmente inclui Tkinter. Em distribuições Ubuntu/Debian, caso falte o módulo: `sudo apt install python3-tk`.

## Instalação e execução

1. Extraia o projeto refatorado e abra um terminal **na pasta que contém `cadastro_portaria.py` e `portaria/`**.
2. Se estiver migrando uma instalação existente, faça uma cópia de segurança dos quatro arquivos de dados listados na seção [Persistência e migração](#persistência-e-migração).
3. Copie os arquivos existentes para a **raiz do projeto**, ao lado de `cadastro_portaria.py` — **não** para dentro da pasta `portaria/`.
4. Instale a dependência criptográfica e execute:

```bash
python -m pip install -r requirements.txt
python cadastro_portaria.py
```

No Windows, também é possível usar:

```powershell
py cadastro_portaria.py
```

**Importante:** `cadastro_portaria_v6.py` era o ponto de entrada da versão anterior. **Não é o comando de inicialização desta versão modular.** Também não é necessário executar os módulos de `portaria/` individualmente.

### Primeiro acesso

1. Se não houver dados anteriores, o aplicativo solicita o cadastro do **Admin Final**.
2. Informe os dados, a senha e as três palavras-chave. O cofre criptografado é criado nessa etapa, sem gerar `usuarios_portaria.json` em texto puro.
3. **Copie e guarde o código de recuperação** mostrado na tela. Ele aparece apenas uma vez. Não o salve na mesma pasta compartilhada da aplicação.
4. Faça login com CPF ou e-mail, senha e cargo **Admin Final**, e cadastre os demais usuários.
5. **Nas próximas inicializações**, alguém precisará informar a senha do Admin Final para desbloquear os dados; a partir daí cada funcionário entra com sua própria senha.

**Instalação antiga:** se houver `usuarios_portaria.json` e os CSVs legados, a primeira inicialização pedirá a senha atual do Admin Final para migrar os quatro arquivos para `dados_portaria.enc`. Faça backup dos quatro arquivos **antes** de iniciar a migração. O programa não solicita um novo cadastro do Admin Final se os usuários existentes forem válidos.

**Recuperação:** se esquecer a senha do Admin Final após a migração, escolha **Código de recuperação** na tela de desbloqueio; com o cofre aberto, use **Esqueci minha senha** na tela de login para redefini-la com as três palavras-chave. Sem a senha e sem o código, os dados criptografados não podem ser recuperados pelo aplicativo.

## Estrutura do projeto

```text
portaria_reestruturada/
├── cadastro_portaria.py            # Ponto de entrada e configuração do log
├── requirements.txt                # Dependência cryptography
├── .gitignore                       # Arquivos locais ignorados
├── portaria/
│   ├── __init__.py
│   ├── config.py                    # Constantes, caminhos, tema, cargos, permissões
│   ├── domain/
│   │   ├── security.py              # Hash de credenciais e recuperação
│   │   ├── input_masks.py           # Máscaras incrementais de data e hora
│   │   └── validation.py            # CPF, datas, normalização, regras de validação
│   ├── application/
│   │   └── service.py               # PortariaService: operações e estado da aplicação
│   ├── infrastructure/
│   │   ├── storage.py               # Leitor de legado CSV/JSON e escrita atômica
│   │   └── vault.py                 # AES-GCM, chaves, migração e repositórios do cofre
│   └── presentation/
│       ├── app.py                   # PortariaApp: composição da aplicação Tkinter
│       ├── access.py                # Cadastro, consulta, edição e saída
│       ├── audit.py                 # Tela de auditoria
│       ├── users.py                 # Login e gerenciamento de usuários
│       ├── user_forms.py            # Formulários e recuperação de senha
│       ├── components.py            # Botões, entradas mascaradas, calendário e relógio
│       ├── operation_guard.py       # Proteção contra operações reentrantes
│       ├── navigation.py            # Menu, telas e controles visuais de acesso
│       └── window_chrome.py         # Barra de título e comportamento da janela
├── tests/
│   ├── test_input_masks.py         # Casos de máscara e valores inválidos
│   ├── test_service.py             # Testes da lógica sem interface gráfica
│   ├── test_ui.py                  # Fluxo integrado de interface
│   └── test_vault.py               # Criptografia, adulteração, migração e recuperação
├── docs/
│   └── DECISOES_ARQUITETURAIS.md   # Decisões e riscos residuais da refatoração
├── backup_original/
│   └── cadastro_portaria_original.py
└── README.md
```

O cofre `dados_portaria.enc` e o `portaria.log` ficam na raiz; arquivos CSV/JSON simples são aceitos apenas para migração. Arquivos `__pycache__/` são produzidos automaticamente pelo Python e não fazem parte da arquitetura.

### Responsabilidades e dependências

| Camada | Responsabilidade |
|---|---|
| **Domain** | Funções de validação, regras de formato e operações de segurança que não dependem da interface. |
| **Application** | `PortariaService` centraliza cadastros, edições, exclusões, autenticação, permissões e estado em memória. |
| **Infrastructure** | Migração de CSV/JSON legados, cofre criptografado, escrita atômica e validação de integridade. |
| **Presentation** | Telas Tkinter, componentes reutilizáveis e eventos de interface; utiliza o serviço de aplicação. |
| **Config** | Constantes de negócio, aparência, caminhos e formatos compartilhados. |

A interface foi dividida em **mixins por funcionalidade**, combinados em `PortariaApp`. Isso torna o código mais organizado, mas **não transforma a aplicação desktop em microserviços** nem elimina todo acoplamento interno. A persistência continua local.

### Fluxo simplificado

```text
Usuário
   ↓
Tkinter / PortariaApp (presentation)
   ↓
PortariaService (application)
   ├── Validações / Segurança (domain)
   └── Repositórios (infrastructure)
           ↓
      dados_portaria.enc (AES-GCM)
```

## Cofre criptografado e migração dos dados

**Arquivo atual:** `dados_portaria.enc` fica na raiz, ao lado de `cadastro_portaria.py`. O conteúdo é um único cofre autenticado que armazena os quatro conjuntos lógicos:

| Conjunto lógico | Formato legado aceito na migração | Conteúdo |
|---|---|---|
| Registros | `registros_portaria.csv` | Nomes, tipos, entradas, saídas e IDs |
| Auditoria | `auditoria_portaria.csv` | Histórico de alterações, exclusões e responsáveis |
| Tipos temporários | `tipos_temporarios.csv` | Nomes dos tipos temporários e datas de criação |
| Usuários | `usuarios_portaria.json` | Usuários, cargos, CPF/e-mail e hashes de autenticação |

Após a migração bem-sucedida, os arquivos legados em texto claro são removidos da pasta ativa. **O aplicativo não recria CSVs legíveis** em operações normais. Os dados continuam sendo manipulados pelos mesmos casos de uso, mas são serializados dentro do cofre criptografado.

### Segurança do cofre

- **Criptografia autenticada:** AES-256-GCM com nonce aleatório por gravação. Uma modificação não autorizada dos bytes provoca falha no desbloqueio; a aplicação não sobrescreve o cofre danificado.
- **Chaves:** chave de dados aleatória de 256 bits, protegida por uma chave derivada da **senha do Admin Final** com PBKDF2-HMAC-SHA256 e salt aleatório (600.000 iterações).
- **Recuperação:** uma segunda cópia da chave de dados é protegida pelo **código aleatório de recuperação**, exibido apenas na criação/migração. O código **equivale a uma credencial de acesso aos dados**; proteja-o como uma senha administrativa.
- **Troca da senha do Admin Final:** o acesso ao cofre é reconfigurado no mesmo commit criptografado que atualiza o hash do usuário; o código de recuperação permanece utilizável.
- **Gravação atômica do conjunto:** cada alteração salva um novo cofre completo em arquivo temporário criptografado, sincroniza e substitui o anterior com `os.replace`. Edição e auditoria são gravadas juntas.

**Limites reais:** a proteção impede leitura casual e alteração indetectável do cofre sem a chave. **Não impede exclusão, substituição por backup antigo (rollback), cópias do arquivo ou alteração do próprio código Python** por alguém com acesso ao sistema de arquivos. Depois do desbloqueio, a chave fica na memória do processo. Use contas separadas no sistema operacional e permissões NTFS/Linux para proteger a pasta e impedir modificação do aplicativo. Não considere essa solução equivalente a um servidor protegido.

### Migração de instalação anterior

1. **Feche a aplicação antiga** e faça backup dos quatro arquivos `registros_portaria.csv`, `auditoria_portaria.csv`, `tipos_temporarios.csv` e `usuarios_portaria.json` em um local seguro, preferencialmente criptografado.
2. Copie-os para a raiz do projeto novo. Não coloque os arquivos na pasta `portaria/`.
3. Instale `cryptography` e execute `python cadastro_portaria.py`.
4. Informe a senha **atual** do Admin Final quando solicitada.
5. Guarde o **código de recuperação** exibido uma única vez.
6. Verifique os dados e o login antes de descartar os backups.

A leitura de registros antigos sem `Id` e auditoria sem `Usuario` continua compatível. Em caso de interrupção **após** a gravação do cofre mas **antes** da remoção de todos os arquivos antigos, a próxima inicialização usa o cofre íntegro e tenta concluir a limpeza. O arquivo legado de usuários jamais é considerado a fonte de verdade se o cofre já existir.

**Importante:** apagar ou perder `dados_portaria.enc` significa perder os dados protegidos, mesmo que os usuários tenham senhas válidas. Os backups de CSV/JSON originais continuam **sem criptografia** e precisam de proteção separada. A exclusão normal de arquivos não garante eliminação segura de cópias em SSD, snapshots e histórico do Git.

### Git e arquivos sensíveis

O `.gitignore` incluído no projeto ignora `dados_portaria.enc`, arquivos legados CSV/JSON, logs, caches e arquivos temporários. **Nunca publique o cofre, os backups ou o código de recuperação em um repositório.** O `.gitignore` não apaga dados enviados anteriormente ao histórico do Git.

## Melhorias de robustez implementadas

- **Gravação atômica do cofre completo:** gera exclusivamente dados criptografados no arquivo temporário, faz `flush`/`fsync` e `os.replace`; registros e auditoria são persistidos juntos.
- **Persistência antes da confirmação:** operações de negócio gravam os dados antes de publicar o estado alterado em memória.
- **Falha de leitura não significa arquivo vazio:** dados existentes que não podem ser lidos ou estão estruturalmente inválidos impedem a inicialização, evitando sobrescrita silenciosa.
- **Validações e permissões no serviço:** regras essenciais também são conferidas fora dos controles visuais.
- **Máscara incremental com validação do Tkinter:** impede letras, emojis e valores incorretos diretamente nos campos de data e hora, incluindo tentativas de colagem. Datas completas impossíveis são rejeitadas.
- **Bloqueio de reentrância de registros:** `proteger_operacao_registro` desativa temporariamente os botões de cadastro, saída e exclusão, e impede que cliques rápidos, Enter ou callbacks reentrantes acionem uma segunda operação antes do fim da primeira (incluindo a exibição de diálogos). Um bloco `finally` restaura os estados anteriores de cada botão mesmo após erros, sem conceder permissões indevidas.
- **Auditoria no mesmo commit:** ao editar ou excluir registros, o cofre escreve alterações e eventos de auditoria em uma única substituição atômica.
- **Registro de exceções da interface:** falhas inesperadas de callbacks Tkinter são gravadas no `portaria.log`, na raiz do projeto.

**A proteção contra cliques repetidos é local ao processo e à interface**, não uma chave de idempotência persistida no CSV. Ela não impede cadastros intencionais idênticos em momentos diferentes nem substitui o controle de concorrência entre instâncias.

**A gravação conjunta reduz o risco de inconsistência entre registros e auditoria**, mas não há bloqueio entre processos: não execute duas instâncias na mesma pasta. A durabilidade em falha de energia também depende das garantias do sistema de arquivos.

## Testes

Na raiz do projeto, execute:

```bash
python -m unittest discover -s tests -v
```

Os testes usam diretórios temporários e **não precisam dos seus arquivos reais**. Cobrem, entre outros cenários, cadastro, edição, saída, exclusão, auditoria, permissões, tipos temporários, recuperação/redefinição de senha, bloqueio de login, formatos legados e falhas simuladas de persistência. Também verificam as máscaras de entrada, a digitação automática de separadores, tentativas de reentrância por cliques repetidos e a restauração das permissões após a operação.

O teste de interface requer um display gráfico. Se a variável `DISPLAY` não existir em Linux, o teste é **ignorado**. Caso `DISPLAY` aponte para um servidor gráfico inacessível, o teste pode falhar com `TclError`; execute-o com um display virtual, se `xvfb-run` estiver disponível:

```bash
xvfb-run -a python -m unittest discover -s tests -v
```

A suíte inclui testes de senha incorreta, adulteração de ciphertext, recuperação, troca de senha do Admin Final, migração de legado, falha de gravação e rollback de estado. Os testes de cofre dependem da biblioteca `cryptography` instalada.

Os testes automatizados não substituem a validação manual do comportamento da interface no Windows (especialmente minimizar, maximizar e barra de tarefas).

## Configurações

As configurações compartilhadas ficam em **`portaria/config.py`** — não mais no início de um arquivo monolítico.

| Constante | Função | Valor padrão |
|---|---|---|
| `BARRA_TITULO_PERSONALIZADA` | Habilita ou desabilita a barra personalizada. | `True` |
| `TIPOS_ACESSO` | Tipos fixos disponíveis para cadastro. | Visitante, Morador, Entregador, Funcionário |
| `VALIDADE_TEMPORARIO` | Prazo para oferecer um tipo temporário em novos cadastros. | 24 horas |
| `PERMISSOES` | Regras por cargo, aplicadas também nos casos de uso. | Conforme tabela de cargos |
| `MAX_TENTATIVAS` | Limite de tentativas incorretas de login. | `5` |
| `MINUTOS_BLOQUEIO` | Duração do bloqueio de conta. | `5` |
| `DATA_DIR` | Pasta-base dos dados locais. | Raiz do projeto |

**Parâmetros criptográficos:** PBKDF2 com 600.000 iterações e AES-256-GCM estão definidos em `portaria/infrastructure/vault.py`. **Não altere o formato ou as iterações** sem uma estratégia de versionamento/migração, pois cofres existentes deixariam de abrir.

`ITERACOES_SENHA` e `ITERACOES_PALAVRA` também estão em `config.py`, mas **não devem ser alteradas sem uma migração planejada dos hashes existentes**.

## Solução de problemas

| Sintoma | Orientação |
|---|---|
| `No module named 'portaria'` | Execute a partir da pasta com `cadastro_portaria.py` e `portaria/`, usando o ponto de entrada correto. |
| `No module named 'tkinter'` | Instale ou habilite Tkinter na sua distribuição do Python. |
| `TclError: couldn't connect to display` ao testar | É necessário um display acessível; em Linux headless, use `xvfb-run`. |
| `No module named 'cryptography'` | Rode `python -m pip install -r requirements.txt` no mesmo Python da aplicação. |
| Cofre não desbloqueia | Confira a senha do **Admin Final** (não a de um usuário comum) ou use o código de recuperação. Corrupção e senha incorreta podem gerar mensagem parecida. **Não apague o cofre**. |
| Esqueceu a senha do Admin Final | Use o **código de recuperação** para abrir o cofre e depois o fluxo **Esqueci minha senha** no login. Sem ambos, não há recuperação garantida. |
| Erro ao migrar CSV/JSON | Verifique os backups, permissões e formato; **não apague os arquivos**. O cofre, se já criado, tem precedência. |
| Erro de gravação | Verifique permissões da pasta, espaço em disco e bloqueio dos arquivos por outros programas. Consulte `portaria.log` se necessário. |
| Conta bloqueada | Aguarde 5 minutos ou peça ao Admin Final que a desbloqueie. |
| Esqueceu a senha | Use a recuperação disponível na tela de login. |
| Barra personalizada apresenta problemas | Defina `BARRA_TITULO_PERSONALIZADA = False` em `portaria/config.py`. |
| Precisa consultar o CSV antigo no Excel | Utilize um **backup legado protegido**; a versão criptografada não gera exportação CSV em texto puro. |
| Ícones ou emojis como quadrados | A fonte do sistema pode não conter os caracteres necessários. |

## Histórico do projeto

| Etapa | Mudanças principais |
|---|---|
| **1.0** | Exercício inicial: cadastro, tabela, operações básicas e arquivo de dados. |
| **2.0** | Datas, calendário, relógio, filtros e histórico de alterações. |
| **3.0** | Tipos temporários com validade de 24 horas. |
| **4.0** | Autenticação, cargos, CPF, palavras-chave e recuperação de senha. |
| **5.0** | Interface em janela única e painel lateral. |
| **6.0** | Tema creme/verde, botões arredondados e barra de título personalizada. |
| **Refatoração modular da 6.0** | Separação em camadas, testes, validação centralizada e tratamento mais defensivo de falhas de arquivo. |
| **Validação de entrada e proteção de registro** | Campos com máscara de data/hora, bloqueio de comandos duplicados na interface e testes de reentrância/permissão. |
| **Cofre criptografado** | AES-256-GCM, senha do Admin Final, código de recuperação, migração dos CSV/JSON e commit atômico de registros/auditoria. |

A refatoração **não declara uma nova versão funcional**: documenta uma reorganização interna com melhorias de confiabilidade e mantém o escopo da versão 6.0.

## Relação com a disciplina de Compiladores

O projeto permite observar conceitos de análise léxica, sintática e semântica em código Python distribuído entre módulos:

- **Análise léxica:** em `nome = ' '.join(nome.split())`, no método `PortariaService.criar_tipo_temporario` (`portaria/application/service.py`), há identificadores, operadores, uma constante de string, pontos e delimitadores.
- **Escopo e tabela de símbolos:** parâmetros como `nome`, `tipo` e `entrada` em `PortariaService.cadastrar` são variáveis locais; `self.registros` é um atributo de instância mantido no serviço.
- **Verificação semântica:** `validar_ordem()` impede que a saída seja anterior à entrada; `cpf_valido()` verifica dígitos verificadores; `PortariaService.exigir()` aplica as permissões de cada cargo. Esses exemplos são **regras semânticas da aplicação**, não uma implementação de analisador semântico de compilador.

## Limitações e possíveis evoluções

- **Persistência local:** o cofre criptografado ainda não suporta múltiplos processos/computadores escrevendo simultaneamente. Pode haver perda de atualização se duas instâncias compartilharem a pasta.
- **Segurança:** arquivos e código podem ser apagados/substituídos por usuários com acesso ao disco; rollback de snapshots válidos não é detectado. A senha do Admin Final ou o código de recuperação é obrigatória para abrir os dados, inclusive para permitir acesso posterior a contas comuns. A recuperação por três palavras-chave permanece como no sistema original e não equivale à segurança de produção.
- **Interface:** os botões personalizados possuem limitações de navegação por teclado, e a barra de título deve ser avaliada em cada sistema operacional.
- **Evoluções futuras:** backup **criptografado** automatizado, bloqueio entre processos, diretório de dados com ACL restritiva, teste de interface no Windows, relatórios e acessibilidade. Nenhum desses recursos foi incluído nesta etapa.

Para mais contexto técnico, consulte [`docs/DECISOES_ARQUITETURAIS.md`](docs/DECISOES_ARQUITETURAIS.md).

## Autores e contexto acadêmico

**Lucas Augusto Morais Carvalho** — estudante de Ciência da Computação, Faculdade UNA.  
**Lucas Andrian Pieroni** — estudante de Ciência da Computação, Faculdade UNA.  
**Disciplina:** Teoria da Computação e Compiladores (Prof.ª Cíntia Silvana de Souza).

*Projeto acadêmico, desenvolvido para fins educacionais.*
# ProjetoPortaria
