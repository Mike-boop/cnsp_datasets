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


@pytest.mark.parametrize("method", ["hw_trigger", "sw_trigger", "stimtrack_xcorr", "onset_only", "dnn", "brain_trf",
                                    "none"])
def test_provenance_accepts_plan_vocabulary(method):
    assert json.loads(provenance(method, "unknown", ""))["alignment_method"] == method


def test_plan_lists_the_same_alignment_methods():
    from pathlib import Path
    from cnsp_datasets.standardise.provenance import ALIGNMENT_METHODS
    plan = (Path(__file__).parents[2] / "PLAN.md").read_text(encoding="utf-8")
    row = next(line for line in plan.splitlines() if line.startswith("| `alignment_method` |"))
    assert set(row.split("|")[2].replace("`", "").replace(" ", "").split(",")) == ALIGNMENT_METHODS
