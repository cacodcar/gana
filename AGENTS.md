# Working on Gana

## Common MultiRepo policy

This section is shared by Energia, Gana, Vaelchi, and Aayam. Keep its wording
consistent across the four repositories; put project-specific details below.
Explicit user instructions take precedence. This file governs agent behavior;
it does not itself configure GitHub protections.

### Scope and authorization

- Treat requests to investigate or propose as read-only. A request to implement
  or fix authorizes the agreed edits, validation, and the task branch, commits,
  pushes, and pull request needed to present the result, unless the user limits
  that scope. Explain the intended changes and complete authorized work without
  asking for the same permission again.
- Obtain explicit authorization for merging, tagging a release, publishing,
  deploying, deleting or archiving work, changing repository visibility, or
  changing access/protection settings. Existing authorization for the same
  action and scope remains valid. Permission to implement is not permission
  to merge or release.
- Work on a task branch and present a focused PR. Do not push directly to main,
  enable auto-merge, or use an owner/admin bypass without authorization for the
  corresponding action. Keep completed PRs ready for review; use draft status
  only while work is incomplete and explain what remains.
- Preserve user changes, unrelated work, manuscript content, research inputs,
  saved notebook outputs, and historical branches. Do not regenerate research
  results or edit manuscripts unless explicitly included in the task.

### Existing tests require Rahul's approval

- Before modifying, deleting, renaming, or weakening an existing test, explain
  the proposed change and obtain Rahul Kakodkar's explicit approval for it.
  This includes expected results, fixtures, snapshots, tolerances, skips,
  parametrization, shared test helpers, and collection/coverage exclusions.
- General approval to fix implementation does not approve changes to existing
  tests. Approval that explicitly covers the described test changes is enough;
  do not ask twice. Continue independent authorized work while awaiting a decision.
- Add meaningful new regression tests within the approved implementation scope.
  Do not change shared helpers or configuration to evade the existing-test rule,
  or add trivial tests that only mirror implementation to inflate coverage.

### Correctness, compatibility, and documentation

- Mathematical and numerical correctness take priority over metrics. Preserve
  public APIs, indexing/mapping semantics, units, solver defaults, serialization,
  and numerical behavior unless the task explicitly authorizes a change.
  Explain any necessary change outside that scope before implementing it.
- For ports and algorithm changes, compare against the recorded source version
  using identical inputs and assumptions. Report constraints, objectives,
  outputs, exact agreement or justified tolerances, and any unverified scope.
  Do not claim full parity from a reduced example.
- Keep changes cohesive, maintainable, and limited to the task. Document changed
  behavior with useful docstrings, including relevant dunders, and small examples
  where they clarify the API. Preserve original authorship and port provenance.
  AI/model authorship comments are not required; avoid boilerplate annotations.
- Read dependency declarations and verify compatibility across affected main
  repos. Do not silently substitute an unpublished sibling checkout for a
  declared released dependency; disclose and pin deliberate integration setups.

### Validation and evidence

- Use an isolated project environment and the current configured checks.
  Read the repository-specific section, CI workflows, tool configuration, and
  applicable editor/tox tasks before choosing validation commands.
- Run focused regression checks for code changes and the full relevant suites
  for shared modeling, indexing, compilation, solver, or algorithm changes.
  Use the supported interpreter matrix for compatibility and release validation.
  Documentation-only changes need appropriate content/link checks; do not
  invent runtime tests merely to exercise prose.
- Preserve required CI checks and coverage/complexity floors. Do not disable
  hooks, suppress findings, skip failing tests, relax thresholds, or rewrite a
  baseline merely to obtain green results. Any deliberate policy exception
  needs explicit approval and must remain visible in the report.
- Where tracked hooks exist, activate them in local checkouts and inspect their
  results. Do not use --no-verify to conceal a failure. Hosted checks still have
  to pass; local success is not evidence that remote services ran.
- Preserve baseline environments, source hashes, deterministic settings, raw
  evidence, and dated reports. Run hash-locked baseline verification only in
  its matching recorded environment; never apply an old platform lock to an
  unrelated environment or overwrite history to hide a regression.
- Isolate solver outputs, coverage/profiling files, caches, and generated docs
  from user files. Do not overwrite saved notebooks or source docs as a side
  effect of validation.
- Report checks run, results, relevant before/after metrics, existing failures
  versus regressions, and missing dependencies or solver/license limitations.
  Current executable configuration defines checks and floors; historical
  measurements in documentation are not current thresholds.

### Merge and release boundaries

- Before an authorized merge, verify required checks on the current PR head,
  review/thread requirements, and the intended diff. The standard protection
  model separates owner approval from quality: Rahul may bypass the review
  requirement through a PR, but quality checks remain mandatory.
- Before an authorized release, reconcile versions and changelog, verify the
  release commit and supported matrix, build and check distributions, and test
  installed wheels outside the checkout. Follow the repository's release
  workflow rather than improvising a second publication path.
- After publication, verify the PyPI version and artifacts, GitHub release notes
  and assets (including built wheels where applicable), and documentation.
  Report incomplete stages accurately; a merge or tag alone is not a release.
- Do not weaken protections or change visibility to work around a service-plan
  or permission limitation. Report the limitation and retain the PR workflow.

## Gana-specific instructions

- Repository: `cacodcar/gana`; Python package: `gana`. Python source lives
  under `src/gana/`; native code lives under `crates/`.
- Install current development dependencies with
  `python -m pip install -e '.[test,quality,docs]'` in a fresh
  `.quality-venv`. The native extension requires Rust/Cargo and a linker;
  follow the toolchain pins in the current workflows. Leave `GANA_BACKEND`
  unset for ordinary validation.
- Run `.quality-venv/bin/python tools/quality.py all` for Python tests,
  statement/branch coverage, Ruff lint/format, Flake8, Mypy, Radon, Sphinx,
  and dependency consistency. Run
  `.quality-venv/bin/python tools/native_quality.py` when native behavior
  is affected. Use `python -m tox` in that environment for the Python matrix.
- Coverage floors live in `[tool.research-quality]` in `pyproject.toml`;
  native gates live in `tools/native_quality.py`. Do not duplicate numerical
  thresholds in this file. Preserve the documented, narrowly scoped
  mathematical API and test lint exceptions in `ruff.toml` and `tox.ini`.
- Activate hooks with `git config --local core.hooksPath .githooks`.
  Preserve the historical `.venv`, dated evidence, and `tools/baseline.py`
  separately from current native validation. `--baseline` is only for its
  matching recorded environment. See `docs/QUALITY_GATES.md` and
  `docs/REPRODUCIBLE_BASELINE.md`; old Vael/dependency/floor references are
  historical and must not override current package configuration.
- Check downstream Energia behavior when changing expression construction,
  indexing, compilation, solver adapters, or result serialization.
- Releases use `.github/workflows/release-artifacts.yml` followed by
  `.github/workflows/publish.yml`. The publish workflow consumes the tested
  build run for the same main commit. Preserve platform wheels, source archive,
  checksums, and changelog-derived notes. Follow the workflow's exact tag format.
