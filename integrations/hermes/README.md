# ADAPT Hermes Plugin

Official **Memory Provider Plugin** for Hermes Agent (`agent.memory_provider.MemoryProvider`).

## Capabilities
- **Turn Synchronization (`sync_turn`)**: Automatically records conversations and extracts durable user preferences.
- **Context Prefetching (`prefetch`)**: Recalls relevant long-term memories prior to each LLM generation with transparent indicators (`🧠`).
- **Pre-Compression Preservation (`on_pre_compress`)**: Rescues decisions, constraints, and goals before context window truncation.
- **Session End Maintenance (`on_session_end`)**: Runs consolidation, deduplication, and working memory TTL archival.
- **Custom Tool Suite**: Exposes `adapt_remember`, `adapt_recall`, `adapt_update`, `adapt_forget`, `adapt_relate`, and `adapt_stats`.

## Installation & Setup
```bash
# Validate local plugin
hermes plugins validate ./integrations/hermes --install-deps

# Install plugin
hermes plugins install /path/to/adapt/integrations/hermes
```

## Activation
In `~/.hermes/config.yaml`:
```yaml
memory:
  provider: adapt

adapt:
  storage_dir: ~/.hermes/adapt
  top_k: 5
```
Or via interactive wizard:
```bash
hermes memory setup
# Select 'adapt'
```

