# ADAPT Hackathon Demonstration Video Script (<90 Seconds)

## Video Overview
- **Duration:** 80 seconds
- **Format:** Screen recording of terminal + concise voiceover
- **Objective:** Demonstrate persistent memory continuity, hybrid recall, knowledge graph linking, and context compression preservation in Hermes Agent.

---

### [0:00 - 0:15] The Hook & Problem
- **Visual:** Terminal showing a blank agent prompt.
- **Voiceover:**
  > "Most AI agents wake up with amnesia. They lose context when sessions end, forget your preferences, and start from zero every single time.
  > This is **ADAPT**: Persistent memory infrastructure for autonomous agents. Build once. Remember continuously."

---

### [0:15 - 0:35] Session 1: Ingestion & Knowledge Graph
- **Visual:** Hermes agent running with ADAPT memory provider active (`🧠`).
  Agent receives instructions:
  `"We decided our database is PostgreSQL 16 on Supabase, and migrations run with alembic upgrade head."`
- **Voiceover:**
  > "In Session 1, ADAPT ingests and classifies interactions into four distinct tiers: Episodic, Semantic, Procedural, and Working memory.
  > Notice how it automatically links the database fact to the migration runbook in an associative knowledge graph."

---

### [0:35 - 0:55] Session 2: Continuity After Reboot
- **Visual:** Terminal: Process is killed (`Ctrl+C` or session reset). A new session starts.
  User asks: `"How do we run migrations for our database?"`
  Hermes instantly prefetches the exact procedural memory and PostgreSQL context from SQLite FTS5.
- **Voiceover:**
  > "We terminate the session, restart the agent, and ask how to run migrations.
  > Without repeating any context, ADAPT instantly prefetches the exact answer using hybrid BM25 lexical and semantic vector search."

---

### [0:55 - 1:15] Context Compression & Evolution
- **Visual:** Run compression test showing `on_pre_compress` rescuing facts before context compaction.
  User updates preference to MySQL, showing the previous version preserved in audit history rather than silently destroyed.
- **Voiceover:**
  > "Even when context windows compact, ADAPT's `on_pre_compress` hook rescues critical decisions before truncation.
  > When information changes, older versions are preserved in an immutable audit trail—never silently overwritten."

---

### [1:15 - 1:20] Call to Action & Conclusion
- **Visual:** GitHub repo and Hermes catalog entry: `hermes plugins install adapt`.
- **Voiceover:**
  > "ADAPT is local-first, zero-dependency, and ready for Hermes Agent. Check out the repository on GitHub!"
