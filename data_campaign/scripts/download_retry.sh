#!/bin/bash
# Resumable download with retries (OpenNeuro's GraphQL listing returns transient 502s). Usage: download_retry.sh <dataset>
d=$1; R=/data_storage/gu08wuvu/datasets/tmp/review; mkdir -p $R/$d
for attempt in 1 2 3 4 5 6; do
  echo "=== $d attempt $attempt start $(date)"
  (cd /tmp && /home/gu08wuvu/cnsp_datasets/.venv/bin/python -u -c "
import sys; sys.path.insert(0, '/home/gu08wuvu/cnsp_datasets_dev')
from cnsp_datasets.download import download_dataset
download_dataset(dataset_name='$d', download_dir='$R/$d/download', max_workers=${WORKERS:-2}, retries=5, skip_existing=True, extract_archives=True)
") && { echo "=== $d exit 0 $(date)"; exit 0; }
  echo "=== $d attempt $attempt failed $(date)"; sleep 60
done
echo "=== $d exit 1 $(date)"; exit 1
