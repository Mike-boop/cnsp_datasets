"""Write pieces.csv and source_cover.csv from the shipped files (see splices.py).
Usage: python -m cnsp_datasets.datasets.zhang2023.alignment.make_maps <download_dir>"""
import sys

from cnsp_datasets.datasets.zhang2023.alignment.splices import write_maps

if __name__ == "__main__":
    write_maps(sys.argv[1])
