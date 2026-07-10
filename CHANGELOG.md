# Changelog

All notable changes to the **spore.host Python SDK** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Release tags use the `python-vX.Y.Z` prefix.

## [Unreleased]

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

[Unreleased]: https://github.com/spore-host/python-sdk/compare/python-v0.1.3...HEAD
[0.1.3]: https://github.com/spore-host/python-sdk/compare/python-v0.1.2...python-v0.1.3
[0.1.2]: https://github.com/spore-host/python-sdk/releases/tag/python-v0.1.2
