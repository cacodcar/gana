# Type aliases

Annotation refactoring completed on 2026-10-09. Shared numeric aliases live in
`src/gana/types.py`; domain-specific unions
remain beside their consuming classes to preserve existing import boundaries.
`Self` remains at method use sites. Tuple lengths, container element types,
union members, defaults, and executable function bodies are preserved.
Gana's `NumericTuple` deliberately retains its original one-element shape.

## TODOs

- [x] Inventory repeated numeric and long union annotations.
- [x] Introduce and apply named aliases throughout the package's source annotations.
- [x] Verify expanded annotations and executable ASTs against pre-task snapshots.
- [x] Run the configured full quality suite before and after the changes.
- [x] Resolve newly introduced lint and formatting diagnostics.
- [ ] Existing repository quality failures remain: complexity thresholds,
  lint, formatting, static typing, and documentation configuration.
  Release-quality repairs were authorized on 2026-10-22; the historical
  measurements below remain unchanged.

## Runtime introspection repair

On 2026-10-22, aliases that cross the parameter, variable, theta, function,
and constraint import cycle were changed to explicit forward references.
Their union members and container shapes remain unchanged. Sphinx can now
inspect their runtime values without requiring circular imports of classes
that are otherwise imported only under `TYPE_CHECKING`.

## Validation

Ran from the repository's intended `.quality-venv`:

```sh
.quality-venv/bin/python tools/quality.py all
.quality-venv/bin/python tools/quality.py lint
.quality-venv/bin/python tools/quality.py format
.quality-venv/bin/python tools/quality.py raw
.quality-venv/bin/python tools/quality.py maintainability
```

The full suite runs pytest with statement/branch coverage, Radon cyclomatic
complexity, maintainability and raw metrics, Ruff lint/format checks, mypy,
Sphinx, dependency validation and Flake8. Reports preserve commands and statuses:

- Before: `quality/runs/20261009T073902653706Z/manifest.json`.
- After: `quality/runs/20261009T074225100521Z/manifest.json`.
- Final maintainability: `quality/runs/20261009T074553741529Z/manifest.json`.

These are local paths relative to the repository root. The historical reports
are retained locally and are not distributed with the documentation website.

36 tests pass before and after. Dependency checks pass.
Expanded annotations and executable ASTs match exactly across all 26 modified
modules in the two repositories. All modified modules parse with Python 3.12
grammar. Complexity values are unchanged, including existing grades below B.
No algorithms were changed or ported. No new lint diagnostics or formatting
failures remain; pre-existing failures persist.

Gana mypy errors decrease from 1,188 to 1,172, with no increased error-code counts per file.
The documentation build already fails because the Markdown source parser is
not registered. Sphinx-generated source changes were restored to pre-task hashes.
The supplementary tox Python-version matrix and hash-locked historical baseline
reproduction were not run; the current full checks used Python 3.13.7.
No commits, pushes, or manuscript changes were made.

## Metrics

Statement coverage 54.137% → 54.385%;
branch coverage 35.810% is unchanged.
The small statement-coverage increase reflects executed alias declarations,
not additional tests. Some maintainability scores decrease because declarations
and imports add source lines. MI grades are unchanged, including Gana’s
existing grade C modules.
Existing function complexity is preserved rather than expanded into an unrelated
algorithm refactor.

| Module | MI before | MI after | Grade |
| --- | ---: | ---: | --- |
| `src/gana/sets/constraint.py` | 51.40 | 50.82 | A → A |
| `src/gana/sets/variable.py` | 38.96 | 37.83 | A → A |
| `src/gana/sets/birth.py` | 86.07 | 86.00 | A → A |
| `src/gana/sets/theta.py` | 51.14 | 51.02 | A → A |
| `src/gana/sets/parameter.py` | 0.00 | 0.00 | C → C |
| `src/gana/sets/function.py` | 0.00 | 0.00 | C → C |
| `src/gana/block/program.py` | 0.00 | 0.00 | C → C |
