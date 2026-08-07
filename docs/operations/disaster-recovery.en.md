# Backup, Restore, and Recovery

## Current classification

The Docker Compose environment is intended for development and homologation. The provided scripts exercise procedures and produce evidence; they do not represent enterprise backup with immutable retention, geographic replication, or managed encryption.

## Reference RPO/RTO

| Component | Local strategy | Initial RPO | Initial RTO |
|---|---|---:|---:|
| PostgreSQL | `pg_dump`/`pg_restore` | 24 h | 2 h |
| MongoDB | `mongodump`/`mongorestore` | 24 h | 2 h |
| Redis | rebuildable cache/session; inventory included in backup | according to TTL | 1 h |
| OpenSearch | rebuild from source documents | according to ingestion | 4 h |
| Kafka | rebuild/replay according to retention | according to retention | 4 h |
| Configuration | Git + checksums | per commit | 1 h |

## Local backup

```bash
scripts/backup-local.sh
```

The package contains PostgreSQL and MongoDB dumps, Redis/Kafka/OpenSearch inventories, redacted Compose files, and `SHA256SUMS`.

## Local restore

Restore is deliberately blocked by default:

```bash
ALLOW_DESTRUCTIVE_RESTORE=true \
  scripts/restore-local.sh backups/<timestamp>
```

It recreates PostgreSQL and MongoDB. Redis is reset/rebuilt by local design. Kafka and OpenSearch remain classified as rebuildable in the local environment.

## Required drill

Before promoting a release:

1. start a disposable environment;
2. insert test data;
3. generate a backup;
4. validate checksums;
5. destroy data volumes;
6. restore PostgreSQL and MongoDB;
7. reprocess the documents/events required for Redis, Kafka, and OpenSearch;
8. execute readiness and the E2E journey;
9. record RPO, RTO, and evidence under `docs/validation/`.

## Production

The final implementation must add:

- encrypted and immutable storage;
- policy-based retention and expiration;
- copies in a separate region/account;
- backup credentials separated from application credentials;
- automated periodic restore tests;
- restore evidence, not only backup evidence;
- a disaster declaration and communication runbook.
