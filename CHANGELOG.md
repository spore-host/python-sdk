# Changelog

All notable changes to the **spore.host Python SDK** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Release tags use the `python-vX.Y.Z` prefix.

## [Unreleased]

### Fixed
- **A pin's version comment can no longer silently misstate what CI runs.**
  `tests/test_ci_hygiene.py` required only that *some* `# vN` comment be present,
  never that it was true. A wrong label is worse than a missing one: it makes a
  major-version jump read as a routine same-line bump. Not hypothetical —
  Dependabot bumped nf-spawn's `checkout` pin to a **v7.0.1** SHA while leaving the
  comment reading `# v6`, and the identical regex passed it. Two complementary
  halves now, because neither alone suffices: the test requires an exact `vX.Y.Z`
  (offline, hermetic — catches vague labels), and a new `scripts/verify-pins.sh`
  resolves each SHA against the tag its comment claims and fails if they disagree
  (needs the network, so it runs as its own CI step — catches exact-but-false
  labels the offline half cannot see). This repo's nine pins were already exact
  and true, so nothing needed relabelling; the gate is what changed. The new step
  runs in the single-version `lint` job rather than the 4-way `test` matrix, for
  the same reason `ruff` does — pin results don't vary across Python versions.

### Security
- **The PyPI publish job ran a mutable *branch* ref; every action is now pinned to
  a commit SHA, with Dependabot to bump the pins** ([#10]). `publish-python.yaml`
  grants `id-token: write` in the `pypi` environment — whatever runs there can
  publish `spore-host` to PyPI as us — and it invoked
  `pypa/gh-action-pypi-publish@release/v1`. That is a branch, not a tag, so it
  resolved to whatever the branch tip was at the moment the job ran: nothing in
  this repo sat between an upstream force-push and code executing with that
  publish authority. All 9 `uses:` refs across both workflows are now full SHAs
  with a `# vX.Y.Z` comment.
  - A SHA alone would trade a mutable-tag hole for a staleness one — pins don't
    move, including past a security fix — so a new `.github/dependabot.yml` bumps
    them weekly (7-day cooldown, so a freshly-published tag sits before it's
    proposed) and covers `pip` dependencies too. Its group pattern is `*`, not
    `actions/*`: the publish action lives under `pypa/`, which `actions/*` would
    silently exclude. `ruff >=0.16` is explicitly ignored so a bump can't undo the
    deliberate cap below.
  - `tests/test_ci_hygiene.py` makes both halves regressions rather than
    conventions: reverting a pin or dropping the Dependabot entry now fails
    `pytest`, which the existing test matrix already runs. `pyyaml` joins the
    `[dev]` extra so those tests can't degrade into a green skip.
  No change to the shipped `spore` package — CI wiring and tests only.

### Fixed
- **`ruff` was a declared dev dependency that CI never ran, so it enforced
  nothing — it's now pinned `<0.16` and actually invoked.** ruff 0.16 moved a
  large set of opinionated rules into its **default** set; unpinned, `ruff check .`
  reported 76 findings here, of which 73 were annotation-style suggestions
  (`UP045`/`UP037`/`UP006`) that the rest of the suite doesn't enforce either. With
  the cap, 3 real findings remained, all in `examples/` and all fixed:
  - `marimo_example.py` computed a `state_color` for the instance state and then
    never used it — the status table rendered the state uncolored. Now applied, as
    originally intended.
  - `script_example.py` had an f-string with no placeholders.
  - `jupyter_example.ipynb` tripped `E402` (import not at top of cell), which is
    inherent to notebooks — every cell is its own top level — so it's excluded per
    file rather than worked around in the example.
  A `lint` job now runs `ruff check .` on 3.12 (lint results don't vary across the
  test matrix), so the pin protects a check that actually executes. Matches the cap
  on the four workflow adapters.
  No change to the shipped `spore` package — examples, tooling and CI only.

## [0.1.5] - 2026-07-10

### Added
- **`spawn.launch()` now exposes the remaining launch parameters** (#6):
  `ami` (custom AMI), `key_name` (SSH key pair), `pre_stop` (pre-stop hook), and
  `completion_file` (path spored watches). These were accepted by the REST launch
  endpoint but not surfaced by the SDK. With this, the SDK covers the full launch
  body. Additive; unset params are omitted.

## [0.1.4] - 2026-07-10

### Added
- **`spore.notifications` — SMS notification registration.** New
  `NotificationsClient` (`spore.notifications.register(...)` /
  `.deregister(...)`) wrapping `POST` / `DELETE /v1/notifications/register` — the
  one REST endpoint the SDK didn't cover. Supply your chat identity as
  `platform=`/`workspace_id=`/`user_id=` (assembled into the
  `platform#workspace#user` key spore-bot uses) or a raw `user_key=`. Also adds
  `Client.delete()`. (#5)

### Fixed
- **`spawn.launch()` no longer advertises a dead `phone=` parameter.** It was
  documented for SMS but silently did nothing — launch doesn't accept `phone`,
  and SMS registration is a separate endpoint. Removed it; register a number via
  `spore.notifications.register(...)` instead. (#4)

## [0.1.3] - 2026-07-09

### Fixed
- **`spore.truffle` / `spore.spawn` now work as documented.** The top-level
  quickstart (`import spore; spore.truffle.find(...)`) resolved `spore.truffle`
  to the *module* (which has no `.find`), because the same-named submodule
  shadowed the module-level `__getattr__` hook — and importing it is unavoidable
  (the client does it internally). The implementation modules are renamed to
  `spore._truffle` / `spore._spawn` (private), and `spore.truffle`/`spore.spawn`
  are now robust lazy proxies to a default client's sub-clients. Public classes
  are re-exported from the top level: `from spore import Client, SpawnClient,
  TruffleClient, Instance, InstanceType, SpotPrice, QuotaInfo`.
- **`spore.spawn.launch()` no longer raises `TypeError`.** It constructed
  `Instance(private_ip=…, availability_zone=…)` but those fields didn't exist on
  the dataclass. Added `private_ip` / `availability_zone` to `Instance` (populated
  by launch/status/list), and `launch()` now builds its `Instance` through the
  same `_parse` path as the rest of the client.
- **`spore.truffle.find()` no longer returns zeroed memory, GPU memory, and AZs.**
  The parser read mangled JSON keys (`memory_mi_b`, `gpu_memory_mi_b`,
  `available_a_zs`) that the REST API never sends; it now reads the real keys
  (`memory_mib`, `gpu_memory_mib`, `availability_zones`, `vcpus`, `gpus`), so
  `memory_gib` / `gpu_memory_gib` / `available_azs` are populated correctly.

### Added
- Test suite (`tests/test_sdk.py`) covering the quickstart entry points and the
  parsers against the real REST API JSON keys. CI now runs it as a gate (it
  previously swallowed a missing/failing suite with `|| echo "No tests yet"`),
  so a broken SDK can no longer ship green.

## [0.1.2]

Baseline. Earlier history is in the
[GitHub Releases](https://github.com/spore-host/python-sdk/releases) and the
[commit log](https://github.com/spore-host/python-sdk/commits/main).

---

[#10]: https://github.com/spore-host/python-sdk/issues/10

[Unreleased]: https://github.com/spore-host/python-sdk/compare/python-v0.1.5...HEAD
[0.1.5]: https://github.com/spore-host/python-sdk/compare/python-v0.1.4...python-v0.1.5
[0.1.4]: https://github.com/spore-host/python-sdk/compare/python-v0.1.3...python-v0.1.4
[0.1.3]: https://github.com/spore-host/python-sdk/compare/python-v0.1.2...python-v0.1.3
[0.1.2]: https://github.com/spore-host/python-sdk/releases/tag/python-v0.1.2
