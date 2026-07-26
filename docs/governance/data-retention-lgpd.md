# Retenção, classificação e LGPD

## Princípios

- coletar somente o necessário para a finalidade da jornada;
- separar identificadores operacionais de conteúdo sensível;
- definir retenção por classe de dado;
- permitir localização, correção, anonimização e exclusão;
- preservar evidência regulatória sem manter conteúdo além do necessário;
- registrar quem executou cada operação administrativa.

## Matriz inicial

| Classe | Exemplo | Store | Retenção de referência | Tratamento |
|---|---|---|---:|---|
| Conteúdo de conversa | texto enviado pelo cliente | MongoDB | 90 dias | exclusão/anonimização por titular e tenant |
| Estado operacional | Inbox, estado, Outbox | PostgreSQL | 180 dias | purge após conclusão e janela de reconciliação |
| Auditoria | tool, decisão, status | PostgreSQL | 5 anos, sujeito à política regulatória | minimizar payload e restringir acesso |
| Sessão/cache | contexto temporário | Redis | TTL de horas/dias | expiração automática |
| Logs | eventos técnicos sem conteúdo | Loki | 30 dias | redaction e expiração |
| Traces | spans e correlação | Jaeger/backend | 7–14 dias | sem payload sensível |
| Base RAG | documentos/chunks | OpenSearch/origem | vigência contratual | exclusão na origem e reindexação |

Os prazos são referência técnica, não decisão jurídica. Jurídico, LGPD e negócio devem aprovar a política final.

## Controles necessários

1. catálogo de campos com classificação;
2. redaction centralizada antes de logs, métricas e traces;
3. API/processo de busca por titular e tenant;
4. exclusão com tombstone e evidência;
5. anonimização quando retenção regulatória impedir exclusão integral;
6. reindexação de OpenSearch após exclusão na origem;
7. métricas de backlog de solicitações;
8. testes automatizados que provem que CPF e conteúdo não viram labels.

## Evidência mínima

Cada solicitação deve registrar:

- identificador da solicitação;
- base legal/finalidade;
- tenant;
- stores consultados;
- quantidade de registros alterados;
- resultado e falhas;
- operador/workload;
- timestamp;
- hash do relatório de execução.
