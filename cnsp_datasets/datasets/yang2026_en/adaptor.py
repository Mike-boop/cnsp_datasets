from functools import partial

from cnsp_datasets.datasets.yang2026_base.adaptor import Yang2026Adaptor

ADAPTOR = partial(Yang2026Adaptor, site="en")
