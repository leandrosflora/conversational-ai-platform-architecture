# knowledge-service

Repo: [`leandrosflora/knowledge-service`](https://github.com/leandrosflora/knowledge-service) · Stack: Python, FastAPI, OpenSearch, OpenAI Embeddings · Local port: `8500`

## Primary responsibility

RAG (retrieval-augmented generation) service for renegotiation FAQs: it ingests PDFs, splits them into chunks, embeds each chunk through OpenAI, and indexes them in OpenSearch with vector k-NN search. It exposes `GET /search` — already consumed by `agent-runtime-renegotiation` through the `search_knowledge_base` tool — and `POST /admin/reindex` to reprocess content without restarting the service.

## Data owned by the service

There is no in-memory domain model of its own — all state lives in OpenSearch, in a **per-tenant index** `faq_chunks-{tenantId}`. Each chunk document contains `text`, `title`, `sourceFile`, `chunkIndex`, `contentHash`, `createdAt`, `tenantId`, and `embedding` — a 1,536-dimension k-NN vector using `hnsw`/`cosinesimil` with the `lucene` engine.

## Published APIs

| Method | Route | Description |
|---|---|---|
| `GET` | `/search?query=...` | Embeds the query, performs k-NN search in the current tenant index, filters by `min_relevance_score` (default `0.70`), and returns results ordered by score |
| `POST` | `/admin/reindex` | Reprocesses the current tenant's `.pdf` files on demand without restarting the process |

Both endpoints require a resolved tenant — `400` for malformed `X-Tenant-Id`, `401` for missing/invalid bearer token, or `403` when the tenant claim does not match, all before the handler runs. `GET /search` returns `200 OK` with `results: []` when nothing relevant is found; this is a normal result, not an error. Both endpoints return `503 Service Unavailable` rather than a raw `500` or hang when OpenSearch or the OpenAI Embeddings API is unavailable (`KnowledgeBackendUnavailableError`, mapped by a central exception handler in `app/main.py`).

## Published events

None.

## Consumed events

None.

## Synchronous dependencies

| Destination | Behavior when unavailable |
|---|---|
| OpenSearch (`:9200`) | Client configured with `timeout=3s`, `max_retries=0`; without this, the default `opensearch-py` retry behavior would multiply the failure time to roughly 9 seconds before a `503` could be returned. Any `OpenSearchException` becomes `KnowledgeBackendUnavailableError` → `503` |
| OpenAI Embeddings API (external, real) | Without `OPENAI_API_KEY`, `embed_texts` refuses to call the API and immediately raises `KnowledgeBackendUnavailableError`. With a configured key but an unavailable API, the SDK error becomes the same `KnowledgeBackendUnavailableError` |

## Persistence and infrastructure

- **OpenSearch** (`faq_chunks-{tenantId}`, one index per tenant): the service's only real storage — text chunks, embeddings, and k-NN search.
- PDF ingestion reads from `data/faq_pdfs/{tenantId}/` (bind-mounted in `docker-compose.yml`, so dropping a PDF there makes it visible to `POST /admin/reindex` without rebuilding the image). The seed tenant in the local environment falls back to the root `data/faq_pdfs/` directory when no tenant-specific subfolder exists, preserving compatibility with demo content that predates multitenancy.
- No relational or document database.

## Business rules

1. **Content-hash idempotency**: each file has a `contentHash` calculated during extraction. If the indexed hash matches the current hash **and** the indexed chunk count matches `len(chunks)` for the file, the file is skipped (`files_skipped`); only new or changed files are reprocessed.
2. **Partial-ingestion detection**: a matching hash alone does not prove that the previous indexing operation completed. A chunk write may have timed out on the client while succeeding on the server. The indexed chunk count is therefore also checked; when it differs from the expected count, the file is reingested even if the hash is unchanged.
3. **Rollback on partial failure**: if the backend fails while writing chunks for one file, chunks already written for that file are removed. Leaving a partial state would allow `get_indexed_hash` to see a matching hash and skip the file forever, never completing the ingestion that actually failed.
4. A backend failure (OpenSearch/OpenAI) during batch ingestion of `data/faq_pdfs/` **aborts the rest of the batch**. If the backend is down, all remaining files would fail the same way; one explicit failure is preferred over N identical failure records.
5. With no PDFs under `data/faq_pdfs/`, the service starts normally and `GET /search` returns `200` with `results: []` for any query — absence of content is not an error condition.
6. `refresh_index` is called once after all chunks for a file are indexed, not after each individual chunk, preventing unnecessary serialization and latency that could exceed the client's 3-second timeout against an otherwise healthy cluster.

## Architecture references

- [Journey sequence diagrams](../architecture/sequence-diagrams.md)
- [Contracts — Datastores](../contracts/data-stores.md)
