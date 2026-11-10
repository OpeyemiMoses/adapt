# ADAPT Configuration Guide

ADAPT is designed with sensible local-first defaults so that a new user needs zero manual configuration to get started.

## Configuration Options

| Environment Variable | Config YAML Key | Default | Description |
| :--- | :--- | :--- | :--- |
| `ADAPT_STORAGE_DIR` | `storage_dir` | `~/.hermes/adapt` | Directory where SQLite database and local files reside |
| `ADAPT_DB_NAME` | `db_name` | `adapt_memory.db` | SQLite database file name |
| `ADAPT_DEFAULT_TOP_K` | `top_k` | `5` | Maximum number of memories recalled per prefetch / query |
| `ADAPT_HYBRID_ALPHA` | `hybrid_alpha` | `0.5` | Weight between semantic (1.0) and lexical (0.0) search |
| `ADAPT_MIN_RELEVANCE` | `min_score` | `0.20` | Minimum score threshold for recalled memories |
| `ADAPT_EMBEDDING_PROVIDER` | `embeddings.provider` | `hash` | `hash` (offline zero-dependency), `none` (FTS5 BM25 fallback), or `remote` |
| `ADAPT_WORKING_MEMORY_TTL` | `working_ttl_hours` | `24` | Hours before inactive working memories are eligible for archival |
| `ADAPT_AUTO_CONSOLIDATE` | `auto_consolidate` | `true` | Whether to run consolidation on session end hooks |
| `ADAPT_LOG_LEVEL` | `logging_level` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Hermes Agent Plugin Configuration
When configured inside `~/.hermes/config.yaml`:
```yaml
memory:
  provider: adapt

adapt:
  storage_dir: ~/.hermes/adapt
  top_k: 5
  hybrid_alpha: 0.5
```

