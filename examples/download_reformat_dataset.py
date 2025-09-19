from cnsp_datasets.download import download_dataset
from cnsp_datasets.standardise.format_dataset import format_dataset
from cnsp_datasets.standardise.flat_sink import FlatSinkV1


if __name__ == "__main__":

    # define paths where the dataset will be downloaded/standardised to
    dataset_name = "weissbart2019"
    downloaded_dataset_dir = f"/data_nfs/gu08wuvu/datasets/{dataset_name}/downloaded"
    standardised_data_dir = f"/data_nfs/gu08wuvu/datasets/{dataset_name}/standardised-flat"

    # download the dataset
    download_dataset(
        dataset_name=dataset_name,
        download_dir=downloaded_dataset_dir,
        max_workers=6, retries=3, skip_existing=False,
        extract_archives=True, verify_checksum=False
        )
    
    # and standardise it
    format_dataset(
        dataset_name=dataset_name,
        download_dir=downloaded_dataset_dir,
        standardised_dir=standardised_data_dir,
        sinker_handle=FlatSinkV1
        )