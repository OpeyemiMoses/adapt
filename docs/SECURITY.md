# ADAPT Security and Privacy Model

## 1. Principles
- **Local-First Data Ownership**: By default, memories remain strictly on the user's local machine in SQLite. No data is sent to external services unless the user explicitly configures a remote embedding provider.
- **Strict Tenant & Agent Isolation**: All queries enforce `owner_id` boundaries. Unauthorized cross-user or cross-agent leakage is prevented at the database query layer.
- **Data Not Code**: Memories retrieved into prompt context are tagged as untrusted informational context (`<recalled_context provider="adapt">`). They are never interpreted as executable instructions or system prompts.
- **Immutable Provenance & Versioning**: Critical updates do not overwrite historical records. All updates generate an audit record in `memory_versions`.
- **Soft and Hard Deletion**: Memories marked for deletion are immediately excluded from recall and search queries, with permanent purging available on request.
- **No Hardcoded Credentials**: API tokens and keys are read exclusively from environment variables or secure profile stores.

