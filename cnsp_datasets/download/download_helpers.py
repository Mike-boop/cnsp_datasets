import os
import re
import gzip
import shutil
import zipfile
import tarfile
import requests

from queue import Queue
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse


## general utilities

def extract_archives(download_dir, recursive=False):
    """
    Extract all archives in the specified directory.
    Supports .zip, .tar, .tar.gz, and .gz (single file).
    If `recursive` is True, also extracts archives found within extracted archives.

    Notes:
    Does not extract .nii.gz files; these can be extracted on-the-fly with nibabel.
    """
    for dirpath, dirnames, filenames in os.walk(download_dir):
        for filename in filenames:
            print(filename)
            file_path = os.path.join(dirpath, filename)

            if filename.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(dirpath)
                print(f"Extracted {filename} to {dirpath}")
                os.remove(file_path)

            elif filename.endswith(('.tar', '.tar.gz')):

                with tarfile.open(file_path, 'r:*') as tar_ref:
                    tar_ref.extractall(dirpath)
                print(f"Extracted {filename} to {dirpath}")
                os.remove(file_path)

            elif filename.endswith('.gz') and not (filename.endswith('.tar.gz') or filename.endswith('.nii.gz')):
                output_file = os.path.splitext(file_path)[0]
                with gzip.open(file_path, 'rb') as f_in:
                    with open(output_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                print(f"Decompressed {filename} to {output_file}")
                os.remove(file_path)

            if recursive:
                # Optionally dive into newly extracted folders
                if filename.endswith(('.tar.gz')):
                    filename_no_ext = filename.replace('.tar.gz', '')
                else:
                    filename_no_ext = os.path.splitext(filename)[0]
                extract_archives(os.path.join(dirpath, filename_no_ext), recursive=True)

## helpers for obtaining downloadable files (urls) and checksums (where available) from a particular dataset identifier.
## all of these functions return a list of dicts, each dict containing:
## - 'url': the url to download the file from
## - 'name': the filename (or relative path) to save the file as
## - 'checksum' (optional): the expected md5 checksum of the file, in the format "md5:abcd1234". If unavailable, the value is `None`.

def doi_to_downloadables_zenodo(doi):
    """
    Get a list of downloadable files from a Zenodo DOI.

    Example doi string format: "10.5281/zenodo.1234567"
    """

    zenodo_record_id = doi.split("zenodo")[-1][1:]

    zenodo_api_url = f"https://zenodo.org/api/records/{zenodo_record_id}"
    response = requests.get(zenodo_api_url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for DOI {doi}: {response.status_code}")
    
    metadata = response.json()
    files = metadata['files']

    file_data = [{"name": file['key'], "url": file['links']['self'], "checksum": file['checksum']} for file in files]

    return file_data

def doi_to_downloadables_dryad(doi):
    """
    Get a list of downloadable files from a Dryad DOI.

    Example doi string format: "10.5061/dryad.1234567"
    """

    encoded_doi = quote(f"doi:{doi}", safe='')
    dryad_server = "https://datadryad.org"

    dryad_api_url = f"{dryad_server}/api/v2/datasets/{encoded_doi}"
    response = requests.get(dryad_api_url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for DOI {doi}: {response.status_code}")
    
    metadata = response.json()
    version = metadata["_links"]["stash:version"]["href"]

    files_metadata_url = "/".join([dryad_server, version, "files"])
    files_metadata_response = requests.get(files_metadata_url)

    if files_metadata_response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for files request {files_metadata_url}: {response.status_code}")
    
    files_metadata = files_metadata_response.json()

    file_data = [{"name": entry["path"], "url": '/'.join([dryad_server, entry["_links"]["self"]["href"], "download"]), "checksum":None} for entry in files_metadata["_embedded"]["stash:files"]]

    return file_data

def doi_to_downloadables_dataverse(doi, dataverse_server="https://rdr.kuleuven.be"):
    """
    Get a list of downloadable files from a Dataverse DOI.

    Example doi string format: "10.48804/K3VSND"

    Note: this function ignores .data_dict pickle files, which are included in the Bollens2023 dataset.
    This is because these files contain copies of the raw data contained in other files, and can be ommitted
    to save download time and disk space.
    """

    dataverse_api_url = f"{dataverse_server}/api/datasets/:persistentId?persistentId=doi:{doi}"
    response = requests.get(dataverse_api_url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for DOI {doi}: {response.status_code}")
    
    metadata = response.json()["data"]["latestVersion"]
    files_metadata = metadata["files"]

    file_ids = [file_info["dataFile"]["id"] for file_info in files_metadata]
    file_urls = [f"{dataverse_server}/api/access/datafile/{id}?gbrecs=true" for id in file_ids]

    file_data = [
        {
            "name": os.path.join(file.get("directoryLabel", ""), file["dataFile"]["filename"]),
            "url": file_urls[i],
            "checksum": file["dataFile"]["checksum"] 
        }
        for i, file in enumerate(files_metadata)
    ]
    file_data = [file for file in file_data if not file["name"].endswith(".data_dict")]

    return file_data

def doi_to_downloadables_drum(doi):

    """
    Get a list of downloadable files from a DSpace DOI.

    Example doi string format: "10.13016/M2599Z52H"

    Note:
    This function scrapes the HTML page for the DOI to find file links, then queries the Drum API for metadata including checksums.
    This approach may break if the Drum website structure changes; we should at a minimum add informative error-handling to indicate
    if this has happened (prompting an update to our code).

    DSpace has an API but the UMD Drum requires an access token for it, which we typically do not have. My best guess at how the API could
    be used (with an access token) is provided in a separate function in this file.
    """

    dataset_url = f"https://doi.org/{doi.strip('/')}"
    response = requests.get(dataset_url, allow_redirects=True)

    if response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for DOI {doi}: {response.status_code}")
    
    file_data = []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    for link in soup.find_all("link", rel="item"):

        url = link.get("href")

        if "/bitstreams/" not in url:
            continue

        file_uuid = url.split("/")[-2]

        drum_api_url = f"https://api.drum.lib.umd.edu/server/api/core/bitstreams/{file_uuid}"

        response = requests.get(drum_api_url)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve metadata for URL {drum_api_url}: {response.status_code}")
        
        metadata = response.json()

        name = metadata["metadata"]["dc.title"][0]["value"]

        if "checkSum" in metadata["metadata"]:
            checksum = ":".join([
                metadata["metadata"]["checkSum"]["checkSumAlgorithm"],
                metadata["metadata"]["checkSum"]["value"]
            ])
        else:
            checksum = None

        file_data.append({
            "name": name,
            "url": url,
            "checksum": checksum
        })

    return file_data

def id_to_downloadables_deepblue(id):
    """
    Get a list of downloadable files from a DeepBlue dataset ID.

    Example id string format: "bn999738r"

    Note: I think there is no mapping between the dataset ID and the DOI.
    """

    dataset_url = f"https://deepblue.lib.umich.edu/data/concern/data_sets/{id}.json"

    response = requests.get(dataset_url)

    if response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for dataset ID {id}: {response.status_code}")
    
    metadata = response.json()
    file_data = []

    for file_set in metadata["file_sets"]:
        
        id = file_set["id"]
        url = "https://deepblue.lib.umich.edu/data/downloads/" + id
        checksum = ":".join([file_set["checksum_algorithm"], file_set["checksum_value"]])
        name = file_set["label"]

        file_data.append({
            "name": name,
            "url": url,
            "checksum": checksum
        })
    return file_data

### Open Science Framework datasets must be queried hierarchically to find the downlaodable files within each sub-directory.
### Therefore, the following functions implement logic to walk the "OSF Tree" structure and collect downloadable files alongside
### their relative paths. OSF can be pretty slow to respond, so queries are made in parallel.


def doi_to_downloadables_osf(osf_id):
    """
    Get a list of downloadable files from an OSF DOI.

    Example doi string format: "10.17605/OSF.IO/XXXX"
    (where XXXX is the OSF project ID)

    Returns a list of dictionaries with the following keys
    - name: File name
    - url: Download URL
    - checksum: MD5 checksum of the file (if available), otherwise None
    """

    base_api = "https://api.osf.io/v2"

    osf_root_url = f"{base_api}/nodes/{osf_id}/files/osfstorage/"
    file_metadata = walk_osf_directory_fetch_files(osf_root_url)

    file_data = [{"name": file["name"], "url": file["url"], "checksum": file["checksum"]} for file in file_metadata]

    return file_data

def fetch_osf_leaves_branches(osf_dir_url):
    """
    Fetch all leaves and branches from an OSF directory.
    """
    response = requests.get(osf_dir_url)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for URL {osf_dir_url}: {response.status_code}")

    metadata = response.json()
    
    leaves = []
    branches = []

    for item in metadata["data"]:
        if item["attributes"]["kind"] == "file":

            metadata = {
                "name": item["attributes"]["materialized_path"].strip("/"),
                "url": item["links"]["download"],
                "checksum": ":".join(["md5", item["attributes"]["extra"]["hashes"]["md5"]])
            }
            leaves.append(metadata)
            
        elif item["attributes"]["kind"] == "folder":
            branch_url = item["relationships"]["files"]["links"]["related"]["href"]
            branches.append(branch_url)

    return leaves, branches

def walk_osf_directory_fetch_files(osf_dir_url, file_metadata = []):
    """
    Recursively walk through an OSF directory and fetch file metadata.
    Kinda slow - this is a blocking function. The walk_osf_directory_fetch_files_concurrent
    function should be preferred for large directories.
    """
    leaves, branches = fetch_osf_leaves_branches(osf_dir_url)

    for leaf in leaves:
        file_metadata.append(leaf)
    
    for branch in branches:
        walk_osf_directory_fetch_files(branch, file_metadata)

    return file_metadata

def walk_osf_directory_fetch_files_concurrent(start_url, max_workers=10):
    """
    Recursively walk through an OSF directory tree in parallel to fetch all file metadata.
    """
    file_metadata = []
    visited = set()
    url_queue = Queue()
    metadata_lock = Lock()
    visited_lock = Lock()

    url_queue.put(start_url)

    def worker():
        while not url_queue.empty():
            try:
                url = url_queue.get_nowait()
            except:
                return
            try:
                leaves, branches = fetch_osf_leaves_branches(url)

                with metadata_lock:
                    file_metadata.extend(leaves)

                for branch_url in branches:
                    with visited_lock:
                        if branch_url not in visited:
                            visited.add(branch_url)
                            url_queue.put(branch_url)
            finally:
                url_queue.task_done()

    # Mark the start URL as visited
    visited.add(start_url)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for _ in range(max_workers):
            executor.submit(worker)

        # Block until all tasks are done
        url_queue.join()

    return file_metadata

### Similar to OSF datasets (see above), OpenNeuro datasets must be queried hierarchically to find all downloadable files within
### sub-directories. The following functions implement logic to walk the OpenNeuro snapshot structure and collect downloadable 
### files alongside their relative paths.

def get_snapshot_files(dataset_id, tag="1.0.0", tree_id=None):
    """
    Returns a GraphQL query and variables to retrieve files from a snapshot.
    If tree_id is provided, it queries the contents of a directory.
    """
    if tree_id:
        query = """
        query($datasetId: ID!, $tag: String!, $tree: String!) {
          snapshot(datasetId: $datasetId, tag: $tag) {
            files(tree: $tree) {
              id
              key
              filename
              urls
              size
              directory
              annexed
            }
          }
        }
        """
        variables = {"datasetId": dataset_id, "tag": tag, "tree": tree_id}
    else:
        query = """
        query($datasetId: ID!, $tag: String!) {
          snapshot(datasetId: $datasetId, tag: $tag) {
            files {
              id
              key
              filename
              urls
              size
              directory
              annexed
            }
          }
        }
        """
        variables = {"datasetId": dataset_id, "tag": tag}

    return query, variables

def doi_to_downloadables_openneuro(doi, endpoint="https://openneuro.org/crn/graphql"):
    
    """
    Recursively collect links to downloadable files from an OpenNeuro DOI.
    Returns a list of dicts with keys: name, url, checksum.

    Example doi string format: "10.18112/openneuro.ds004703.v1.1.0"
    """

    # Extract dataset ID and version tag from the DOI
    pattern = r"^.+/openneuro\.(ds\d+)\.v(\d+\.\d+\.\d+)$"
    match = re.match(pattern, doi)
    if not match:
        raise ValueError("DOI format is incorrect. Expected format: '10.18112/openneuro.dsXXXX.vX.X.X'")
    openneuro_id, tag = match.groups()

    query, variables = get_snapshot_files(openneuro_id, tag)
    response = requests.post(
        endpoint,
        json={"query": query, "variables": variables},
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()


    leaves, branches = [], []
    for file in response.json()["data"]["snapshot"]["files"]:
        if file["directory"]:
            branches.append({
                "name": file["filename"],
                "id": file["id"],
                "dirname": ""  # root level
            })
        else:
            leaves.append({
                "name": file["filename"],
                "url": file["urls"][0] if file["urls"] else None,
                "checksum": "sha1:" + file["key"] if file["key"] else None
            })

    for branch in branches:
        leaves.extend(walk_openneuro_branch(branch, openneuro_id, tag, endpoint))

    return leaves

def walk_openneuro_branch(branch, dataset_id, tag, endpoint):
    """
    Recursively walk a branch (subdirectory) and return all file metadata inside.
    """
    query, variables = get_snapshot_files(dataset_id, tag, tree_id=branch["id"])
    response = requests.post(
        endpoint,
        json={"query": query, "variables": variables},
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()

    leaves, branches_next = [], []
    for file in response.json()["data"]["snapshot"]["files"]:
        full_path = os.path.join(branch["dirname"], branch["name"], file["filename"])
        if file["directory"]:
            branches_next.append({
                "name": file["filename"],
                "id": file["id"],
                "dirname": os.path.join(branch["dirname"], branch["name"])
            })
        else:
            leaves.append({
                "name": full_path,
                "url": file["urls"][0] if file["urls"] else None,
                "checksum": "sha1:" + file["key"] if file["key"] else None
            })

    for sub_branch in branches_next:
        leaves.extend(walk_openneuro_branch(sub_branch, dataset_id, tag, endpoint))

    return leaves

### DSpace helpers
### UMD Drum is a DSpace repository, and we could use the corresponding API to get download links to the dataset files.
### At present, an access token is required to use the API, which we do not have. Therefore, we are web-scraping the HTML
### page for the DOI (see above).

def drum_doi_to_uuid(doi):
    """
    Resolve a DOI and extract the DRUM UUID from the redirected URL.

    Args:
        doi (str): A DOI string (e.g., '10.13016/M2599Z52H')

    Returns:
        str: The UUID of the DRUM item.
    """
    doi_url = f"https://doi.org/{doi}"
    try:
        response = requests.get(doi_url, allow_redirects=True)
        final_url = response.url
        parsed = urlparse(final_url)
        if "items" in parsed.path:
            uuid = parsed.path.split("/")[-1]
            return uuid
        else:
            raise ValueError("UUID not found in the redirected URL.")
    except Exception as e:
        raise RuntimeError(f"Failed to resolve DOI: {e}")
    
def doi_to_downloadables_dspace_api(doi, dspace_server="https://api.drum.lib.umd.edu"):
    """
    Get a list of downloadable files from a DSpace DOI.

    Example doi string format: "10.13016/M2599Z52H"

    NOTE drum requires authentication to access the API... we can just scrape the html instead I guess.
    """

    # Resolve the DOI to get the UUID
    uuid = drum_doi_to_uuid(doi)

    # Construct the URL for the DSpace item
    dspace_api_url = f"{dspace_server}/server/api/"

    bitstreams_url = f"https://api.drum.lib.umd.edu/server/api/core/bitstreams/{uuid}"

    response = requests.get(bitstreams_url)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve bitstreams: {response.status_code}")
    
    bitstreams = response.json()['_embedded']['bitstreams']

    # Step 3: Extract file names and download URLs
    file_data = []
    for bitstream in bitstreams:
        file_info = {
            "name": bitstream['name'],
            "url": f"{dspace_api_url}/core/bitstreams/{bitstream['uuid']}/content"
        }
        file_data.append(file_info)

    return file_data