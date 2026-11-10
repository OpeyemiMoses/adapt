## Pull Request Description

### Summary of Changes
Please include a summary of the change and which issue is addressed.

### Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Verification & Testing Evidence

### Automated Tests
- [ ] All unit, integration, and security tests pass locally (`pytest tests/`).
- [ ] Added new tests covering modified or added functionality.

### Hermes Plugin Conformance
- [ ] Conformance probe passes with zero warnings:
  ```bash
  python -m hermes_cli.plugin_validate ./integrations/hermes --install-deps
  ```
- [ ] Catalog schema validation passes:
  ```bash
  python scripts/validate_plugin_catalog.py integrations/hermes/catalog_entry.yaml
  ```

## Checklist
- [ ] My code follows the code style and guidelines of this project.
- [ ] I have commented my code, particularly in hard-to-understand areas.
- [ ] I have updated corresponding documentation in `docs/` and `README.md`.
- [ ] I have not introduced any secrets, API keys, or private core imports.
