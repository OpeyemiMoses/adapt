# Security Policy

## Supported Versions

ADAPT is actively developed. Security updates are applied to the latest release on the `main` branch.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of ADAPT and persistent agent memory seriously. If you discover a security vulnerability, please report it responsibly:

1. **Do not create a public GitHub issue.**
2. Send an email to `security@adapt-memory.org` or contact the maintainer directly via GitHub Security Advisories.
3. Include detailed steps to reproduce the issue, environment information, and any potential mitigation.

### Response Timeline
- **Initial Acknowledgment:** Within 24 hours.
- **Triage & Assessment:** Within 72 hours.
- **Fix & Disclosure:** Coordinated release within 14 business days.

## Security Architecture Highlights
- **Tenant Isolation:** All database queries, full-text indexes, and graph traversals are strictly partitioned by `agent_id`.
- **FTS5 Injection Mitigation:** All user queries undergo strict sanitization (`re.escape` of SQLite FTS5 operators such as `AND`, `OR`, `NOT`, `NEAR`, colons, asterisks, and unbalanced quotes) to prevent query injection attacks.
- **Atomic Persistence:** SQLite WAL mode ensures transactional ACID guarantees without uncommitted state leakage.
- **Local Sovereignty:** Zero telemetry, zero external network calls by default, and offline deterministic vector hashing to prevent data leakage.
