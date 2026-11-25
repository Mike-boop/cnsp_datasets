from cnsp_datasets.datasets.yang2026_base.adaptor import Yang2026Adaptor


class Yang2026RUAdaptor(Yang2026Adaptor):
    """yang2026_ru: the site "ru" listeners."""

    def __init__(self, download_dir: str, **options):
        super().__init__(download_dir, site="ru", **options)


ADAPTOR = Yang2026RUAdaptor
