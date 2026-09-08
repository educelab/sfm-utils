# PySfMUtils Maintenance Roadmap

Planning document for the 2026 maintenance pass. Written 2026-09-08, against
`develop` at 99b61e5 (last functional commit 2021-07-13).

## Baseline: what is actually broken

Verified locally before planning, so the phases below are grounded in fact rather
than assumption:

| Check | Result |
| --- | --- |
| `python -m unittest -v test.sfm_utils_tests` on Python 3.14.7 / numpy 2.5.3 | **5 tests, all pass** |
| `python -m build` from repo root | **sdist + wheel build cleanly**; wheel contains only `sfm_utils/`, `test` correctly excluded |
| Git remote | Already `git@github.com:educelab/sfm-utils.git` |

The conclusion that shapes this plan: **no code is broken by age.** The library
runs unmodified on a Python four minor versions past its declared ceiling, and
against a numpy major it predates. This is modernization of packaging, CI, and
test coverage — not a rescue. Every phase can therefore be verified against a
green baseline, and any red is a regression we introduced.

There are, however, two *latent* defects that predate this pass and are unrelated
to Python version drift. Both were found while planning, both are now owned by a
phase below, and neither is currently caught by any test:

1. **`scene.add_intrinsic(Intrinsic())` raises `TypeError` on the second call.**
   Owned by Phase 5.
2. **Both golden fixtures use an identity rotation, which makes three distinct
   behaviours invisible to the test suite.** Owned by Phase 4b.

Two smaller notes:

- `.gitlab-ci.yml` is **dead config**. The repo lives on GitHub, so nothing has
  run this pipeline in years. There is currently no CI of any kind.
- The `deploy:pypi` job runs on `python:3.6` and uses `twine upload` with ambient
  credentials. Both go away in Phase 6.

## Decisions locked

| Decision | Choice | Consequence |
| --- | --- | --- |
| Python floor | **3.11+**, matrix 3.11–3.14 | Enables builtin generics and `X \| Y` unions; drops `typing.List/Tuple/Union` (Phase 3) |
| Version source | **Static in `pyproject.toml`**, bumped manually | No new build deps; requires a release-checklist step (see Risks) |
| GitLab | **Retired fully** | Delete `.gitlab-ci.yml`, repoint all URLs at GitHub |
| numpy floor | `>=1.26` declared. **Measured in CI:** 3.11 resolves numpy 2.4.6; 3.12–3.14 resolve 2.5.3 | Confirms numpy 2.5 requires Python >=3.12. Since every leg lands on numpy 2.4+, Phase 2 could raise the floor to `>=2.0` if dropping numpy 1.x is acceptable |
| `Intrinsic.__eq__` | **Keep comparing derived properties**, made None-safe | Preserves "group by effective calibration" intent while removing the crash (Phase 5) |
| `Intrinsic.__hash__` | **Deliberately `None`** — declared explicitly, not incidental | Field-based equality over mutable state cannot have a stable hash; locks in the O(n) dedup scan (Phase 5) |
| Golden fixtures | **Existing two frozen; add new ones with a non-identity rotation** | Never regenerate `openmvg_sfm.json` / `alicevision_sfm.json` (Phase 4b) |

## Phase order and why

Each phase is verified by something that already exists when it starts:

```
Phase 1  CI on unchanged code         <- builds the safety net first
   |
Phase 2  Packaging + Python floor     <- verified by Phase 1's matrix
   |
   +-- Phase 3  Typing modernization  <- verified by golden-file tests
   |
Phase 4  Test expansion               <- needs the 3.11 floor settled
   |
Phase 5  Intrinsic eq/hash contract   <- behaviour change; needs P4 tests to protect it
   |
Phase 6  Tag-driven PyPI release      <- needs correct metadata (P2) + the P5 fix shipped
   |
Phase 7  Docs and hygiene             <- describes the end state, so it goes last
```

Phase 3 is independent of Phase 4 and the two can run in parallel on separate
branches. Everything else is a hard dependency chain. Phase 5 deliberately sits
*after* Phase 4 (tests first, then the behaviour change) and *before* Phase 6, so
the fix ships in the same release as the modernization.

---

## Phase 1 — GitHub Actions CI on the current code

**Status: complete** — PR #2, all four legs green.

**Goal:** get a working safety net *before* changing anything the tests protect.

- Add `.github/workflows/test.yml`: `ubuntu-latest`, matrix over Python
  3.11 / 3.12 / 3.13 / 3.14, running `python -m unittest -v test.sfm_utils_tests`.
- Install with `python -m pip install -e .`, **not** `-r requirements.txt`, so CI
  exercises the real dependency declaration. This is what lets Phase 2 land
  without touching the workflow.
- Trigger on `push` to `develop` and on `pull_request`.
- Delete `.gitlab-ci.yml` (dead config, per Baseline).

**Acceptance:** all four matrix legs green on a PR into `develop`, with the
package installed from its own metadata.

**Note:** the matrix is deliberately 3.11+ even though the package still declares
`>=3.6` at this point. Phase 1 establishes the *target* matrix; Phase 2 makes the
metadata honest about it.

## Phase 2 — Packaging modernization and Python floor

**Goal:** one declarative `pyproject.toml`, metadata that matches reality.

- Migrate `setup.cfg` `[metadata]` + `[options]` into `pyproject.toml`
  `[project]`. Delete `setup.cfg`.
- `requires-python = ">=3.11"`; classifiers for 3.11–3.14.
- Adopt PEP 639 licensing: `license = "GPL-3.0-or-later"` (SPDX expression) plus
  `license-files = ["LICENSE"]`, and **drop** the
  `License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)`
  classifier, which is deprecated in favour of the expression. Requires bumping
  `build-system.requires` to `setuptools>=77`.
- `dependencies = ["numpy>=1.26"]`. Verify the floor actually resolves on every
  matrix leg — the 3.11 leg will pick a different numpy major than the 3.14 leg.
- Explicit discovery: `[tool.setuptools] packages = ["sfm_utils"]`, preserving the
  current behaviour of shipping only `sfm_utils` and excluding `test`.
- `[project.urls]` pointing at GitHub (Homepage, Repository, Issues).
- Delete `requirements.txt` — the dependency is declared in one place now.

**Acceptance:** `python -m build` succeeds; `twine check dist/*` passes; the wheel
contains exactly the same five modules as the 1.2.0 baseline wheel and no `test`
package; matrix still green.

## Phase 3 — Typing and syntax modernization

**Goal:** spend the 3.11 floor we just bought. Behaviour-neutral by construction.

- `List[float]` -> `list[float]`, `Tuple[float, float]` -> `tuple[float, float]`,
  `Union[np.ndarray, None]` -> `np.ndarray | None`. Drop the `typing` imports.
- `Union[str, bytes, PathLike]` -> `str | bytes | PathLike` in the several
  path-accepting setters and in `export_scene` / `openmvg_load_camdb`.

**Acceptance:** the golden-file tests pass unchanged. This phase must not alter a
single byte of exported JSON — that is what makes it safe, and why the existing
`TestIO` fixtures are the right check.

**Care:** two things not to touch while in here.

- The double-underscore module-level constants (`__OPENMVG_DEFAULT_COB`, the
  `*_NAME_MAP` dicts). Their names are load-bearing: the leading double
  underscore is what excludes them from the `from ... import *` re-export in
  `__init__.py`.
- `Intrinsic.__eq__` / `__hash__`. It is tempting to "fix" the missing `__hash__`
  while editing these classes. Leave it for Phase 5, which changes behaviour and
  needs Phase 4's tests in place first.

## Phase 4 — Test expansion

**Goal:** cover the public API. Today's five tests cover intrinsic properties and
a single-view golden-file export; large parts of the public surface have **zero**
coverage.

Confirmed gaps (grepped against `test/sfm_utils_tests.py`):

| Untested surface | Why it matters |
| --- | --- |
| `export_scene` | **The documented public entry point is never called by any test.** Only the lower-level `scene_to_*` converters are exercised |
| `cob_matrix` argument | No test passes one. The OpenMVG *default* is implicitly locked by the fixture, but nothing else is (see 4a) |
| `openmvg_load_camdb` | Zero references. Regex parsing, quoting, and error paths all unverified |
| `group_models` dedup | Zero references. The documented `view.intrinsic = scene.add_intrinsic(...)` contract rests on this |
| `Format` dispatch | Zero references, including the `ValueError` branch |
| `camera_make_model` | Zero references |
| `Intrinsic.__eq__` edge cases | Zero references. Hides the Phase 5 defect |

Batches, in descending value order:

### 4a — Public entry point and change-of-basis

`export_scene` writing a real file and round-tripping through `json.load`;
`Format` dispatch plus the `ValueError` on an unknown format; and the asymmetry
CLAUDE.md warns about — `export_scene(cob_matrix=None)` substitutes
`diag(-1, 1, -1)` for OpenMVG, a 3x3 identity disables it, and
`scene_to_alicevision(cob_matrix=None)` means *no* change of basis.

Be precise about what is already covered: the OpenMVG fixture's extrinsic
rotation is `[[-1,0,0],[0,1,0],[0,0,-1]]`, so the default COB *is* implicitly
applied and locked today. What is unverified is `export_scene`'s `None`
substitution, the identity-disables path, and custom matrices.

### 4b — Non-identity rotation fixtures (owns latent defect #2)

Both existing fixtures use the default `Pose`, whose rotation is `eye(3)`.
Verified consequence: **three separate behaviours are invisible to the suite.**

| Hidden behaviour | Why identity hides it | Test that exposes it |
| --- | --- | --- |
| AliceVision column-major ravel (`np.ravel(rot, order='F')`) | For the identity matrix, C-order and F-order ravel are byte-identical | Asymmetric rotation: F-order gives `[0,1,0,-1,0,0,0,0,1]`, C-order gives `[0,-1,0,1,0,0,0,0,1]` |
| COB **pre**-multiply vs post-multiply | `cob @ eye == eye @ cob` for a diagonal COB, so the fixture cannot tell the order | Same rotation: `cob @ rot` gives `[[0,1,0],[1,0,0],[0,0,-1]]`, `rot @ cob` gives `[[0,-1,0],[-1,0,0],[0,0,-1]]` |
| `disto_k3` / `disto_t2` emission and both `*_NAME_MAP` lookups | Fixtures use a plain `Intrinsic`; confirmed the OpenMVG fixture's intrinsic data has only `width`/`height`/`focal_length`/`principal_point` and `polymorphic_name: pinhole`, and the AliceVision one has no `distortionParams` | `IntrinsicRadialK3` and `IntrinsicBrownT2` scenes |

The pre-multiply order is the one that matters most: the README explicitly
promises premultiplication, and today nothing enforces it. Use the rotation
`[[0,-1,0],[1,0,0],[0,0,1]]` (a 90° rotation about Z, determinant +1) — asymmetric, exact in floating point,
so no tolerance handling is needed and the fixtures stay byte-comparable.

Also add a multi-view/multi-pose scene to cover sequential id wiring and the
Cereal pointer counter's increments across views and intrinsics.

These need **new** golden files. Do not regenerate
`test/expected/openmvg_sfm.json` or `alicevision_sfm.json` — they are a correct
record of current behaviour, and Phases 2, 3, and 5 all rely on them staying
fixed.

### 4c — Scene model and equality semantics

`add_*` assigns sequential ids and returns the stored element; `add_intrinsic`
dedup returns the *pre-existing* object (assert with `is`, not `==`, since `==` is
the thing under test); `group_models=False` creates a duplicate.

For `Intrinsic.__eq__`, lock the verified current behaviour *before* Phase 5
changes it:

- `IntrinsicRadialK3() == Intrinsic()` -> `False` (type differs)
- `intrinsic == "not an intrinsic"` -> `False` (isinstance guard)
- one side dimensioned, other not -> `False` (short-circuits on width before
  reaching the derived properties)
- **both sides default-constructed -> raises `TypeError`** (Phase 5 changes this;
  write it as an `assertRaises` now and flip it in Phase 5, so the diff makes the
  behaviour change explicit and reviewable)

### 4d — Element details

`Pose` defaults (`[0, 0, 0]` centre, `eye(3)` rotation); `Pose.center` truncating
to three elements; `View.path` coercing `str` to `Path`; `camera_make_model`
string composition.

### 4e — Camera database

`openmvg_load_camdb` with quoted and unquoted camera names, fractional sensor
widths, an unparseable line (currently `print`s an error and continues), and a
missing file.

**Structural change to consider:** split the single `test/sfm_utils_tests.py` into
`test_sfm.py` / `test_openmvg.py` / `test_alicevision.py` / `test_io.py` and move
CI to `python -m unittest discover`. Worth doing while adding this much material —
but it changes the documented test command, so CLAUDE.md and the Phase 1 workflow
must be updated in the same commit.

**Acceptance:** every row of the gap table has at least one test; all three rows
of the 4b hidden-behaviour table have a test that fails if the behaviour is
inverted; matrix green on all four legs; the two original golden files untouched.

## Phase 5 — Intrinsic equality and hash contract (owns latent defect #1)

**Goal:** fix a real crash, and make the hashability decision deliberate.

**The defect, verified:**

```python
s = sfm.Scene()
s.add_intrinsic(sfm.Intrinsic())
s.add_intrinsic(sfm.Intrinsic())   # TypeError: unsupported operand type(s) for /: 'NoneType' and 'float'
```

**Root cause.** `__eq__` compares the *derived* properties `ppx`, `ppy`, and
`focal_length_as_pixels`. Those are lazily computed (`ppx` returns
`self.width / 2.0`) and raise `TypeError` when their inputs are unset. Equality
only reaches them when the raw fields match, so the crash needs *both* sides
under-specified — which is exactly what two default-constructed intrinsics are.
A single under-specified intrinsic in the scene is safe, because `eq` short-
circuits to `False` on the width comparison first. That narrowness is why it has
survived unnoticed.

**Fix:** make `__eq__` None-safe — guard the derived comparisons so an
under-specified intrinsic compares `False` (or compares on raw fields) instead of
raising.

Two rejected alternatives, recorded so they are not revisited:

- *Compare raw stored fields instead of derived ones.* Changes dedup semantics:
  an intrinsic with an explicit `ppx = 50` would stop matching one with
  `width = 100` that derives the same `ppx`. The derived comparison looks
  intentional — it groups cameras by *effective* calibration — so keep it.
- *Make `ppx` / `focal_length_as_pixels` return `None` instead of raising.*
  `test_defaults` explicitly asserts `assertRaises(TypeError)` on those
  properties. That is a documented, tested contract; changing it is a much larger
  breaking change than the bug warrants.

**Hashability.** Verified: `Intrinsic.__hash__` is `None`, because defining
`__eq__` without `__hash__` makes Python set `__hash__ = None`. `Pose` is still
hashable. The decision is to **keep `Intrinsic` unhashable, but declare
`__hash__ = None` explicitly** in the class body so it reads as intent rather
than accident, and document why: field-based equality over a mutable object whose
compared values are lazily derived cannot have a stable hash. Rejected:

- *Hash by identity (`__hash__ = object.__hash__`).* Restores hashability but
  breaks the hash/equality invariant — two equal intrinsics would hash
  differently, silently breaking any future set-based dedup.
- *Hash the compared fields.* The object is mutable (the documented usage sets
  `width` after construction), so the hash would change under the caller, and it
  would raise for under-specified intrinsics for the same reason `__eq__` does.

**Consequence to document in the code:** because unhashable is deliberate,
`add_intrinsic`'s O(n) linear scan is correct by necessity, not an oversight. It
must not later be "optimized" into a `dict`/`set` lookup. A comment at the scan
saying so will save a future reader the round trip.

**Acceptance:** the reproducer above returns a scene with one deduplicated
intrinsic instead of raising; the Phase 4c `assertRaises(TypeError)` is flipped to
assert the new behaviour in the same commit as the fix; `hash(Intrinsic())` still
raises `TypeError` and there is a test asserting that; the golden fixtures are
unchanged, proving export output did not move.

## Phase 6 — Tag-driven PyPI publishing

**Goal:** replace the `python:3.6` + `twine upload` job with a modern,
credential-free release.

- Add `.github/workflows/release.yml`, triggered on tags matching `v*`.
- Use **PyPI Trusted Publishing (OIDC)** via `pypa/gh-action-pypi-publish`, with
  `permissions: id-token: write` and a dedicated `pypi` GitHub environment. **No
  API token stored as a secret** — a strict improvement over the GitLab job.
- Build sdist and wheel, publish both, attach them to a GitHub Release.
- Gate the publish on the test matrix passing for that tag.

**One-time manual setup** (cannot be automated from here): register the trusted
publisher on PyPI for project `PySfMUtils` — owner `educelab`, repository
`sfm-utils`, workflow `release.yml`, environment `pypi`.

**Acceptance:** a dry run publishing to **TestPyPI** from a throwaway tag succeeds
before the first real `v*` tag is pushed.

## Phase 7 — Documentation and repo hygiene

- **README:** replace both GitLab URLs (the development-install command and the
  repository link) with GitHub; update Requirements from "Python 3.6+ / numpy
  1.15+" to the new floors.
- **CLAUDE.md:** it currently documents `python_requires = >=3.6`, the 3.6–3.9
  GitLab matrix, `setup.cfg` as the version location, the GitLab upstream, and the
  merge-request workflow. All five statements become false during this pass. Add
  the Phase 5 outcome to the "easy to get wrong" section: `Intrinsic` is
  deliberately unhashable and the dedup scan is intentionally linear.
- Add `CHANGELOG.md`, starting with this maintenance release. The Phase 5 fix is a
  behaviour change and belongs in it explicitly.
- Add a linter. There is none configured today; `ruff` plus a `lint` job is the
  cheap option. Formatting-only churn lands in its own commit so it never mixes
  with behavioural change.
- `.gitignore`: add `.venv/`; `build/`, `dist/`, and `*.egg-info/` already covered.

---

## Risks and accepted trade-offs

**Static version plus tag-triggered publish can drift.** With the version static
in `pyproject.toml`, tagging `v1.3.0` while the file still reads `1.2.0` builds
and attempts to publish *1.2.0*, which PyPI rejects as a duplicate. Loud rather
than silent, but it wastes a tag. Mitigation is a release checklist: bump
`pyproject.toml`, commit, *then* tag. If it bites more than once, revisit the CI
tag-vs-metadata guard.

**Golden-file fixtures are byte-for-byte.** Any change to key order, formatting,
or emitted fields breaks `TestIO`. That sensitivity is the point — it is what
makes Phases 2, 3, and 5 verifiable — so fixtures get regenerated only
deliberately, never to make a test go green.

**The Cereal emulation is not refactorable.** The `2147483649` pointer counter and
hardcoded `polymorphic_id` values in `scene_to_openmvg` look like magic numbers
but encode OpenMVG's deserializer expectations. Phase 3 especially should leave
them alone.

**AliceVision export remains untested against Meshroom.** Phase 4 locks in the
*current* output's structure, but no phase here verifies that Meshroom accepts it.
That limitation, already documented in the README, survives this pass.

**Phase 5 is a behaviour change in a published library.** Callers relying on
`add_intrinsic` raising `TypeError` for under-specified intrinsics would see it
stop raising. This is judged safe — the current behaviour is a crash in the
documented happy path, not a contract anyone would depend on — but it is why the
fix ships in a minor version bump with a CHANGELOG entry rather than a patch.
