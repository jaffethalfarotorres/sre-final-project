"""The one rule for which pods count as part of the lab (shared by lab.py and smoke_test.py)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import labpods  # noqa: E402


def pod(name, phase="Running", ready=True, owners=True):
    return {"metadata": {"name": name, "ownerReferences": [{"kind": "ReplicaSet"}] if owners else []},
            "status": {"phase": phase, "containerStatuses": [{"ready": ready}]}}


def test_drill_pod_never_counts_in_any_state():
    for phase in ("Running", "Pending", "Succeeded", "Failed", "Unknown"):
        assert not labpods.counts(pod("errload", phase=phase, ready=False, owners=False))


def test_finished_one_off_pods_do_not_count_but_owned_ones_do():
    assert not labpods.counts(pod("job-x", phase="Succeeded", owners=False))
    assert labpods.counts(pod("web-1", phase="Failed", owners=True))


def test_ready_needs_running_and_every_container_ready():
    assert labpods.is_ready(pod("a"))
    assert not labpods.is_ready(pod("a", ready=False))
    assert not labpods.is_ready(pod("a", phase="Pending"))
    assert not labpods.is_ready({"metadata": {"name": "a"}, "status": {"phase": "Running"}})
