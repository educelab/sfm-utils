# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PySfMUtils (`sfm_utils`) is a small, dependency-light (numpy only) Python library that models a
Structure-from-Motion scene in a format-agnostic way and exports it to OpenMVG and
AliceVision/Meshroom project files. Its original purpose is injecting known pose priors into an
OpenMVG pipeline. Upstream is GitLab (`gitlab.com/educelab/sfm-utils`); releases go to PyPI as
`PySfMUtils`.

## Commands

```shell
# Run the full test suite (this is exactly what CI runs)
python -m unittest -v test.sfm_utils_tests

# Run a single test case / test method
python -m unittest -v test.sfm_utils_tests.TestIO
python -m unittest -v test.sfm_utils_tests.TestIntrinsics.test_radial_k3

# Editable install for development
python -m pip install -e .

# Build distributions (what the deploy job does)
python -m build
```

Only `python3` is on PATH on this machine (`python` is not); CI images provide `python`.
numpy is not installed in the system interpreter, so use a virtualenv to run the suite locally.

There is no linter or formatter configured. CI (`.gitlab-ci.yml`) runs the unittest suite on
Python 3.6–3.9; the package declares `python_requires = >=3.6`, so avoid syntax and stdlib APIs
newer than 3.6.

## Architecture

Three layers, all re-exported flat into the `sfm_utils` namespace by `__init__.py`:

1. **`sfm.py` — the format-agnostic scene model.** `Scene` owns three parallel lists (`views`,
   `intrinsics`, `poses`) of `SceneElement` subclasses. Elements have no id until they are added
   to a scene: `Scene.add_*()` assigns `element.id = len(list)` and *returns the stored element*.
   The intended usage is always `view.intrinsic = scene.add_intrinsic(intrinsic)` — because
   `add_intrinsic(group_models=True)` (the default) deduplicates via `Intrinsic.__eq__` and may
   return a *different, pre-existing* object than the one passed in. `View` holds direct object
   references to its `Intrinsic` and `Pose`, not indices; exporters read `.id` off those objects.

2. **`openmvg.py` / `alicevision.py` — pure `Scene -> dict` converters.** `scene_to_openmvg()` and
   `scene_to_alicevision()` build a plain dict that mirrors the target file format; neither
   touches the filesystem. Adding a new target format means adding a `scene_to_<fmt>()` here plus
   a `Format` enum member and a branch in `export_scene`.

3. **`io.py` — the public entry point.** `export_scene()` selects a converter by `Format` and
   `json.dump`s it with `indent=4`.

### Things that are easy to get wrong

- **Change-of-basis defaults differ between the two API levels.** `export_scene(cob_matrix=None)`
  substitutes a *format-specific default* (for OpenMVG, `diag(-1, 1, -1)`, converting this
  package's right-handed rotations to OpenMVG's left-handed system). The lower-level
  `scene_to_alicevision(cob_matrix=None)` means *no* change of basis, while
  `scene_to_openmvg()`'s own default parameter is the OpenMVG matrix. Callers pass a 3x3 identity
  to disable the conversion, not `None`.
- **OpenMVG output emulates Cereal's serialization.** `scene_to_openmvg` fakes shared-pointer ids
  with a counter starting at `2147483649` and hardcoded `polymorphic_id` values. These are not
  meaningful numbers to change; OpenMVG's deserializer depends on their structure.
- **`TestIO` compares exported JSON byte-for-byte against golden files** in `test/expected/`. Any
  change to key order, formatting, or emitted fields requires regenerating those fixtures
  deliberately — don't "fix" the test by loosening the comparison without reason.
- **Intrinsic properties are lazily derived.** `ppx`/`ppy` default to half the image dimensions and
  `focal_length_as_pixels` is computed from `max(width, height) * focal_length / sensor_width`
  unless explicitly set; reading them before the inputs are set raises `TypeError` (tested
  behavior). `dist_params` setters truncate the input list to the type's coefficient count
  (3 for `IntrinsicRadialK3`, 5 for `IntrinsicBrownT2`).
- **Module-level names with a double-underscore prefix** (e.g. `__OPENMVG_DEFAULT_COB`,
  the `*_NAME_MAP` dicts) are intentionally excluded from the `from ... import *` re-export in
  `__init__.py`. Import them by explicit path if needed internally.
- Every source file carries the GPLv3 header block; keep it on new files.

## Release

Version lives in `setup.cfg` under `[metadata]`. Pushing a tag matching `v*` triggers the
`deploy:pypi` CI job (`python -m build` + `twine upload`). Work merges into `develop` via merge
requests, not directly to a `main`/`master` branch.
