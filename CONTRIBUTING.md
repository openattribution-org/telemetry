# Contributing to OpenAttribution Telemetry

Thank you for your interest in contributing. OpenAttribution is an open-source schema and SDK for AI content attribution, licensed under Apache 2.0.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/openattribution-org/telemetry.git
cd telemetry

# Install with dev dependencies
pip install -e ".[dev]"

# Or with uv
uv sync
```

## Running Tests

```bash
pytest                       # All tests
pytest tests/test_client.py  # Specific file
pytest -v                    # Verbose output
```

Tests use `pytest-asyncio` for async client tests.

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check --fix .
ruff format .
```

Key conventions:
- **Type hints everywhere**
- **Pydantic v2 patterns** (use `model_validator`, not `root_validator`)
- **Async by default** for I/O operations
- **British English** in documentation

## What to Contribute

- **Bug fixes** and test improvements
- **Implementations in other languages** (the JSON Schema in `schema.json` is the cross-language reference)
- **UCP integration feedback** (see `ucp/` for specs)
- **Use cases** we haven't considered

## Schema Changes

If your change affects the data model:

1. Update `src/openattribution/telemetry/schema.py` (Pydantic models)
2. Update `SPECIFICATION.md` to match
3. Regenerate `schema.json` from the Pydantic models
4. Update UCP schemas in `ucp/` if applicable
5. Add or update tests

## Submitting Changes

1. Fork the repository and create a branch from `main`
2. Make your changes with tests
3. Ensure `pytest` and `ruff check` pass
4. Open a pull request with a clear description of the change

## Licence

By contributing, you agree that your contributions will be licensed under the Apache 2.0 licence.
