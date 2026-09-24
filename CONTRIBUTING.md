# Contributing

Contributions are welcome. Use Python 3.11 or newer and install the development dependencies:

```console
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pre-commit install
```

Before submitting a change, run `ruff check .`, `ruff format --check .`, `mypy --strict src`,
and `pytest`. Security changes should begin with a failing adversarial test and keep database
read-only controls independent from validation. Use focused conventional commits and explain
design tradeoffs in non-trivial commit bodies.

Do not report security vulnerabilities in a public issue. Contact the maintainers privately
with reproduction steps, affected versions, and any known mitigations.

