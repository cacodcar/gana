# Working on Gana

## Authorship annotations

At the user's explicit request on 2026-10-04, Gana code does not require
`Authored by OpenAI` comments. This overrides the standing authorship-comment
requirement for this repository. Keep useful code documentation and preserve
existing original-author and port provenance.

## Approval

Default to read-only investigation. Before changing source code, tests,
documentation, dependencies, or configuration, explain the proposed changes and
affected files and wait for the user's explicit approval. Approval applies only
to the agreed scope. Obtain separate approval before committing, pushing,
publishing, or deploying. Preserve existing user changes.

## Quality checks

For approved code changes, consider all checks in `.vscode/tasks.json`:
cyclomatic complexity, complexity ranks B through F, maintainability index,
raw code metrics, and pytest statement/branch coverage.

- Record relevant before/after metrics for affected code and explain regressions.
- Run appropriate regression tests and the full suite when changes affect shared
  expression, indexing, compilation, or solver behavior.
- Treat mathematical correctness as the primary requirement. Metrics are review
  evidence, not a substitute for correct semantics or meaningful tests.
- Do not refactor unrelated code just to improve aggregate scores or inflate
  coverage with tests that only mirror implementation.
- Distinguish existing failures from newly introduced failures. Report missing
  dependencies and solver/license limitations explicitly.
- Use Gana's dedicated `.venv` for the reference baseline, not an arbitrary
  `python` on PATH. The original exploratory baseline used `kuru/.venv`.
- Use `tools/baseline.py` for reproducible full measurements. Preserve the
  pinned environment, deterministic settings, source hashes, and raw reports.
  See `docs/REPRODUCIBLE_BASELINE.md`; never silently update a baseline to hide
  a regression.
- Solver tests create MPS and solution files. For investigation, run from a
  temporary working directory with the repository on `PYTHONPATH`, and direct
  coverage, Hypothesis, and plotting caches there. Do not overwrite user files.

See `docs/QUALITY_BASELINE.md` for the initial measurements and task usage.

Use `.quality-venv/bin/python tools/quality.py all` for the shared blocking
gates and `--baseline` for hash-locked verification. See `docs/QUALITY_GATES.md`.
The original Gana `.venv` and dated baseline are preserved separately.
