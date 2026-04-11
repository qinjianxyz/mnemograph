# Contributing

## Development setup

```bash
cd projects/oss/mnemograph
pip install -e ".[dev]"
```

## Run tests

```bash
pytest tests -v
```

## Run the demo

```bash
python scripts/demo_hobbes.py \
  --base-dir demo-output \
  --company-url https://vercel.com \
  --base-url http://localhost:11434/v1 \
  --model qwen3.5:latest \
  --max-pages 1
```

## Add a golden eval case

1. Add a YAML scenario under `evals/golden/`.
2. Run `mnemograph-eval evals/golden/ --base-dir /tmp/mnemograph-eval`.
3. Update expectations only when the new behavior is intentional.

## PR expectations

- Tests must pass before review.
- New features need tests.
- Keep canon changes deterministic and provenance-preserving.
- Update docs when behavior or interfaces change.
