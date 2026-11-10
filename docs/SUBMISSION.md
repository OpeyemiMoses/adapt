# ADAPT - Hermes Agent Plugin Hackathon Submission

## 1. Hackathon Overview & Match
- **Hackathon:** Hermes Agent Plugin Hackathon (Nous Research)
- **Deadline:** **5:00 PM EST on November 11th**
- **Category Match:** *"A plugin can change anything from the model Hermes runs on, **where it stores its memory**, where it runs commands..."*
- **Judging Focus:** 
  - **Usefulness:** Multi-tiered memory (Episodic, Semantic, Procedural, Working) that prevents amnesia.
  - **Reliability:** 100% test pass rate (40/40), atomic SQLite WAL persistence, thread safety, and fallback recovery.
  - **Polish:** Fully documented, clean CLI validation (0 warnings, 0 errors), zero-config setup.
  - **Creativity & Beyond Prompt/Skills:** Deep runtime hooks (`on_pre_compress`, `prefetch`, `sync_turn`), SQLite FTS5 + cosine vector search, recency decay, and non-destructive graph updates (`SUPERSEDES`). A prompt or skill cannot intercept context compression or survive reboots.

## 2. Prize Target
- **1st Prize:** $10,000 + Neon sign + Merch + $1,000 credits
- **Total Prize Pool:** $20,000 across top 5 + 5 runners-up

## 3. Submission Steps & Links
1. **GitHub Repository:** Push this repository to GitHub: `https://github.com/OpeyemiMoses/adapt`.
2. **Open Pull Request on NousResearch/hermes-agent:**
   - Add [`integrations/hermes/catalog_entry.yaml`](file:///Users/user/.gemini/antigravity/scratch/adapt/integrations/hermes/catalog_entry.yaml) into `plugin-catalog/adapt.yaml` in the `NousResearch/hermes-agent` repository.
   - Reference: [Catalog Submission Guide](http://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission)
3. **Record & Post Demo Video on X:**
   - Under 90 seconds (Script ready in [`docs/DEMO_SCRIPT.md`](file:///Users/user/.gemini/antigravity/scratch/adapt/docs/DEMO_SCRIPT.md) ~75s).
   - Tag [@NousResearch](https://x.com/NousResearch).
4. **Submit Typeform:**
   - Complete form at [http://form.typeform.com/to/FwJLvOln](http://form.typeform.com/to/FwJLvOln) with your PR and X video link.

## 4. Verification Evidence
- **Automated Tests:** 40 passing tests across unit, integration, security, and e2e (`pytest tests/`).
- **Official Plugin Validation:**
  ```bash
  hermes plugins validate ./integrations/hermes --install-deps
  # Result: OK: True (0 warnings, 0 failures)
  ```
- **Official Catalog Schema Validation:**
  ```bash
  python3 scripts/validate_plugin_catalog.py integrations/hermes/catalog_entry.yaml
  # Result: OK: 1 file(s) valid
  ```

