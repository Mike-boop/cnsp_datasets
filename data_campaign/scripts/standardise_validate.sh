#!/bin/bash
# usage: standardise_validate.sh <dataset> [--adaptor-opt key=value ...] [extra validate args...]
# Standardises <review>/<dataset>/download with the dataset's adaptor (FlatSinkV1), then validates the result.
# Leading --adaptor-opt pairs go to the adaptor constructor (values parsed as Python literals where possible).
set -u
R=/data_storage/gu08wuvu/datasets/tmp/review
d=$1; shift
opts=()
while [ $# -ge 2 ] && [ "$1" = --adaptor-opt ]; do opts+=(--adaptor-opt "$2"); shift 2; done
[ "${1:-}" = --adaptor-opt ] && { echo "--adaptor-opt needs a value" >&2; exit 2; }
cd ${CNSP_REPO:-/home/gu08wuvu/cnsp_datasets}
export MNE_DONTWRITE_HOME=true
echo "=== $d standardise start $(date) ${opts[*]}"
rm -rf $R/$d/standardised
/home/gu08wuvu/cnsp_datasets/.venv/bin/python -u -m cnsp_datasets.standardise.format_dataset "$d" "$R/$d/download" \
    "$R/$d/standardised" "${opts[@]}" > "$R/$d/standardise.log" 2>&1
echo "=== $d standardise exit $? $(date)"
/home/gu08wuvu/cnsp_datasets/.venv/bin/python -u -m cnsp_datasets.validate $d --standardised-dir $R/$d/standardised --n-subjects 0 \
    --json $R/$d/validation.json --fig-dir $R/$d --reference average "$@" > $R/$d/validate.log 2>&1
echo "=== $d validate exit $? $(date)"
