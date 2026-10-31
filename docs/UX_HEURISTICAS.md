# Interface v2 — avaliação das 10 heurísticas de Nielsen

**Escopo:** interface desktop Tk/ttk. Checklist de implementação, **não** substitui testes com usuários nem avaliação formal de acessibilidade.

| Heurística | Aplicação prática | Limite atual |
|---|---|---|
| 1. Visibilidade do estado do sistema | Indicadores de total/pendências, estado de sessão, mensagens de sucesso e erros. | Operações síncronas grandes ainda podem bloquear a UI temporariamente. |
| 2. Correspondência com o mundo real | Linguagem de portaria: entrada, saída, pendente, tipo de acesso. | Nomes de papéis antigos (`Adm`, `Admin Final`) mantidos por compatibilidade. |
| 3. Controle e liberdade | Cancelamento nos diálogos, botão limpar, retorno ao login, escolha de data/hora. | Não existe um undo geral após exclusão; confirmação e auditoria são a mitigação. |
| 4. Consistência e padrões | Botões, títulos, superfícies, paleta e controles reutilizados por todas as telas. | Alguns widgets nativos diferem visualmente conforme o SO. |
| 5. Prevenção de erros | Datas/horas com máscara e verificação de calendário; limites de nome/CPF; permissão no serviço; confirmação antes de excluir. | Digitação em datas parciais ainda exige conferência antes de salvar. |
| 6. Reconhecimento em vez de memorização | Tipo em lista, calendário e relógio, rotulagem explícita, status de saída e papéis visíveis. | Recuperação por três palavras legada impõe carga de memória ao usuário. |
| 7. Flexibilidade e eficiência | Busca incremental, filtro pendências, duplo clique para editar, horário atual em um toque. | Não há atalhos customizáveis e comandos em lote complexos. |
| 8. Estética e minimalismo | Campos essenciais em cards, sidebar com navegação, tema consistente e modo compacto em janela estreita. | Em telas muito baixas a navegação depende de rolagem. |
| 9. Recuperação diante de erros | Mensagem contextual, não confirma persistência se disco falhar, falhas no log, backup orientado. | Erros de cofre corrompido exigem restauração manual de backup. |
| 10. Ajuda e documentação | Configurações explicam cofre e temas; README contém guia de primeiro acesso, migração e segurança. | Ajuda contextual em cada campo pode ser ampliada. |

## Recomendações de aceite

- Testar janela nas larguras ~800 px, 1024 px, 1280 px e 1600 px no Windows.
- Testar com teclado, alto contraste, zoom de fontes do SO e leitores de tela; Tk/ttk tem limites para semântica acessível moderna.
- Confirmar com operadores que os fluxos mais frequentes (nova entrada, pesquisa e saída) exigem poucos cliques e que mensagens de erros indicam uma ação concreta.
- Validar responsividade **desktop** e não classificar esta solução como web/mobile.
