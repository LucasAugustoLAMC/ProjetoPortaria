# Cadastro de Portaria — Documento de Requisitos de Software (SRS)

**Controle de entrada e saída de pessoas em portaria** · Software versão 6.0 · Documento versão 1.0

## Controle do documento

| Item | Descrição |
| --- | --- |
| Produto | Cadastro de Portaria — Controle de entrada e saída |
| Versão do software | 6.0 (arquivo `cadastro_portaria_v6.py`) |
| Versão do documento | 1.0 |
| Data | 29/10/2026 |
| Autores | Lucas Augusto Morais Carvalho; Lucas Andrian Pieroni |
| Instituição / disciplina | Faculdade UNA — Teoria da Computação e Compiladores (Prof.ª Cíntia Silvana de Souza) |
| Padrão seguido | Estrutura da IEEE 830-1998 e da ISO/IEC/IEEE 29148:2018, adaptada ao porte do projeto |
| Situação | Primeira versão completa |

### Histórico de revisões do documento

| Versão | Data       | Descrição                                               |
|--------|------------|---------------------------------------------------------|
| 1.0    | 29/10/2026 | Documento inicial, cobrindo o software até a versão 6.0 |

## Sumário

1. Introdução
2. Descrição geral
3. Requisitos funcionais
4. Requisitos não funcionais
5. Regras de negócio
6. Matriz de permissões
7. Casos de uso
8. Interfaces com o usuário
9. Modelo de dados
10. Arquitetura e projeto
11. Plano de testes e rastreabilidade
12. Instalação, execução e manutenção
13. Manual do usuário
14. Relação com a disciplina de Compiladores
15. Riscos, limitações e trabalhos futuros
16. Histórico de versões do software

## 1. Introdução

### 1.1 Propósito

Este documento especifica os requisitos do aplicativo **Cadastro de Portaria**, um sistema desktop para registrar a entrada e a saída de pessoas em uma portaria (visitantes, moradores, entregadores, funcionários e prestadores temporários). Ele descreve o que o sistema faz (requisitos funcionais), como deve se comportar (requisitos não funcionais), quem pode usar cada função, como os dados são guardados, como o software foi organizado e como foi testado.

O público-alvo é o professor e a turma da disciplina (avaliação do trabalho), a pessoa que for dar manutenção ao código e quem for operar o sistema.

### 1.2 Escopo

O produto nasceu do exercício “Cadastro de Portaria” da disciplina de Teoria da Computação e Compiladores (Python + Tkinter) e evoluiu em seis versões até um sistema com login, cargos, auditoria e interface em janela única.

**O sistema inclui:**

- Autenticação com três cargos (Admin Final, Adm e Usuário), cadastro de usuários e recuperação de senha.
- Registro de entradas e saídas, com pesquisa, edição, exclusão e tipos de acesso temporários.
- Registro de auditoria de edições e exclusões, com identificação do responsável.
- Interface gráfica em uma única janela, com painel lateral ocultável, tema creme e verde selva e barra de título própria.
- Persistência local em arquivos CSV e JSON.

**O sistema não inclui:**

- Acesso em rede ou uso simultâneo por vários computadores.
- Banco de dados, servidor, envio de e-mail ou SMS.
- Leitura de documentos, fotos, QR code ou integração com catraca, interfone ou câmeras.
- Exportação de relatórios (PDF/Excel) e backup automático (ver seção 15).

### 1.3 Definições, acrônimos e abreviações

| Termo           | Significado                                                                               |
|-----------------|-------------------------------------------------------------------------------------------|
| SRS             | Software Requirements Specification (Especificação de Requisitos de Software)             |
| RF / RNF / RN   | Requisito funcional / Requisito não funcional / Regra de negócio                          |
| UC / CT         | Caso de uso / Caso de teste                                                               |
| Admin Final     | Cargo de maior nível: acesso total, único, criado no primeiro acesso                      |
| Adm             | Cargo intermediário: opera a portaria e consulta a auditoria, sem gerenciar usuários      |
| Usuário         | Cargo mais restrito: cadastra entradas e preenche saídas                                  |
| Registro        | Uma linha da portaria: pessoa, tipo de acesso, entrada e saída                            |
| Tipo temporário | Tipo de acesso criado na hora (ex.: Mecânico), válido por 24 horas na lista               |
| Auditoria       | Histórico de edições e exclusões, com valor anterior e responsável                        |
| Hash            | Resultado de uma função matemática de via única, usado para guardar senhas sem texto puro |
| Salt            | Valor aleatório misturado à senha antes do hash                                           |
| PBKDF2          | Função de derivação de chave usada para o hash das senhas (RFC 8018)                      |
| CPF             | Cadastro de Pessoas Físicas, validado pelos dois dígitos verificadores                    |
| Tkinter         | Biblioteca gráfica padrão do Python                                                       |
| CSV / JSON      | Formatos de arquivo de texto usados para guardar os dados                                 |
| LGPD            | Lei Geral de Proteção de Dados (Lei 13.709/2018)                                          |

### 1.4 Referências

- IEEE Std 830-1998 — Recommended Practice for Software Requirements Specifications.
- ISO/IEC/IEEE 29148:2018 — Requirements engineering.
- ISO/IEC 25010:2011 — Modelo de qualidade de produto de software (base da seção 4).
- RFC 8018 — PKCS \#5: Password-Based Cryptography Specification (PBKDF2).
- Lei 13.709/2018 (LGPD).
- Documentação oficial do Python: módulos tkinter, hashlib, hmac, secrets, csv, json.
- Enunciado do exercício “Cadastro de Portaria” (Faculdade UNA, Prof.ª Cíntia Silvana de Souza).

### 1.5 Visão geral do documento

A seção 2 apresenta o produto em alto nível. As seções 3 a 6 trazem os requisitos e as regras. A seção 7 descreve os casos de uso, a 8 as telas e a 9 os dados. A seção 10 explica a arquitetura. A seção 11 traz os testes e a rastreabilidade. As seções 12 e 13 são o guia de instalação e o manual. A seção 14 liga o projeto à disciplina de Compiladores e a 15 lista riscos e melhorias futuras.

### 1.6 Convenções

- **Identificadores:** RF-nnn, RNF-nnn, RN-nn, UC-nn, CT-nn.
- **Prioridade:** *Essencial* (o sistema não funciona sem), *Importante* (esperado pelo usuário), *Desejável* (melhora a experiência).
- Os nomes entre crases (assim) são nomes reais de arquivos, funções ou constantes do código.

## 2. Descrição geral

### 2.1 Perspectiva do produto

O Cadastro de Portaria é um aplicativo independente (stand-alone), escrito em um único arquivo Python, que usa somente a biblioteca padrão. Os dados ficam em arquivos na mesma pasta do programa. Ele substitui o controle em papel ou planilha por um sistema com controle de acesso por cargo e trilha de auditoria.

### 2.2 Funções principais

1. Login por cargo, primeiro acesso e recuperação de senha.
2. Cadastro e gestão de usuários (Admin Final).
3. Registro de entrada de pessoas, com calendário e relógio.
4. Registro da saída, inclusive de quem entrou dias antes (pesquisa no histórico).
5. Edição de dados na própria tabela e exclusão de registros.
6. Tipos de acesso temporários com validade de 24 horas.
7. Registro de auditoria de edições e exclusões.
8. Navegação por painel lateral e interface em janela única.

### 2.3 Classes de usuários (cargos)

| Cargo       | Quem é                                                     | O que pode fazer                                                                           | Nível técnico esperado |
|-------------|------------------------------------------------------------|--------------------------------------------------------------------------------------------|------------------------|
| Admin Final | Responsável pelo sistema; único; criado no primeiro acesso | Tudo: portaria, edição, exclusão, auditoria e gestão de usuários                           | Básico                 |
| Adm         | Supervisor da portaria                                     | Cadastrar, registrar saída, editar, excluir e ver a auditoria; não gerencia usuários       | Básico                 |
| Usuário     | Porteiro / atendente                                       | Cadastrar entradas, registrar saídas e pesquisar; não edita nem exclui; não vê a auditoria | Básico                 |

### 2.4 Ambiente operacional

| Item                  | Especificação                                                                           |
|-----------------------|-----------------------------------------------------------------------------------------|
| Linguagem / interface | Python 3.8 ou superior (testado em 3.12) com Tkinter (Tk 8.6)                           |
| Sistema operacional   | Windows 10/11 (alvo principal); Linux (testado); macOS (não testado)                    |
| Hardware              | Qualquer computador que rode o Python; tela com no mínimo 980 × 640 pixels de área útil |
| Dependências externas | Nenhuma (somente a biblioteca padrão)                                                   |
| Rede                  | Não utiliza                                                                             |

### 2.5 Restrições de projeto e implementação

- Linguagem Python com Tkinter, conforme o enunciado da disciplina.
- Sem pacotes externos (por exemplo, sem tkcalendar): o calendário e o relógio são próprios.
- Dados em arquivos locais (CSV e JSON), sem banco de dados.
- Todo o texto da interface em português do Brasil.
- Janela única: nenhum diálogo ou janela secundária pode ser aberto.

### 2.6 Premissas e dependências

- O computador tem Python e Tkinter instalados (no Windows vêm com o instalador padrão).
- A pasta do programa permite leitura e gravação.
- Há um único computador operando o sistema por vez.
- O relógio do computador está correto (datas e a validade de 24 horas dependem dele).
- A fonte Segoe UI está disponível (padrão no Windows); em outros sistemas o Tk usa uma fonte substituta.

## 3. Requisitos funcionais

### 3.1 Autenticação e sessão

| ID     | Requisito                                                                                                                                                                                                                     | Prioridade |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-001 | O sistema deve exibir uma tela de login com seleção de cargo (Admin Final, Adm ou Usuário), campo de e-mail ou CPF, campo de senha e opção “Mostrar senha”.                                                                   | Essencial  |
| RF-002 | O sistema deve autenticar o usuário somente se o cargo selecionado for o da conta e a senha conferir; caso contrário, deve exibir a mensagem genérica “E-mail/CPF, senha ou cargo incorretos.”, sem indicar qual dado falhou. | Essencial  |
| RF-003 | O sistema deve aceitar como identificador o e-mail (texto com @) ou o CPF, com ou sem máscara.                                                                                                                                | Essencial  |
| RF-004 | O sistema deve contar as falhas consecutivas de cada conta e bloqueá-la por 5 minutos após 5 falhas, informando os minutos restantes.                                                                                         | Essencial  |
| RF-005 | O sistema deve zerar o contador de falhas após login bem-sucedido ou recuperação de senha concluída.                                                                                                                          | Importante |
| RF-006 | Se não existir nenhum usuário cadastrado, o sistema deve exibir, no lugar do login, o cadastro do Admin Final (primeiro acesso).                                                                                              | Essencial  |
| RF-007 | O sistema deve permitir encerrar a sessão (botão Sair) voltando ao login sem fechar o aplicativo.                                                                                                                             | Essencial  |
| RF-008 | Após o login, o sistema deve exibir no painel lateral o nome de exibição e o cargo de quem está logado.                                                                                                                       | Importante |
| RF-009 | O sistema deve restringir as funções conforme o cargo (seção 6), desabilitando os botões e bloqueando a ação também no código.                                                                                                | Essencial  |

### 3.2 Cadastro de usuários

| ID     | Requisito                                                                                                                                                                                                                                    | Prioridade |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-010 | O formulário de cadastro deve conter: nome completo, nome para exibição, e-mail, CPF, cargo, senha, confirmação da senha e três palavras-chave.                                                                                              | Essencial  |
| RF-011 | O nome completo deve ter ao menos duas palavras.                                                                                                                                                                                             | Importante |
| RF-012 | O nome para exibição é obrigatório e limitado a 25 caracteres.                                                                                                                                                                               | Importante |
| RF-013 | O e-mail deve ter formato válido e ser único no sistema (ignorando maiúsculas).                                                                                                                                                              | Essencial  |
| RF-014 | O CPF deve ser formatado automaticamente enquanto é digitado, validado pelos dígitos verificadores, rejeitando sequências repetidas (ex.: 111.111.111-11), e ser único. Ao completar 11 dígitos o sistema mostra “✔ válido” ou “✖ inválido”. | Essencial  |
| RF-015 | A senha deve ter no mínimo 8 caracteres, com pelo menos uma letra e um número, e a confirmação deve ser idêntica.                                                                                                                            | Essencial  |
| RF-016 | O formulário deve ter a opção “Mostrar senhas” para exibir ou ocultar a senha e a confirmação.                                                                                                                                               | Desejável  |
| RF-017 | As três palavras-chave devem conter apenas letras (4 a 20), sem espaços, e ser diferentes entre si (ignorando acentos e maiúsculas).                                                                                                         | Essencial  |
| RF-018 | Para cada palavra-chave, o sistema deve gerar três alternativas de escrita parecida e guardar as quatro opções, além do hash da palavra correta.                                                                                             | Essencial  |
| RF-019 | A senha e as palavras-chave nunca devem ser gravadas em texto puro; apenas hash com salt.                                                                                                                                                    | Essencial  |
| RF-020 | O Admin Final é cadastrado no primeiro acesso, com cargo fixo; os demais usuários são cadastrados pelo Admin Final com cargo Adm ou Usuário.                                                                                                 | Essencial  |

### 3.3 Recuperação de senha

| ID     | Requisito                                                                                                                                                                                   | Prioridade |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-021 | A tela de login deve ter o link “Esqueci minha senha”.                                                                                                                                      | Essencial  |
| RF-022 | Passo 1: o usuário deve digitar o CPF e o e-mail, que precisam pertencer ao mesmo cadastro; senão o sistema exibe “Os dados informados não conferem.” e, se o CPF existir, conta uma falha. | Essencial  |
| RF-023 | Passo 2: o sistema deve apresentar três perguntas (uma por palavra-chave), cada uma com quatro alternativas rotuladas de A a D, em ordem embaralhada.                                       | Essencial  |
| RF-024 | O usuário deve responder as três perguntas; se alguma estiver errada, a recuperação é encerrada, uma falha é contada e o sistema volta ao login.                                            | Essencial  |
| RF-025 | Passo 3: o usuário define a nova senha, que segue as regras do RF-015.                                                                                                                      | Essencial  |
| RF-026 | Se a conta estiver bloqueada, a recuperação não pode prosseguir e a mensagem de bloqueio é exibida.                                                                                         | Importante |
| RF-027 | Ao concluir, o sistema volta ao login e zera as tentativas da conta.                                                                                                                        | Importante |

### 3.4 Gestão de usuários (somente Admin Final)

| ID     | Requisito                                                                                                                                                                   | Prioridade |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-028 | A página Usuários deve listar: nome de exibição, nome completo, cargo, e-mail, CPF mascarado (ex.: ***.***.789-09) e status (Ativo ou Bloqueado com minutos restantes).     | Essencial  |
| RF-029 | A página “Cadastro de novos administradores” deve oferecer o formulário do RF-010 com cargo Adm ou Usuário; ao salvar, mostra confirmação e devolve o formulário em branco. | Essencial  |
| RF-030 | O Admin Final pode alternar o cargo de um usuário entre Adm e Usuário, com confirmação.                                                                                     | Importante |
| RF-031 | O cargo do Admin Final não pode ser alterado.                                                                                                                               | Essencial  |
| RF-032 | O Admin Final pode excluir um usuário, com confirmação; o próprio Admin Final não pode ser excluído.                                                                        | Essencial  |
| RF-033 | O Admin Final pode desbloquear manualmente uma conta bloqueada.                                                                                                             | Importante |
| RF-034 | A página Usuários deve ter o atalho “Novo administrador / usuário” que leva ao cadastro.                                                                                    | Desejável  |

### 3.5 Registro de entrada e saída

| ID     | Requisito                                                                                                                                                                                                       | Prioridade |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-035 | O formulário da portaria deve conter: nome da pessoa, tipo de acesso, data e hora da entrada, data e hora da saída.                                                                                             | Essencial  |
| RF-036 | A entrada deve vir preenchida com a data e a hora atuais.                                                                                                                                                       | Importante |
| RF-037 | O campo de data deve ter um calendário (navegação por mês e ano, botão Hoje) e o campo de hora deve ter um relógio de ponteiros (escolha da hora e depois dos minutos, botão Agora); também é possível digitar. | Essencial  |
| RF-038 | O nome da pessoa é obrigatório.                                                                                                                                                                                 | Essencial  |
| RF-039 | O tipo de acesso deve ser um tipo fixo ou um tipo temporário ainda ativo.                                                                                                                                       | Essencial  |
| RF-040 | Data e hora devem estar nos formatos dd/mm/aaaa e hh:mm, e são normalizadas ao gravar.                                                                                                                          | Essencial  |
| RF-041 | A saída é opcional; se for informada, data e hora devem vir juntas.                                                                                                                                             | Essencial  |
| RF-042 | A saída não pode ser anterior à entrada.                                                                                                                                                                        | Essencial  |
| RF-043 | Cada registro recebe um identificador único de 8 caracteres hexadecimais.                                                                                                                                       | Essencial  |
| RF-044 | Ao cadastrar, o sistema mostra “Registro cadastrado com sucesso!”, atualiza a tabela e limpa o formulário.                                                                                                      | Essencial  |
| RF-045 | O botão Limpar restaura o formulário (entrada com data/hora atuais, saída vazia).                                                                                                                               | Importante |
| RF-046 | A tecla Enter nos campos do formulário deve acionar o cadastro.                                                                                                                                                 | Desejável  |

### 3.6 Tipos de acesso e tipos temporários

| ID     | Requisito                                                                                                                                                 | Prioridade |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-047 | Os tipos fixos são: Visitante, Morador, Entregador e Funcionário.                                                                                         | Essencial  |
| RF-048 | A lista de tipos deve ter a opção “+ Novo tipo temporário...”, que abre um painel para digitar o nome (ex.: Mecânico).                                    | Importante |
| RF-049 | Um tipo temporário fica disponível na lista por 24 horas a partir da criação; depois sai da lista e permanece arquivado no arquivo tipos_temporarios.csv. | Importante |
| RF-050 | Se o nome informado já existe como tipo temporário ativo, ele é reutilizado; se for igual a um tipo fixo, usa-se o fixo (ignorando maiúsculas e acentos). | Importante |
| RF-051 | O sistema deve verificar as validades a cada 60 segundos; se o tipo selecionado vencer, a seleção volta ao primeiro tipo.                                 | Importante |
| RF-052 | Registros com tipo temporário mantêm o nome do tipo para sempre e aparecem com “\*” e em cor diferente na tabela.                                         | Importante |
| RF-053 | Um tipo temporário vencido não pode ser usado em novos cadastros.                                                                                         | Essencial  |

### 3.7 Consulta e pesquisa no histórico

| ID     | Requisito                                                                                                                                                                                                         | Prioridade |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-054 | A tabela deve mostrar: Nome, Tipo de acesso, Entrada e Saída (“—” quando vazia).                                                                                                                                  | Essencial  |
| RF-055 | Os registros devem aparecer do mais recente para o mais antigo (ordem de inclusão).                                                                                                                               | Importante |
| RF-056 | Registros sem saída devem ser destacados em amarelo.                                                                                                                                                              | Importante |
| RF-057 | A pesquisa deve filtrar enquanto se digita, em nome, tipo, entrada e saída, aceitando várias palavras (todas devem aparecer), ignorando maiúsculas e acentos; a palavra “temporario” filtra os tipos temporários. | Essencial  |
| RF-058 | O filtro “Somente sem saída” deve mostrar apenas quem ainda está no local.                                                                                                                                        | Essencial  |
| RF-059 | O botão “Limpar filtro” deve remover a pesquisa e o filtro.                                                                                                                                                       | Importante |
| RF-060 | Um contador deve mostrar quantos registros estão exibidos, o total e quantos estão sem saída.                                                                                                                     | Desejável  |

### 3.8 Registro de saída

| ID     | Requisito                                                                                                                             | Prioridade |
|--------|---------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-061 | O botão “Registrar saída” deve preencher a saída do registro selecionado na tabela (um por vez), inclusive de quem entrou dias antes. | Essencial  |
| RF-062 | Deve usar a data e a hora de saída do formulário; se estiverem vazias, usa o momento atual.                                           | Importante |
| RF-063 | Deve recusar se o registro já tem saída (orientando a editar a célula) ou se a saída for anterior à entrada.                          | Essencial  |
| RF-064 | O primeiro preenchimento da saída não gera evento de auditoria.                                                                       | Essencial  |

### 3.9 Edição de registros

| ID     | Requisito                                                                                                                                                                                                                                         | Prioridade |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-065 | O duplo clique em uma célula deve permitir editar: Nome (campo na própria célula; Enter confirma, Esc cancela), Tipo (menu com os tipos e a opção de novo temporário), Entrada e Saída (calendário e depois relógio; na saída é possível limpar). | Essencial  |
| RF-066 | Ao editar Entrada ou Saída, o sistema deve manter a regra RF-042.                                                                                                                                                                                 | Essencial  |
| RF-067 | Toda alteração, exceto o RF-064, deve gerar um evento de auditoria “EDIÇÃO” com valor anterior, novo valor e responsável.                                                                                                                         | Essencial  |
| RF-068 | Após editar, o sistema deve exibir uma mensagem com o campo alterado, o valor anterior e o novo valor.                                                                                                                                            | Importante |
| RF-069 | O cargo Usuário só pode editar a saída de registros que ainda não a têm.                                                                                                                                                                          | Essencial  |
| RF-070 | Uma edição que não muda o valor não gera evento nem mensagem.                                                                                                                                                                                     | Desejável  |

### 3.10 Exclusão de registros

| ID     | Requisito                                                                                                           | Prioridade |
|--------|---------------------------------------------------------------------------------------------------------------------|------------|
| RF-071 | O botão “Excluir selecionado” deve remover um ou vários registros selecionados, após confirmação.                   | Essencial  |
| RF-072 | Cada registro excluído deve gerar um evento “EXCLUSÃO” guardando o registro completo (nome, tipo, entrada e saída). | Essencial  |
| RF-073 | Somente Admin Final e Adm podem excluir.                                                                            | Essencial  |

### 3.11 Registro de auditoria

| ID     | Requisito                                                                                                                                   | Prioridade |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-074 | A página Registro de auditoria deve listar: data/hora, ação, responsável, pessoa, campo, valor anterior e novo valor.                       | Essencial  |
| RF-075 | Os eventos devem aparecer do mais recente ao mais antigo, com edições em amarelo e exclusões em vermelho claro.                             | Importante |
| RF-076 | Deve haver filtro Todos, Edições ou Exclusões.                                                                                              | Importante |
| RF-077 | Ao selecionar uma linha, o detalhe completo (ação, data, pessoa, responsável, campo, valor anterior e novo) deve aparecer abaixo da tabela. | Importante |
| RF-078 | Um contador deve mostrar o número de eventos exibidos.                                                                                      | Desejável  |
| RF-079 | A página é acessível apenas para Admin Final e Adm.                                                                                         | Essencial  |

### 3.12 Interface e navegação

| ID     | Requisito                                                                                                                                                                         | Prioridade |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-080 | O aplicativo deve rodar em uma única janela: avisos, confirmações, perguntas, calendário e relógio aparecem como painéis dentro da janela, bloqueando o fundo até serem fechados. | Essencial  |
| RF-081 | A tecla Esc deve fechar (cancelar) o painel aberto.                                                                                                                               | Importante |
| RF-082 | O painel lateral deve poder ser ocultado e reexibido pelo botão ☰.                                                                                                                | Essencial  |
| RF-083 | O painel lateral deve ter os itens Portaria, Usuários, Registro de auditoria e Cadastro de novos administradores, exibindo apenas os permitidos ao cargo.                         | Essencial  |
| RF-084 | O item da página atual deve ficar destacado e o título da página deve aparecer na barra superior.                                                                                 | Importante |
| RF-085 | A barra de título deve seguir o tema do aplicativo e conter os botões Minimizar, Maximizar/Restaurar e Fechar.                                                                    | Importante |
| RF-086 | A janela deve poder ser arrastada pela barra de título, maximizada com duplo clique e redimensionada pelo canto inferior direito, respeitando o tamanho mínimo.                   | Importante |
| RF-087 | O visual deve usar a paleta creme e verde selva, com botões de cantos arredondados, borda destacada e efeitos ao passar o mouse, pressionar e desabilitar.                        | Importante |
| RF-088 | A constante BARRA_TITULO_PERSONALIZADA deve permitir voltar à barra de título nativa do sistema.                                                                                  | Desejável  |
| RF-089 | Login, primeiro acesso e recuperação de senha devem aparecer no mesmo cartão central, sem abrir novas janelas.                                                                    | Importante |

### 3.13 Persistência de dados

| ID     | Requisito                                                                                                                                                          | Prioridade |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| RF-090 | Os registros da portaria devem ser gravados em registros_portaria.csv a cada alteração.                                                                            | Essencial  |
| RF-091 | Ao abrir, o sistema deve carregar os registros e converter arquivos da versão 1 (sem identificador), gerando um Id para cada linha.                                | Importante |
| RF-092 | Os eventos de auditoria devem ser gravados em auditoria_portaria.csv.                                                                                              | Essencial  |
| RF-093 | Os tipos temporários devem ser gravados em tipos_temporarios.csv.                                                                                                  | Importante |
| RF-094 | Os usuários devem ser gravados em usuarios_portaria.json; se o arquivo existir mas estiver ilegível, o sistema deve informar o erro e encerrar sem sobrescrevê-lo. | Essencial  |
| RF-095 | Todos os arquivos ficam na mesma pasta do programa.                                                                                                                | Importante |
