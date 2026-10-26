# Verified reference baseline — 2026-09-21

Two independently installed environments produced identical source hashes,
environment metadata, and measured summaries. Both full-suite runs passed.
See `rebuild-comparison.json` and `rebuild-manifest.json` for verification.

| Measurement | Result |
| --- | --- |
| Gana tests | 14 passed in each environment; no failures, errors, or skips |
| Statement coverage | 1,871 / 3,507 = 53.4% |
| Branch coverage | 585 / 1,662 = 35.2% |
| Combined coverage | 47.5% |
| Complexity | 355 blocks; average 4.47 (A) |
| Complexity distribution | A: 277, B: 43, C: 20, D: 10, E: 4, F: 1 |
| Highest complexity | `F.generate_matrices`: 50 (F) |
| Lowest maintainability | `function.py`, `parameter.py`, `program.py`: 0.0 (C) |
| Source lines | 5,192 across 32 Python source files |

These library measurements match the earlier exploratory baseline. No Gana
library or existing test code was changed. The existing local `parameter.py`
modification is captured in `source.patch` and the source archive; the recorded
Git commit alone is not the exact measured source.

The added baseline tooling was checked separately:

- Three runner safety/comparison tests passed (`python -B -m unittest tools.test_baseline`).
- Fatal-error Flake8 checks passed for `tools`.
- Tooling complexity averages 3.93 (A) over 15 blocks. The largest block is the
  orchestration function `main`, at 14 (C).
- Tooling maintainability is 33.44 (A) for `baseline.py` and 44.32 (A) for
  `test_baseline.py`.
- Added tooling totals 287 physical lines and 246 source lines. It is reported
  separately rather than diluting the library's historical metrics.
- All 45 archived input files were verified against `source-hashes.json`.

Use `summary.json` for metrics, `coverage.json` for detailed coverage,
`manifest.json` for provenance, and command logs for diagnostics. The reference
retains coverage JSON rather than the machine-specific `.coverage` database.
Timing and absolute paths in raw reports are observations, not equality targets.

The 59-package lock is verified for Python 3.13.7 on Intel macOS. The two runs
used macOS 12.7.6 on the same machine, with different newly installed virtual
environments. This verifies clean-environment reproduction, not cross-platform
or independent-hardware reproduction. Dependencies were installed offline from
downloaded wheels with hash checking enabled, and `pip check` passed in both.

Existing test limitations remain: JSON/pickle test names collide, the JSON
import test depends on a file created by an earlier test, and semantic edge
cases are not exhaustively covered. Fixed-seed reproduction does not repair or
hide these issues.

See [the reproduction guide](../../../docs/REPRODUCIBLE_BASELINE.md) for setup,
commands, exact-source replay, and how to compare future approved changes.
Keep this reference immutable; save subsequent approved baselines separately.
