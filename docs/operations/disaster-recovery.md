# Backup, restore e recuperação

## Classificação atual

O ambiente Docker Compose é de desenvolvimento e homologação. Os scripts fornecidos exercitam procedimentos e evidências; não representam backup corporativo com retenção imutável, replicação geográfica ou criptografia gerenciada.

## RPO/RTO de referência

| Componente | Estratégia local | RPO inicial | RTO inicial |
|---|---|---:|---:|
| PostgreSQL | `pg_dump`/`pg_restore` | 24 h | 2 h |
| MongoDB | `mongodump`/`mongorestore` | 24 h | 2 h |
| Redis | cache/sessão reconstruível; inventário no backup | conforme TTL | 1 h |
| OpenSearch | reconstrução por documentos de origem | conforme ingestão | 4 h |
| Kafka | reconstrução/replay conforme retenção | conforme retenção | 4 h |
| Configuração | Git + checksums | por commit | 1 h |

## Backup local

```bash
scripts/backup-local.sh
```

O pacote contém dumps de PostgreSQL e MongoDB, inventário Redis/Kafka/OpenSearch, arquivos Compose redigidos e `SHA256SUMS`.

## Restore local

O restore é deliberadamente bloqueado por padrão:

```bash
ALLOW_DESTRUCTIVE_RESTORE=true \
  scripts/restore-local.sh backups/<timestamp>
```

Ele recria PostgreSQL e MongoDB. Redis é reinicializado/reconstruído por desenho local. Kafka e OpenSearch permanecem classificados como reconstruíveis no ambiente local.

## Drill obrigatório

Antes de promover uma release:

1. iniciar ambiente descartável;
2. inserir dados de teste;
3. gerar backup;
4. validar checksums;
5. destruir os volumes de dados;
6. restaurar PostgreSQL e MongoDB;
7. reprocessar documentos/eventos necessários para Redis, Kafka e OpenSearch;
8. executar readiness e jornada E2E;
9. registrar RPO, RTO e evidências em `docs/validation/`.

## Produção

A implementação final precisa acrescentar:

- armazenamento criptografado e imutável;
- retenção e expiração por política;
- cópia em região/conta separada;
- credenciais de backup separadas das credenciais da aplicação;
- restore periódico automatizado;
- evidência de restore, não apenas evidência de backup;
- runbook de declaração de desastre e comunicação.
