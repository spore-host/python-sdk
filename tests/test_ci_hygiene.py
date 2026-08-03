"""Tests that assert on repo wiring rather than on code.

Wiring is what rots: a pin reverted to `@v5` or a deleted Dependabot entry is a
one-line change whose absence is completely silent — nothing fails, the supply
chain just quietly goes back to being mutable. These make that fail a test.

The stakes here are specific. `publish-python.yaml` holds `id-token: write` in the
`pypi` environment, so whatever executes in that job can publish `spore-host` to
PyPI as us. It previously ran `pypa/gh-action-pypi-publish@release/v1` — a BRANCH
ref, resolved at job time — so nothing in this repo sat between an upstream
force-push and code running with that authority (#10).
"""

from __future__ import annotations

import re
from pathlib import Path

# PyYAML is a declared dev dependency (pyproject.toml `[dev]`), imported directly
# rather than behind a try/except: a guarded import degrades to a skip, and a
# skipped wiring test reports green while asserting nothing — the same silent
# no-op these tests exist to catch. If this import fails, `pip install -e ".[dev]"`
# didn't run, and that should be loud.
import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"

# owner/action@<40-hex> followed by a `# vX.Y.Z` comment. The comment is required:
# a bare SHA is unreadable, and the version is what makes a bump reviewable —
# without it nobody can tell whether a pin is current or two years stale.
PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}\s+#\s*v?\d")


def _uses_refs() -> list[tuple[str, int, str]]:
    """Every registry action ref in the workflows, as (file, line_no, ref)."""
    refs = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        for i, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.strip().removeprefix("- ")
            if not stripped.startswith("uses:"):
                continue
            ref = stripped[len("uses:") :].strip()
            if ref.startswith("./"):  # a local path, not a registry ref
                continue
            refs.append((path.name, i, ref))
    return refs


def test_actions_are_pinned_to_shas() -> None:
    """Every `uses:` must name a full commit SHA, not a tag or branch.

    A tag is mutable and a branch more so: `@v5` means "whatever v5 points at when
    the job runs". `actions/checkout@v6` really did move (df4cb1c 2026-06-02 →
    d23441a 2026-07-16) with no signal to consumers, so this is not hypothetical.
    """
    refs = _uses_refs()
    # Anti-vacuous: a parser that silently stops matching would pass forever.
    assert refs, f"no `uses:` lines found under {WORKFLOWS} — this test is asserting nothing"

    unpinned = [
        f"{name}:{line}: {ref}" for name, line, ref in refs if not PINNED.match(ref)
    ]
    assert not unpinned, (
        "these actions are not pinned to a full commit SHA with a version comment:\n  "
        + "\n  ".join(unpinned)
        + "\nA tag or branch is mutable, so the code CI runs can change with no commit "
        "here — and publish-python.yaml runs with PyPI publish authority. Use:\n"
        "    uses: owner/action@<40-hex-sha> # vX.Y.Z"
    )


def test_dependabot_covers_every_action() -> None:
    """The other half of pinning: something must bump the pins.

    A SHA never moves, including past a security fix. Pinning without Dependabot
    just trades a mutable-tag hole for a staleness one, so the two are one control.
    The check that matters is coverage — an ecosystem entry whose group patterns
    don't match an action leaves it outside the grouped PR, silently.
    """
    config = REPO / ".github" / "dependabot.yml"
    assert config.exists(), (
        "no .github/dependabot.yml: the actions here are pinned to SHAs, so without "
        "Dependabot nothing ever bumps them"
    )
    cfg = yaml.safe_load(config.read_text())
    assert cfg.get("version") == 2, f"dependabot version must be 2, got {cfg.get('version')}"

    patterns: list[str] = []
    found_entry = False
    for update in cfg.get("updates", []):
        if update.get("package-ecosystem") != "github-actions":
            continue
        found_entry = True
        dirs = update.get("directories") or [update.get("directory")]
        assert dirs == ["/"], (
            f"the github-actions entry watches {dirs}; workflows live in "
            '.github/workflows, which Dependabot finds via directory "/"'
        )
        for group in (update.get("groups") or {}).values():
            patterns.extend(group.get("patterns", []))
    assert found_entry, (
        "dependabot.yml has no `github-actions` entry, so the SHA-pinned actions "
        "are never bumped"
    )

    for name, _, ref in _uses_refs():
        action = ref.split("@", 1)[0]
        matched = any(_glob(p, action) for p in patterns)
        assert matched, (
            f"{action} (in {name}) is not matched by any Dependabot group pattern "
            f"{patterns}, so it would open its own PR outside the group, or be "
            "missed. Widen the pattern."
        )


def test_dependabot_covers_python_dependencies() -> None:
    """pyproject.toml's dependencies need bumping too, not just the actions."""
    cfg = yaml.safe_load((REPO / ".github" / "dependabot.yml").read_text())
    ecosystems = {u.get("package-ecosystem") for u in cfg.get("updates", [])}
    assert "pip" in ecosystems, (
        "dependabot.yml has no `pip` entry, so pyproject.toml's dependencies are "
        f"never updated (found: {sorted(e for e in ecosystems if e)})"
    )


def _glob(pattern: str, value: str) -> bool:
    """Dependabot's only wildcard is `*`, matching any run of characters."""
    parts = pattern.split("*")
    if len(parts) == 1:
        return pattern == value
    if not value.startswith(parts[0]):
        return False
    value = value[len(parts[0]) :]
    for middle in parts[1:-1]:
        idx = value.find(middle)
        if idx < 0:
            return False
        value = value[idx + len(middle) :]
    return value.endswith(parts[-1])
