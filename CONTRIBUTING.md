# Contributing to ADAPT

Thank you for your interest in contributing to **ADAPT**! We welcome community contributions, bug fixes, enhancements, and ecosystem adapters.

---

## Code of Conduct

All contributors must adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Development Setup

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- `uv` (recommended) or standard `pip` / `venv`
- `git`

### Quickstart
```bash
git clone https://github.com/OpeyemiMoses/adapt.git
cd adapt

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
pip install pytest pytest-cov ruff
```

---

## Branching Strategy & Workflow

1. Fork the repository and create your feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Follow Conventional Commits:
   - `feat(...)`: New functionality
   - `fix(...)`: Bug fix
   - `docs(...)`: Documentation updates
   - `test(...)`: Adding or updating tests
   - `refactor(...)`: Code improvement without feature change
3. Run the automated test suite before opening a pull request:
   ```bash
   pytest tests/
   ```
4. If modifying the Hermes integration (`integrations/hermes`), run the official validation check:
   ```bash
   python -m hermes_cli.plugin_validate ./integrations/hermes --install-deps
   ```

---

## Coding Standards

- **Type Hints:** All function and method signatures must include Python type annotations.
- **Async/Sync Boundaries:** Core memory engine methods are synchronous and thread-safe. Hermes provider methods implement Hermes lifecycle async/sync contracts.
- **Documentation:** Maintain existing docstrings. Add docstrings to newly introduced public classes and methods.
- **No Mock Testing for Storage:** All storage unit and integration tests must run against real SQLite in-memory or temporary database instances.

---

## Pull Request Guidelines

1. Ensure all 40+ tests pass cleanly.
2. Update relevant documentation in `docs/` or `README.md` if behavior changes.
3. Keep PRs focused on a single responsibility.
4. Fill out the [Pull Request Template](.github/pull_request_template.md).
