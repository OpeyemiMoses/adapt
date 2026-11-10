# ADAPT Hackathon Submission Checklist

## 1. Repository Information
- **Repository Name:** `adapt`
- **Tagline:** Build once. Remember continuously.
- **Project Type:** Persistent Agent Memory Infrastructure Layer
- **Target Integration:** Hermes Agent Memory Provider Plugin (`agent.memory_provider.MemoryProvider`)
- **License:** Apache-2.0

## 2. Verification Evidence
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

## 3. Submission Links
- **GitHub Repository:** `https://github.com/adapt-memory/adapt`
- **Catalog Pull Request:** Proposed entry in `NousResearch/hermes-agent` at `plugin-catalog/adapt.yaml`
- **Hackathon Form:** [Typeform Submission](https://form.typeform.com/to/FwJLvOln)
- **X (Twitter) Tag:** [@NousResearch](https://x.com/NousResearch)

