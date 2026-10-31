# Histórico de mudanças

## 2.0.1 — correção de formulário cortado

- Adiciona rolagem vertical com barra visível, roda do mouse e deslocamento ao focar campos fora da tela nos formulários de autenticação.
- Centraliza os cartões apenas quando cabem; remove largura mínima artificial que cortava formulários menores.
- Reorganiza o formulário de primeiro acesso e novos usuários em uma coluna na largura compacta.
- Faz a janela de cadastro de usuários rolável e reduz a dimensão mínima do desktop para suportar resoluções menores.
- Inclui testes gráficos de rolagem, botão final visível e alternância entre layouts estreito/amplo.

## 2.0 — nova interface e reforço de arquitetura

- Substitui a apresentação antiga por `presentation_v2` com tema Claro, Escuro e Floresta e composição adaptativa desktop.
- Divide as operações da aplicação entre acesso, identidade e ciclo de vida do cofre, com fachada `PortariaService` preservada.
- Centraliza RBAC em `domain/permissions.py`; a UI reflete as capacidades, mas não é a barreira de autorização.
- Introduz chave de operação para idempotência de cadastro persistente no ID, guarda contra reentrância e edição multicoluna atômica.
- Audita cadastro de usuários, alterações de papéis, desbloqueios, exclusões e tipos temporários sem armazenar senhas na auditoria.
- Recuperação de contas passa a usar token efêmero validado na aplicação, de uso único.
- Implementa lock de instância local e detecção otimista de mudanças externas no arquivo criptografado.
- Mantém cofre **PORTARIA-COFRE-v2** original com AES-256-GCM e compatibilidade de hashes de contas.
- Adiciona `--data-dir` para selecionar a pasta de dados (padrão anterior mantido).
- Substitui testes da UI antiga por testes de versão 2; inclui documentação das 10 heurísticas e modelo de ameaças.

## Compatibilidade

**Não existe migração de formato ao atualizar do cofre v2 anterior para esta edição.** Para migrar CSVs/JSON legados, siga `README.md`. Não distribua arquivos de dados reais junto do projeto.
