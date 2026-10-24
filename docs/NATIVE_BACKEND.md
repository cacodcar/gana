# Native owner foundation

This development backend stores registered P values and V/T membership in Rust. Python
remains the default (`GANA_BACKEND=python`). Select `GANA_BACKEND=rust-parameters`
**before importing Gana** to exercise the native path. A missing extension is an
error; native tests and benchmarks never silently substitute Python storage.

The historical flag now enables all three owner types. This is an incremental
integration toward the 1.1.0 backend. Supported affine batches and
reductions and sparse compilation now run in Rust. Coordinate normalization
still uses Python. Public
`sigma`, `inf`, and `sup` calls are unchanged.

## Layout and ownership

```text
crates/gana-core       safe Rust, no Python dependency
  Affine              immutable sparse row batches and bulk arithmetic/reduction
  Membership          optional member-to-row index for a queried constraint batch
  Owner<T>            stable root; replaces its current Payload<T>
  Payload<T>          shared lock + immutable vector version; atomic batch writes
  Snapshot<T>         retained vector version + fixed Selector
  Selector            spans O(1); Cartesian axes O(rank); irregular IDs O(k)
  Coordinates<T>      append-only coordinates and records; fixed shared views
crates/gana-python     PyO3 numeric and symbolic record bindings
src/gana/
  __init__.py              public modeling API
  types.py                 public type aliases
  _native.pyi / _native.*  compiled PyO3 module and its typing interface
  backends/native/
    algebra.py             affine dispatch and captured operands
    constraints.py         registration and sparse compilation
    constraint_rows.py     individual constraint rows and stable identities
    rows.py                individual expression rows and guarded edits
    membership.py          selective variable/constraint bookkeeping
    registry.py            compact constraint replacement and numbering
    render.py              formula display without scalar row construction
    export.py              sparse solver and MPS snapshots
    results.py             result loading and solution history
    theta.py               parametric binding and captured intervals
  indexing/
    coordinates.py         Python axis interning and native coordinate IDs
    ordered.py             ordered axis/member/token collections
    selection.py           skipped, missing and repeated-coordinate containers
    staging.py             constructor Cartesian maps
  storage/
    parameters.py          numeric payloads and sequence/mapping facades
    symbols.py             V/T ownership and program registry spans
    members.py             temporary scalar wrappers and persistent state
  sets/                    public I/P/V/T/F/C/O classes
  block/                   programs and solutions
  operators/               sigma, inf and sup
  utils/                   display, timing and drawing helpers
  shapes/, value/          existing geometry and scalar-value modules
```

The root-level `_native` module remains the compiled extension boundary used by
Maturin. The implementation packages have lightweight initializers so moving
modules does not eagerly load backend adapters or introduce new import cycles.
Public imports such as `from gana import Prg, I, P, V, T, sigma, inf, sup` and the
existing `gana.sets` class paths are unchanged. The internal development modules
formerly named `gana.native_*`, `gana.coordinates`, and `gana.symbol_*` now live
in the subpackages shown above; internal numeric storage is
`gana.storage.parameters`. Persisted objects that name those old internal module
paths require migration; this layout change does not provide a legacy unpickler.

No addresses into growable vectors escape. Snapshots keep data alive through
`Arc`; writes copy the vector only when a snapshot shares it. Each payload has a
local version counter. Python inputs are converted before Rust acquires a lock.
The core forbids unsafe Rust. Dependency unsafe code is outside that guarantee.
Bindings currently retain the GIL; free-threaded Python is not a validated target.

The Python facades share one authoritative numeric payload. `._` positional
writes and `.map.update()` validate entire batches before changing either view.
Length-changing edits, deletion, raw reordering and container replacement raise
an actionable error. Supported program assignment still handles growth and
replacement; old retained facades remain detached and editable. Partial P
selections keep their captured values and detach on their first local write.
`list`, `dict`, `.copy()`, and NumPy conversions explicitly materialize copies.
Direct `._` and `.map` display uses list/dictionary formatting in both Python
and notebooks. Native previews show at most ten entries, followed by `...` when
entries remain. Previewing does not export the full numeric buffer or create
all symbolic children; only the displayed symbolic members may gain metadata.
The preview follows the view's order and current values without caching its text.
Unregistered P declarations retain the permissive staging containers needed for
legacy validation. Program tokens remain Python objects with no owning backref.

P/V/T share native coordinate lookup and selector machinery. Python retains one
intern table of axis objects per owner, rather than a tuple dictionary per
selection. Full V copies freeze membership in O(1). Public selections freeze and
encode each requested axis, then cross the native boundary once. Rectangular
owners are recognized at registration; their selections retain separate axis
selectors instead of expanding Cartesian coordinates. Regular strides, reversal
and compatible nested products retain O(rank) native selector storage. Irregular
axis orders retain O(sum of axis lengths) IDs. Python axis normalization still
takes O(sum of axis lengths), and constructing an `I` slice retains its existing
Python index list. This does **not** make all public slicing constant-time.

Unions of products and grown domains use native coordinate lookup, preserving
registration order and fixed view membership. This fallback still enumerates
the requested product in Rust, with O(k) temporary IDs; irregular selections
retain an O(k) inverse lookup to avoid quadratic nested mapping access. Parameter
snapshots compose the same selectors against their captured value version, and
detach on local writes without changing their owner or earlier snapshots.

Skipped, missing and repeated coordinates use lazy compatibility containers.
V retains missing tuple keys with None values; P collapses skipped keys to None
and raises for other missing keys; T omits skipped keys from its map and raises
for other missing keys. Their lists keep all requested slots. Construction and
membership checks do not instantiate scalar symbols. Explicit reads create only
the requested members; a container edit materializes that legacy list or dict,
preserving their historically independent mutation semantics. These exceptional
containers use the compatibility algebra path when consumed by operations.

A tiny snapshot may retain a large underlying version. Native
`reserved_bytes` counts vector capacity only, excluding locks, selectors and
allocator overhead. Do not treat tracemalloc alone as native memory usage.

V/T registration and supported growth create native records without scalar
Python children. Ordinary T interval tuples now validate and encode in batches
through Rust.
Exact Python integer ordering and integer endpoint text are preserved; NaN and
overflow errors retain their validation order. Tuple/numeric subclasses and
existing T members use the Python fallback in row order. T subclasses retain
their validation overrides. Validation runs again after declaration edits;
neither validation results nor encoded batches are cached across operations.
All conversion finishes before native coordinate mutation or locking.
Built-in endpoints now enter a short-lived immutable native buffer directly,
without Python endpoint/row encoding tuples. Coordinate records share those
native intervals until the temporary buffer is released; later bound writes
replace records and cannot change another owner's shared interval. Legacy
encoded inputs remain accepted for serialization and existing native callers.
Within an exact staging list, consecutive occurrences of the same built-in
interval tuple share one native allocation. Reuse keeps only the previous
tuple alive during preparation and leaves no Python references in the result.
It borrows the last stored native interval and increments its reference count
only when another row actually shares it.
Distinct tuples retain their own encodings, including endpoint types and
signed zero. Custom conversions clear reuse and run for every row; arbitrary
iterators keep per-row conversion because their steps can change conversion
settings. The sharing state disappears at the end of each preparation call.

Program registries retain owner spans in global column order,
including interleaved growth. Root facades remain live; selections have fixed
membership. A weak cache reuses every live scalar wrapper. IDs from `id()` are
only comparable while those wrappers are alive; stable model IDs remain `.n`
and owner-local `.pos`. Mutable Python metadata (including solution dictionaries)
is allocated on first access and retained separately so wrapper collection does
not discard it. Explicit full materialization therefore still has a real cost.

Theta endpoints use integer decimal text or floating-point records, preserving
arbitrary integer precision. Endpoint writes validate the whole interval before
commit. Bounds transformations can read native intervals without filling scalar
wrappers. Raw symbolic container replacement, reordering and structural edits
are rejected; mutable program assignment remains the growth interface.

## Bulk affine operations

Registered native variables/selections and numerical parameters support batch
addition, subtraction, scaling and `sigma` reductions. Expressions capture
parameter values and fixed variable membership, so later writes or growth do
not change previously constructed rows. Consecutive-repeat broadcasting and
duplicate column accumulation preserve the Python compiler's order. Legacy
scalar expressions and unsupported numeric cases use the existing Python path.

Native expressions remain instances of `F`. Named expression registration and
scalar objectives retain native rows without filling variable or expression
children. Integer indexing constructs only the requested scalar expression
and its scalar operands. Slices return ordinary lists of the requested rows;
iteration constructs rows as they are consumed. Selections share the source's
row objects, including repeated coordinates and registration numbers. Each
expression retains the rows already requested; untouched siblings remain in
native storage. A reduction row constructs its own terms, whose count may be
large even when the reduction has only one output row.

Projected rows remain instances of `F`. Their mutable list and dictionary
fields use subclasses that promote the graph to its ordinary compatibility
representation before a mutation. This preserves existing dependent snapshots,
escaped row/container identities, and shared selection edits. Attribute writes,
explicit full-container access (`._`, `.map`, collection matrices), and
serialization of exposed rows also use compatibility replay. This change
optimizes reads; the first mutable edit can still allocate the complete graph.
Saved solution values are restored for the requested row in the original
arithmetic order, using captured solve-time values.
Plain text, ordinary notebook display, LaTeX and long names use transient
formula metadata instead of reconstructing every scalar expression row. They
reuse the existing normalization and formatters. Already exposed Python rows
remain authoritative. Display retains no persistent expression or text cache;
repeated display rebuilds the small metadata tree. Cost depends on the formula
and requested output, and coefficient distribution can still process numeric
arrays. Explicit descriptive display continues to visit every requested row.
Deferred display uses the same scalar objective selection and font nesting as
the Python backend. Objective formatting expands captured numeric coefficients
where Python does, preserves signs and row IDs, and does not relabel an expression
reused elsewhere. Membership snapshots do not add a display wrapper of their own.
Replacing named expressions also uses that compatibility path. There is no
program-wide expression cache. Objective membership is registered per owner;
only already-materialized member metadata is updated eagerly.

Rust retains integer coefficient arithmetic up to checked i128 limits; larger
values or results fall back to Python. This does not change `P`'s existing float
input conversion. Reductions of nonzero floating offsets retain Python's
compensated `sum` through a numeric-only fallback; sparse term reduction stays
native. Native column accumulation never silently wraps integer overflow.
Serialization stores detached numeric rows and shared Python owner references,
not native pointers. Unsupported grouped selections retain compatibility
fallbacks.

## Constraint registration and sparse compilation

Supported native affine comparisons retain one constraint batch through program
registration. `p.A` and `p.B` compile from native rows without creating scalar
variables, expressions or constraints. `p.A_sparse` returns a detached SciPy CSR
matrix with float64 coefficients; both backends avoid a dense intermediary for
this property. Row order remains inequalities, equalities, then nonnegativity
constraints. Repeated columns accumulate in occurrence order; explicit zeros
may remain stored. Public `P` input conversion remains floating point.

Registration keeps owner-level pending links. Integer constraint reads, slices
and iteration project only requested rows and their scalar expressions. Row
identities, categories, export numbers and registered theta columns remain live;
read-only exposure keeps native compilation available. Slice and iteration
share normalization metadata without retaining a global cache. Repeated scalar
reads also reuse a per-expression projection plan once more than one row has
been exposed. Untouched expressions and first-row reads retain no plan. The
plan is released when all rows have been projected or mutable compatibility
replay takes over, including when an enclosing expression finishes an operand.
Partially consumed expressions can retain normalization metadata until then;
allocation benchmarks report that tradeoff separately from timing.
Repeated integer reads of already exposed rows return their existing objects
without setting up a projection context. Existing protected row containers also
reuse their guards; shared theta lists continue to resolve through their owner.
Iteration reuses broadcast alignment metadata. Scalar variable construction
reuses validated defaults while giving each member its own mutable metadata.
Scalar expression construction also prepares invariant metadata once per
collection, including during first-write replay. Each exposed row still owns
independent mutable containers. Already aligned variables retain their scalar
identity and snapshot flag without repeating coordinate selection; overridden
selection methods keep their existing dispatch.

A variable's `cons_by` projects only rows containing that member. The first
lookup builds an optional Rust index for each affected constraint batch, mapping
owner/member IDs to ordered row positions. Building this index visits stored
terms and uses additional native memory; later lookups reuse it. Repeated terms
within a row generate one membership, including explicit zero coefficients.
A registered row's `cons_by_pos` resolves memberships for that row's variables.
Previously returned lists keep their identity and observe later registrations.
These reads retain native compilation. There is no program-wide index cache.

An exposed membership list is already complete for its member. Local list
edits preserve that list's identity without expanding unrelated rows. Later
registration updates it, and full replay preserves the edit rather than
reinstating removed links. These edits retain native compilation. Replacing
the list still completes compatibility bookkeeping. A resolved registered row's
position dictionary also supports local edits: later replay preserves the same
dictionary and does not recreate its completed links. Explicit copying finishes
the graph and memoizes the copied dictionary before traversing its variable keys.
Read-and-edit benchmarks include both the lookup and the edit.
Constraint edits and changes to projected function fields complete compatibility
replay and theta binding before applying the mutation. Escaped coefficient
arrays and constraint rows retain identity even when operand replay promotes
their owner during projection. Serialization completes exposed memberships
before copying constraint or owner states, including queries with no matches.
Derived Rust membership indexes are omitted from serialized state. Replacement
and explicit full-container access still use compatibility rows; reducing these
remaining replay costs is subsequent work.

Native sparse buffers have checked column IDs and checked integer arithmetic.
Overflow requests the Python compatibility compiler. Their capacity accounting
excludes allocator overhead, Python wrappers and other model storage; it is not
a complete native heap measurement. Dense `p.A` still needs quadratic memory
for a square model, even when its construction is compiled in Rust.

## Solver adapters and solution histories

Untouched native affine models export MPS directly from sparse coefficients and
owner metadata. Gurobi construction uses its bulk matrix API and retains the
existing `.mps` file side effect. Row names, integer-last column ordering,
binary/free bounds, objective offsets and omission of unused columns follow
the compatibility exporter. Redundant nonnegativity rows remain omitted while
their columns retain bound/objective anchors. Each operation creates a transient
snapshot; no global expression or solver snapshot cache is retained.

Native result loading validates column names or legacy positional order before
storing values. One immutable history vector is shared across owners. Existing
scalar `X` dictionaries update in place; unseen members obtain their history
when accessed. Solution output records are created without constructing symbolic
members. Constraint expression histories replay the original arithmetic tree
against captured solve-time values when requested, preserving arithmetic order
and subsequent user edits to variable histories. Explicit scalar access, mixed
theta expressions, unsupported result value types and modified compatibility
rows retain their established paths. The ppopt adapter remains on that path.

Serialization stores values and coordinates, rebuilding native handles without
serializing locks or addresses. It does not preserve the optimization of sharing
an immutable vector between independently serialized snapshots.
Symbolic selections, captured expression members and live scalar identities
share their reconstructed owner after whole-program serialization.

## Build and check

Use Rust/Cargo **1.88.0**, the committed Cargo.lock and pinned native tools.
Do not install build tools into the preserved Python reference environment.

```sh
python3 -m venv .native-venv
.native-venv/bin/python -m pip install -r requirements/native.txt
export CARGO_HOME="$PWD/.cache/cargo"
cargo fetch --locked
.native-venv/bin/maturin build --release --locked --offline --out .cache/wheels
```

Install the wheel into an isolated environment with Gana's dependencies. For
source development, `maturin develop` builds the extension into the source tree;
run it only from a disposable development environment. Existing reference
environments must not be modified.

```sh
# Compiler-matched LLVM tools are needed for the separate native coverage report.
rustup component add llvm-tools-preview --toolchain 1.88.0
python tools/native_quality.py --output quality/reports/native
GANA_BACKEND=rust-parameters python tools/quality.py tests \
  --output quality/reports/native-python
GANA_BACKEND=python python tools/quality.py tests \
  --output quality/reports/python
```

`NATIVE_LLVM_BIN` can point to an isolated compiler-matched LLVM tools directory.
Each explicit output directory must be new; omitting `--output` chooses a fresh
timestamped directory, including from the VS Code task. The native gate runs fmt, core tests, Clippy
with warnings as errors, and pinned Lizard with a per-function CCN ceiling of 10.
Core LLVM line/region coverage is separate from Python statement/branch coverage;
it currently includes the core's inline unit-test module. Binding code receives
Python integration tests, but binding-region coverage is still pending. Miri,
sanitizers, Linux/Windows wheels and Python 3.12 execution remain release checks.

Pytest always records function profiles, backend selection and extension hashes.
Hypothesis's lazy constant-pool scan is initialized after collection and recorded
separately in `hypothesis-startup.prof` and `hypothesis-startup.json`. This uses
the detected internal hook in the pinned Hypothesis 6.142.3; availability is
recorded explicitly. Strategies, sample counts, assertions and health checks
remain unchanged. Parameter property tests no longer execute during import;
pytest runs them with its configured seed and profiler.
Use separate, uninstrumented workers for speed measurements. CI retains failed
test and native gate artifacts, rather than treating a missing tool as a pass.

References: [PyO3 thread safety](https://pyo3.rs/v0.27.2/class/thread-safety.html),
[Maturin mixed projects](https://www.maturin.rs/project_layout.html),
[Rust coverage](https://doc.rust-lang.org/rustc/instrument-coverage.html),
[Lizard's Rust support and CCN](https://github.com/terryyin/lizard).
