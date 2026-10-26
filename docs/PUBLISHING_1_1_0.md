# Publishing Gana 1.1.0

Release source: merged commit `105ef80d02512ee191018963899a284a3748f07e`.
The Python metadata and `gana.__version__` both identify version `1.1.0`.
The internal Rust crates have their own `0.1.0` version and are not published
to crates.io.

## Build all platforms using GitHub Actions

The `Release 1.1.0 artifacts` workflow in
`.github/workflows/release-artifacts.yml` builds a single source archive from
the merged release commit. Each platform wheel is then built from that archive
with Rust 1.88.0 and Maturin 1.9.6:

| Artifact | Platform |
| --- | --- |
| `release-sdist` | Source archive, including both Rust crates and Cargo.lock |
| `release-wheel-linux-x64` | Linux x86_64, manylinux2014 |
| `release-wheel-windows-x64` | Windows x86_64 |
| `release-wheel-macos-x64` | macOS Intel |
| `release-wheel-macos-arm64` | macOS Apple Silicon |

Wheels use the CPython stable ABI beginning with Python 3.12. The workflow
installs each wheel on Python 3.12 and 3.13, checks its version and native
extension location, and runs existing storage, coordinate, matrix export,
and solver adapter tests outside the source checkout. All dependencies must
install as wheels. These packaging checks supplement the full release CI suite.

The workflow runs when its file is pushed on `release/1.1.0-artifacts`.
After the workflow reaches the default branch, it can also be started using
GitHub Actions > Release 1.1.0 artifacts > Run workflow. It builds the pinned
release source regardless of the branch from which the workflow is started.
It uploads artifacts to GitHub Actions and does not publish to PyPI.

Wait for every build and installed-wheel test to succeed. Download the five
artifacts from that one successful run and extract the four `.whl` files and
one `.tar.gz` into an empty release directory, for example `dist/1.1.0-ready`.
Do not include GitHub's ZIP wrappers or old distributions in the upload.

## Reproduce a macOS build locally

Install Python 3.12 or 3.13, the Xcode Command Line Tools (`xcode-select --install`),
and Rust via rustup. Clone Gana into a separate release checkout:

```bash
git clone https://github.com/cacodcar/gana.git gana-1.1.0-release
cd gana-1.1.0-release
git checkout 105ef80d02512ee191018963899a284a3748f07e
python3.13 -m venv .release-venv
source .release-venv/bin/activate
python -m pip install 'maturin==1.9.6' 'twine==6.2.0'
rustup toolchain install 1.88.0 --profile minimal
export RUSTUP_TOOLCHAIN=1.88.0
python -m maturin sdist --out dist/1.1.0
python -m maturin build --release --locked --out dist/1.1.0
python -m twine check --strict dist/1.1.0/*
```

This builds for the Mac's own architecture. Use the hosted Intel and Apple
Silicon jobs to produce and test both architectures. Installing and testing
the resulting wheel should happen in a fresh environment outside the checkout.
For a source checkout used by the ordinary quality runner, use an editable
install so `src/gana` can find its native extension.

## Validate and upload the collected artifacts

On the Windows release workstation, the isolated release tools are installed
in `.cache/release-venv`. From the Gana repository:

```powershell
$releasePython = '.cache\release-venv\Scripts\python.exe'
& $releasePython -m twine check --strict dist/1.1.0-ready/*
Get-FileHash dist/1.1.0-ready/* -Algorithm SHA256
```

Keep API tokens out of chat, source files, and shell command arguments.
Store a project-scoped PyPI token using the hidden password prompt:

```powershell
& $releasePython -m keyring set https://upload.pypi.org/legacy/ __token__
```

After reviewing the complete artifact set and successful test run, upload:

```powershell
& $releasePython -m twine upload --non-interactive --repository-url https://upload.pypi.org/legacy/ --username __token__ dist/1.1.0-ready/*
```

On macOS, the equivalent commands are `python -m keyring set ...` and
`python -m twine upload ...` from the release environment. The token is scoped
to the Gana project, not a particular version. PyPI does not allow replacing
an already uploaded distribution with different bytes under the same filename.

## Verify publication

Check https://pypi.org/project/gana/1.1.0/#files for the source archive and all
four platform wheels. Compare the PyPI SHA-256 values to the validated files.
In a fresh environment on a supported platform, install from PyPI:

```bash
python -m pip install --only-binary=:all: gana==1.1.0
python -c "import gana, gana._native; print(gana.__version__); print(gana._native.__file__)"
python -m pip check
```

The existing PowerShell `publish` function builds only the current platform
and uploads every file directly under `dist`. For this native release, use
the explicit collected artifact directory above.
