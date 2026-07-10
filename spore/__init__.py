"""
spore-host — ephemeral EC2 compute for researchers.

Quick start:
    import spore
    results = spore.truffle.find("nvidia h100", region="us-east-1")
    instance = spore.spawn.launch("c8a.2xlarge", ttl="8h")

Or with an explicit client:
    from spore import Client
    c = Client(region="us-east-1")
    c.truffle.find("amd epyc genoa")
"""

# Defer annotation evaluation so `_default: Client | None` (PEP 604 union) doesn't
# execute at import on Python 3.9 (requires-python >=3.9); without this it raises
# `TypeError: unsupported operand type(s) for |`.
from __future__ import annotations

from .client import Client
from ._spawn import Instance, SpawnClient
from ._truffle import InstanceType, QuotaInfo, SpotPrice, TruffleClient

# Module-level convenience: a default client using ambient AWS credentials.
_default: Client | None = None


def _get_default() -> Client:
    global _default
    if _default is None:
        _default = Client()
    return _default


class _LazySubClient:
    """Proxy for `spore.truffle` / `spore.spawn` that forwards to the default
    client's sub-client, constructing the default `Client()` on first use (so
    `import spore` has no credential-resolution side effect).

    The implementation modules are named ``_truffle`` / ``_spawn`` (private) so
    these public proxy attributes never collide with a submodule. An earlier
    version kept the modules named ``truffle``/``spawn`` and relied on a
    module-level ``__getattr__``, but importing a same-named submodule (which
    ``Client.__init__`` does) permanently rebinds ``spore.truffle`` to the module
    and shadows the hook — so ``spore.truffle`` resolved to the method-less module
    (bug #2). Private module names remove the collision entirely.
    """

    __slots__ = ("_attr",)

    def __init__(self, attr: str):
        self._attr = attr

    def _target(self):
        return getattr(_get_default(), self._attr)

    def __getattr__(self, name: str):
        return getattr(self._target(), name)

    def __repr__(self) -> str:
        return repr(self._target())


truffle = _LazySubClient("truffle")
spawn = _LazySubClient("spawn")

__version__ = "0.1.3"
__all__ = [
    "Client",
    "truffle",
    "spawn",
    "SpawnClient",
    "TruffleClient",
    "Instance",
    "InstanceType",
    "SpotPrice",
    "QuotaInfo",
]
