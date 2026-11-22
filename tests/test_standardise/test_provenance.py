import json

import pytest

from cnsp_datasets.standardise.provenance import provenance


def test_provenance_round_trips():
    d = json.loads(provenance("sw_trigger", "software (inferred)", "a note", jitter_ms=7, block=2))
    assert d == {"alignment_method": "sw_trigger", "trigger_type": "software (inferred)", "drift_ppm": None,
                 "jitter_ms": 7, "validation_tier": None, "block": 2, "notes": "a note"}


@pytest.mark.parametrize("kwargs", [{"alignment_method": "xcorr"}, {"trigger_type": "LSL"},
                                    {"validation_tier": "high"}])
def test_provenance_rejects_invalid_values(kwargs):
    args = {"alignment_method": "none", "trigger_type": "unknown", "notes": ""} | kwargs
    with pytest.raises(ValueError):
        provenance(**args)
