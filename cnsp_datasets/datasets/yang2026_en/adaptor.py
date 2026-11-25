from cnsp_datasets.datasets.yang2026_base.adaptor import Yang2026Adaptor


class Yang2026ENAdaptor(Yang2026Adaptor):
    """yang2026_en: the site "en" listeners."""

    def __init__(self, download_dir: str, **options):
        super().__init__(download_dir, site="en", **options)


ADAPTOR = Yang2026ENAdaptor
