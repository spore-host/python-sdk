"""Tests for the spore SDK — cover exactly the paths the #2 audit found broken.

Everything mocks at the Client.get/post boundary (no network, no AWS). The canned
JSON uses the REAL REST API keys (lambda/rest-api/instances.go, search.go, and
truffle's InstanceTypeResult json tags), so a future key drift fails here.
"""

from __future__ import annotations

import spore
from spore import Client, Instance, SpawnClient, TruffleClient


class FakeClient:
    """A Client stand-in that returns canned responses instead of HTTP calls."""

    def __init__(self, get_return=None, post_return=None):
        self._get_return = get_return or {}
        self._post_return = post_return or {}
        self._region = "us-east-1"
        self.get_calls = []
        self.post_calls = []

    def get(self, path, params=None):
        self.get_calls.append((path, params))
        return self._get_return

    def post(self, path, body=None):
        self.post_calls.append((path, body))
        return self._post_return


# ── Fix #1: module shadowing — the documented quickstart must work ──────────

def test_top_level_truffle_exposes_find():
    # Regression for #2: `spore.truffle` used to resolve to the method-less module.
    # It must forward to a TruffleClient (has .find/.spot/.quota). This must hold
    # even though importing spore.spawn/spore.truffle (top of this file) registers
    # the submodules — the lazy proxy is a real attribute, so it isn't shadowed.
    assert hasattr(spore.truffle, "find")
    assert hasattr(spore.truffle, "spot")
    assert callable(spore.truffle.find)


def test_top_level_spawn_exposes_launch():
    assert hasattr(spore.spawn, "launch")
    assert hasattr(spore.spawn, "list")
    assert callable(spore.spawn.launch)


def test_top_level_proxy_forwards_to_a_real_subclient():
    # The proxy's target is the actual sub-client type.
    assert isinstance(spore.truffle._target(), TruffleClient)
    assert isinstance(spore.spawn._target(), SpawnClient)


def test_private_submodule_import_does_not_shadow_top_level():
    # Importing the (now private) impl module must NOT rebind spore.spawn — the
    # original bug's trigger was a same-named submodule; private names remove it.
    import spore._spawn  # noqa: F401
    assert hasattr(spore.spawn, "launch")   # still the proxy, not the module
    assert callable(spore.spawn.launch)


# ── Fix #3: truffle.find parses the real API keys (was silently zeroing) ────

def test_truffle_find_parses_memory_azs_vcpus():
    fake = FakeClient(get_return={
        "results": [{
            "instance_type": "m7i.2xlarge",
            "region": "us-east-1",
            "vcpus": 8,
            "memory_mib": 32768,
            "gpus": 0,
            "architecture": "x86_64",
            "on_demand_price": 0.4032,
            "availability_zones": ["us-east-1a", "us-east-1b"],
        }]
    })
    tc = TruffleClient(fake)
    results = tc.find("intel 32gb", region="us-east-1")

    assert len(results) == 1
    r = results[0]
    assert r.instance_type == "m7i.2xlarge"
    assert r.vcpus == 8
    assert r.memory_gib == 32.0            # was 0.0 (read memory_mi_b, absent)
    assert r.available_azs == ["us-east-1a", "us-east-1b"]  # was [] (available_a_zs)
    assert r.on_demand_price == 0.4032
    assert r.architecture == "x86_64"


def test_truffle_find_parses_gpu_memory():
    fake = FakeClient(get_return={
        "results": [{
            "instance_type": "p5.48xlarge",
            "region": "us-east-1",
            "vcpus": 192,
            "memory_mib": 2097152,
            "gpus": 8,
            "gpu_model": "H100",
            "gpu_memory_mib": 655360,
            "architecture": "x86_64",
        }]
    })
    r = TruffleClient(fake).find("h100")[0]
    assert r.gpus == 8
    assert r.gpu_model == "H100"
    assert r.gpu_memory_gib == 640.0       # was 0.0 (read gpu_memory_mi_b)
    assert r.memory_gib == 2048.0


# ── Fix #2: spawn.launch returns an Instance (no TypeError) ──────────────────

def _launch_response():
    # Mirrors handleLaunch's jsonResp body (instances.go). Note: no instance_type.
    return {
        "instance_id": "i-0abc123",
        "name": "sim-run",
        "public_ip": "54.1.2.3",
        "private_ip": "10.0.0.5",
        "availability_zone": "us-east-1a",
        "state": "pending",
        "key_name": "spawn-key",
        "region": "us-east-1",
    }


def test_spawn_launch_returns_instance_with_fields():
    fake = FakeClient(post_return=_launch_response())
    sc = SpawnClient(fake)
    inst = sc.launch("c7i.2xlarge", name="sim-run", ttl="4h")

    assert isinstance(inst, Instance)               # was TypeError
    assert inst.instance_id == "i-0abc123"
    assert inst.instance_type == "c7i.2xlarge"      # fallback: response omits it
    assert inst.private_ip == "10.0.0.5"
    assert inst.availability_zone == "us-east-1a"
    assert inst.state == "pending"
    assert inst._client is sc                        # actions/refresh work
    # request body carried the essentials
    _, body = fake.post_calls[0]
    assert body["instance_type"] == "c7i.2xlarge"
    assert body["ttl"] == "4h"


# ── spawn status/list parsing against real instances.go keys ────────────────

def test_spawn_status_parses_instance():
    fake = FakeClient(get_return={
        "instance_id": "i-0abc123", "name": "sim-run", "instance_type": "c7i.2xlarge",
        "state": "running", "region": "us-east-1", "public_ip": "54.1.2.3",
        "private_ip": "10.0.0.5", "availability_zone": "us-east-1a",
        "ttl": "4h", "idle_timeout": "30m", "launch_time": "2026-07-09T00:00:00Z",
    })
    inst = SpawnClient(fake).status("sim-run")
    assert inst.state == "running"
    assert inst.private_ip == "10.0.0.5"
    assert inst.ttl == "4h"
    assert inst.launch_time is not None


def test_spawn_list_parses_instances():
    fake = FakeClient(get_return={"instances": [
        {"instance_id": "i-1", "name": "a", "state": "running", "region": "us-east-1"},
        {"instance_id": "i-2", "name": "b", "state": "running", "region": "us-east-1"},
    ]})
    insts = SpawnClient(fake).list()
    assert [i.instance_id for i in insts] == ["i-1", "i-2"]


# ── Client basics ───────────────────────────────────────────────────────────

def test_client_repr_masks_api_key():
    c = Client(api_key="sk_secret_value_1234567890")
    assert "sk_secre" in repr(c)
    assert "secret_value" not in repr(c)
