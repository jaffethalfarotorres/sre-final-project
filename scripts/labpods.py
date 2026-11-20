"""One definition of which pods count as part of the running lab (used by lab.py and smoke_test.py).

The alert-drill pod (`errload`) and any finished one-off pod come and go on purpose, so they never count as
"not ready". Everything else in the lab namespaces must be running and ready.
"""

DRILL_POD = "errload"
LAB_NAMESPACES = ("application", "monitoring", "opentelemetry")


def is_one_off(pod):
    """True for the drill pod and for finished pods that no Deployment owns."""
    meta = pod.get("metadata", {})
    if meta.get("name") == DRILL_POD:
        return True
    phase = pod.get("status", {}).get("phase", "")
    return phase in ("Succeeded", "Failed") and not meta.get("ownerReferences")


def counts(pod):
    """True when the pod is part of the lab (and so must be ready)."""
    return not is_one_off(pod)


def is_ready(pod):
    """True when the pod is Running and every container reports ready."""
    status = pod.get("status", {})
    containers = status.get("containerStatuses") or []
    return status.get("phase") == "Running" and bool(containers) and all(c.get("ready") for c in containers)
