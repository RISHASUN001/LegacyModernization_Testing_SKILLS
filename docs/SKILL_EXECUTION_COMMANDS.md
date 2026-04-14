# Skill Execution Commands (Option A)

## Run a single skill

```bash
python3 scripts/run_skill.py <skill-name> --input <module-run-input.json> --artifacts-root artifacts --workdir /Users/risha/Documents/Buildathon
```

Example:

```bash
python3 scripts/run_skill.py module-discovery --input run-inputs/module-run-input.Login.test-001.json --artifacts-root artifacts --workdir /Users/risha/Documents/Buildathon
```

## Run the full 7-stage pipeline

```bash
python3 scripts/run_pipeline.py --input <module-run-input.json> --workdir /Users/risha/Documents/Buildathon --verbose
```

## Canonical direct orchestrator command

```bash
python3 skills/legacy-modernization-orchestrator/run.py --input <module-run-input.json> --verbose
```

## Contract notes

- Every skill writes `result.json` under `artifacts/{module}/{runId}/{skill}/`.
- Skills accept canonical args:
  - `--input`
  - `--artifacts-root`
- Backward-compatible aliases remain accepted:
  - `--module`
  - `--run-id`
  - `--output-dir`

