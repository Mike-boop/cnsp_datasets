"""Per-trial provenance sidecar (raw.info["description"]), fields and values as in PLAN.md section 2."""
from __future__ import annotations

import json

ALIGNMENT_METHODS = {"hw_trigger", "sw_trigger", "stimtrack_xcorr", "onset_only", "dnn", "brain_trf", "none"}
TRIGGER_TYPES = {"hardware", "software", "unknown"}
VALIDATION_TIERS = {"none", "low", "mlr", "brainstem", None}


def provenance(alignment_method: str, trigger_type: str, notes: str, drift_ppm: float | None = None,
               jitter_ms: float | None = None, validation_tier: str | None = None, **extra) -> str:
    """
    JSON provenance of one trial. trigger_type starts with hardware/software/unknown, followed by its source
    (e.g. "software (inferred; not documented)"); validation_tier None = not validated yet. extra: dataset fields.
    """
    if alignment_method not in ALIGNMENT_METHODS:
        raise ValueError(f"alignment_method {alignment_method!r} not in {sorted(ALIGNMENT_METHODS)}")
    if trigger_type.split(" ", 1)[0] not in TRIGGER_TYPES:
        raise ValueError(f"trigger_type {trigger_type!r} does not start with one of {sorted(TRIGGER_TYPES)}")
    if validation_tier not in VALIDATION_TIERS:
        raise ValueError(f"validation_tier {validation_tier!r} not in {VALIDATION_TIERS}")
    return json.dumps({"alignment_method": alignment_method, "trigger_type": trigger_type, "drift_ppm": drift_ppm,
                       "jitter_ms": jitter_ms, "validation_tier": validation_tier, **extra, "notes": notes})
