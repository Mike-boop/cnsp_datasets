from importlib import import_module
from cnsp_datasets.standardise.flat_sink import FlatSinkV1

def get_adaptor_class(dataset_name):
    
    module_path = f"cnsp_datasets.datasets.{dataset_name}.adaptor"

    try:
        mod = import_module(module_path)
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            f"Error finding adaptor for dataset{dataset_name}: could not find module path '{module_path}'. "
            f"Please ensure that the dataset name is correct and that an adaptor module exists."
        ) from e
    
    try:
        adaptor = getattr(mod, "ADAPTOR")
    except AttributeError as e:
        raise AttributeError(
            f"Module '{module_path}' does not define ADAPTOR. "
            f"Please ensure that an ADAPTOR sentinel is defined in '{module_path}.py'."
        ) from e
    
    return adaptor


def standardise_dataset(
    dataset_name,
    download_dir,
    standardised_dir,
    sinker_handle=FlatSinkV1
):
    
    Adaptor = get_adaptor_class(dataset_name)
    adaptor = Adaptor(download_dir=download_dir)

    sinker = sinker_handle(save_directory=standardised_dir)

    for record in adaptor.parse():
        sinker.save_record(record)
