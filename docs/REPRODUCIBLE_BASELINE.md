# Reproducing Gana's quality baseline

This workflow measures the current Gana source with a dedicated environment,
fixed dependencies and random-test seed, and a fresh temporary test directory.
It saves raw reports and the exact measured source. It does not modify the
modeling library, repair tests, update the reference automatically, or push code.

## Supported reference environment

The initial lock targets **CPython 3.13.7 on Intel macOS (x86_64)**, matching the
machine used to establish the baseline. Its 59 packages include the complete
runtime/test/quality dependency closure, with exact versions and SHA-256 wheel
hashes. It is not a universal Linux, Windows, Apple Silicon, or Python 3.12 lock.
Those targets need separately generated and verified locks. Existing GitHub
Python 3.12/3.13 CI remains independent and unchanged.

The full suite requires Gurobi to be able to solve the test models. Solver
failures remain failures; the runner does not silently skip them. License
secrets are never copied into reports. It records the Gurobi/PPOPT package
versions and preserves solver diagnostics in the pytest output.

## Create or recreate the environment

Run these commands from Gana using an installed Python 3.13.7 interpreter.
The `.python-version` file records the version; it does not install Python.
Use a new environment directory if `.venv` already contains unrelated packages.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: --no-deps -r requirements/baseline-macos-x86_64-py313.lock
.venv/bin/python -m pip check
```

`pip` itself is pinned in the lock. `--no-deps` prevents unpinned dependencies
from being added; `pip check` verifies the installed closure. The runner rejects
missing, wrong-version, or additional packages. Gana is exercised directly from
this checkout, rather than installing an editable copy or invoking an unpinned
build backend. Use a separate general development environment if you need more
tools or an installed Gana package.

To preserve wheels for offline recreation, download them with the same lock:

```sh
.venv/bin/python -m pip download --require-hashes --only-binary=:all: --no-deps -r requirements/baseline-macos-x86_64-py313.lock --dest /path/to/wheelhouse
```

Then install into a fresh environment with the original install command plus
`--no-index --find-links=/path/to/wheelhouse`. Do not commit the wheelhouse or
virtual environment.

## Run a baseline

```sh
.venv/bin/python -B tools/baseline.py
```

Or select **Tasks: Run Task -> Gana: Reproducible Baseline** in VS Code. This task
uses Gana's `.venv` explicitly; the older individual tasks still use the selected
Python extension interpreter and remain useful for quick investigation.

Each run gets a new directory under `quality/runs/`, which Git ignores. An
explicit output directory is allowed, but must not already exist:

```sh
.venv/bin/python -B tools/baseline.py --output quality/runs/check-1
```

The runner uses `PYTHONHASHSEED=0`, Hypothesis seed `20260921`, controlled locale,
single-thread numerical-library settings, explicit pytest plugins, and fresh
Hypothesis/plot caches. It disables pytest cache and bytecode writes. All model
and solution exports occur in the temporary working directory. It checks that
measured source files did not change during the run.

The fixed seed is for baseline comparison. Additional unseeded property testing
is still valuable when developing changes; one seed is not exhaustive coverage.

## Reports and exact source identity

Each output directory contains:

- `manifest.json`: commit, branch, dirty status, environment, package versions,
  source/lock digests, command arguments, exit codes, and source-change check.
- `source-hashes.json`: SHA-256 digest of each measured source, test, tool, and
  relevant configuration file.
- `source.patch`: tracked source/test/packaging differences from the recorded
  commit, including the pre-existing `parameter.py` change.
- `source.tar.gz`: the measured `src`, `tests`, and Python tooling plus packaging
  and lock inputs. This also preserves new files not yet committed.
- `complexity.json`, `maintainability.json`, `raw.json`: Radon reports using
  repository-relative paths, plus command stdout/stderr logs.
- `coverage.json`, `.coverage`, `pytest.xml`, and pytest stdout/stderr.
- `summary.json`: comparable metrics and test counts, excluding timing and
  machine-specific paths.

Reports and archives are local artifacts; they are not published automatically.
The archive is a source snapshot, not a Git repository. To replay it, use a
separate checkout at the manifest's commit and overlay the archived files there.
Never extract an old snapshot over a working tree containing valuable changes.
Recreate the environment with the archived lock before measuring it.

## Verify a clean rebuild

Create a second fresh environment, install the same lock, run `pip check`, and
use its Python to invoke the runner against this same checkout:

```sh
/path/to/fresh-env/bin/python -B tools/baseline.py --output quality/runs/check-2 --compare quality/runs/check-1
```

The comparison checks source hashes, Python/OS/architecture, packages, controlled
settings, and the measured summary. Different interpreter locations, timestamps,
and test durations are deliberately excluded. A difference exits nonzero and
is recorded in `comparison.json`; it never overwrites the previous result.
Floating-point solver outputs and timing are retained as diagnostics, but are
not required to be byte-for-byte identical.

`--compare` tests exact replay. After an intentional code change, source identity
should differ: compare the two `summary.json` reports during review instead of
using exact-replay equality as a universal change gate. Metrics are evidence,
not automatic correctness or quality thresholds.

## Keep a reviewed reference

The initial verified reference is stored in `quality/baselines/2026-09-21/`.
It was reproduced in two independently installed environments on the same
Intel Mac: both passed all 14 tests with identical source, environment, and
metric comparisons. Statement coverage is 53.4%, branch coverage is 35.2%, and
average library complexity is 4.47 (A). See the reference directory's `README.md`
and `rebuild-comparison.json` for the recorded validation and its limits.
Keep this directory immutable. Record new approved references in new dated
directories and explain changes in test outcomes, statement/branch coverage,
complexity, maintainability, and raw size.

The original exploratory results remain in `QUALITY_BASELINE.md`. A fixed seed
can exercise different branches than that original unseeded run, so the
reproducible reference may have different coverage without a library change.

## Branch protection

Gana's `main-owner-approval` GitHub ruleset restricts updates to the repository
administrator. In this personal repository, that is the owner, `cacodcar`.
The owner can bypass and push directly; collaborators propose pull requests
that the owner must merge. Owner merging is the explicit authorization step;
an approval from someone else does not permit them to update `main`.

Classic protection also requires the existing `build (3.12)`, `build (3.13)`,
`test (3.12)`, and `test (3.13)` checks, up-to-date branches, and resolved review
conversations for non-bypass merges. Force pushes and deletion are disabled.
Administrator enforcement is off so the owner retains the requested bypass.
If the repository is transferred to an organization, reassess the administrator
bypass because it may then cover people other than the current owner.

These settings do not authorize an assistant to commit or push on the owner's
behalf. The approval rules in `AGENTS.md` still apply.
