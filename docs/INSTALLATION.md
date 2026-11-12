# ADAPT Installation & Quickstart

## 1. System Requirements
- Python >= 3.9 (Python 3.11 or 3.12 recommended)
- SQLite 3 with FTS5 support (included by default in Python standard library on macOS and Linux)

## 2. Standalone Package Installation
```bash
git clone https://github.com/adapt-memory/adapt.git
cd adapt
pip install -e .
```

To run test suites:
```bash
pip install -e ".[dev]"
pytest tests/
```

## 3. Hermes Agent Integration Installation
ADAPT is delivered as an official Hermes Memory Provider Plugin:

```bash
# 1. Validate plugin compliance using Hermes official validator
hermes plugins validate . --install-deps

# 2. Install the plugin into Hermes profile
hermes plugins install /path/to/adapt
```

## 4. Activation in Hermes Agent
In your `~/.hermes/config.yaml`:
```yaml
memory:
  provider: adapt

adapt:
  storage_dir: ~/.hermes/adapt
  top_k: 5
```

Alternatively, use the interactive wizard:
```bash
hermes memory setup
# Select 'adapt'
```

