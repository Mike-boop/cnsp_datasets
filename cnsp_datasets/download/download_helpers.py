import asyncio
import base64
import os
import json
import re
import gzip
import shutil
import zipfile
import tarfile
import requests
import httpx

from fnmatch import fnmatch
from pathlib import Path
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
            file_path = os.path.join(dirpath, filename)
            extracted_dir = None

            if filename.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(dirpath)
                print(f"Extracted {filename} to {dirpath}")
                os.remove(file_path)
                extracted_dir = os.path.join(dirpath, os.path.splitext(filename)[0])

            elif filename.endswith('.tar.gz'):
                with tarfile.open(file_path, 'r:*') as tar_ref:
                    tar_ref.extractall(dirpath)
                print(f"Extracted {filename} to {dirpath}")
                os.remove(file_path)
                extracted_dir = os.path.join(dirpath, filename.replace('.tar.gz', ''))

            elif filename.endswith('.tar'):
                with tarfile.open(file_path, 'r:*') as tar_ref:
                    tar_ref.extractall(dirpath)
                print(f"Extracted {filename} to {dirpath}")
                os.remove(file_path)
                extracted_dir = os.path.join(dirpath, os.path.splitext(filename)[0])

            elif filename.endswith('.gz') and not filename.endswith('.nii.gz'):
                output_file = os.path.splitext(file_path)[0]
                with gzip.open(file_path, 'rb') as f_in:
                    with open(output_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                print(f"Decompressed {filename} to {output_file}")
                os.remove(file_path)

            if recursive and extracted_dir and os.path.isdir(extracted_dir):
                extract_archives(extracted_dir, recursive=True)

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

def _dryad_token():
    """
    Bearer token for Dryad file downloads, which require one (metadata does not), or None if not configured.

    Set DRYAD_TOKEN, or DRYAD_CLIENT_ID and DRYAD_CLIENT_SECRET from a Dryad API account (https://datadryad.org/api),
    which are exchanged for a short-lived token here.
    """
    if os.environ.get("DRYAD_TOKEN"):
        return os.environ["DRYAD_TOKEN"]
    client_id, secret = os.environ.get("DRYAD_CLIENT_ID"), os.environ.get("DRYAD_CLIENT_SECRET")
    if not (client_id and secret):
        return None
    response = requests.post("https://datadryad.org/oauth/token", timeout=60, data={
        "grant_type": "client_credentials", "client_id": client_id, "client_secret": secret,
    })
    if response.status_code != 200:
        raise Exception(f"Dryad token request failed: {response.status_code} {response.text[:200]}")
    return response.json()["access_token"]


def doi_to_downloadables_dryad(doi):
    """
    Get a list of downloadable files from a Dryad DOI, with sizes, md5 checksums and the Authorization header the
    downloads need (see _dryad_token).

    Without credentials the files are still listed, with a warning: downloads will fail (HTTP 401) unless the files
    were placed in the download directory by hand and the download runs with skip_existing=True (they are then
    checked against Dryad's size and md5 and skipped).

    Example doi string format: "10.5061/dryad.1234567"
    """
    dryad_server = "https://datadryad.org"
    response = requests.get(f"{dryad_server}/api/v2/datasets/{quote(f'doi:{doi}', safe='')}", timeout=60)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for DOI {doi}: {response.status_code}")
    version = response.json()["_links"]["stash:version"]["href"]

    files_metadata_url = f"{dryad_server}{version}/files"
    files_metadata_response = requests.get(files_metadata_url, timeout=60)
    if files_metadata_response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for files request {files_metadata_url}: {files_metadata_response.status_code}")

    token = _dryad_token()
    headers = {"Authorization": f"Bearer {token}"} if token else None
    files = [
        {
            "name": entry["path"],
            "url": f"{dryad_server}{entry['_links']['self']['href']}/download",
            "size": entry.get("size"),
            "checksum": f"{entry['digestType']}:{entry['digest']}" if entry.get("digest") else None,
            "headers": headers,
        }
        for entry in files_metadata_response.json()["_embedded"]["stash:files"]
    ]
    if token is None:
        print(
            f"Warning: Dryad needs an API token to download files. Either set DRYAD_TOKEN (or DRYAD_CLIENT_ID and "
            f"DRYAD_CLIENT_SECRET; https://datadryad.org/api), or download these files from "
            f"https://datadryad.org/dataset/doi:{doi} into the download directory and run with skip_existing=True: "
            + ", ".join(f["name"] for f in files)
        )
    return files

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

def id_to_downloadables_drum(item_uuid, api="https://api.drum.lib.umd.edu/server/api"):
    """
    Files of a UMD DRUM (DSpace 7) item from its public REST API, e.g. "79afc7aa-560d-442d-b201-ab63e7f1e69f" (the id
    in https://drum.lib.umd.edu/items/<id>). Only the ORIGINAL bundle (not thumbnails or extracted text).
    """
    response = requests.get(f"{api}/core/items/{item_uuid}/bundles", timeout=60)
    response.raise_for_status()
    original = next(b for b in response.json()["_embedded"]["bundles"] if b["name"] == "ORIGINAL")

    bitstreams = []
    url = original["_links"]["bitstreams"]["href"] + "?size=100"
    while url:  # the bitstream listing is paginated
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        page = response.json()
        bitstreams += page["_embedded"]["bitstreams"]
        url = page["_links"].get("next", {}).get("href")
    return [
        {
            "name": b["name"],
            "url": b["_links"]["content"]["href"],
            "size": b["sizeBytes"],
            "checksum": f"{b['checkSum']['checkSumAlgorithm'].lower()}:{b['checkSum']['value']}",
        }
        for b in bitstreams
    ]


def id_to_downloadables_eprints(eprint_id, server="https://eprints.soton.ac.uk"):
    """
    Public files of an EPrints record (e.g. the University of Southampton repository) from its JSON export, e.g.
    "438737" (the id in https://eprints.soton.ac.uk/id/eprint/<id>).

    Southampton serves the files behind an Anubis proof-of-work page (HTTP 401 to scripts, 2026-11): download them in
    a browser into the download directory and run with skip_existing=True, which checks them against the listed sizes
    and md5s.
    """
    response = requests.get(f"{server}/cgi/export/eprint/{eprint_id}/JSON/eprint-{eprint_id}.js", timeout=60)
    response.raise_for_status()
    return [
        {
            "name": f["filename"],
            "url": f["uri"],
            "size": int(f["filesize"]),
            "checksum": f"{f['hash_type'].lower()}:{f['hash']}" if f.get("hash") else None,
        }
        for doc in response.json().get("documents", []) if doc.get("security") == "public"
        for f in doc.get("files", [])
    ]

def id_to_downloadables_deepblue(id):
    """
    Get a list of downloadable files from a DeepBlue dataset ID.

    Example id string format: "bn999738r"

    Note: I think there is no mapping between the dataset ID and the DOI.
    """

    dataset_url = f"https://deepblue.lib.umich.edu/data/concern/data_sets/{id}.json"

    response = requests.get(dataset_url)

    if response.status_code == 200:
        metadata = response.json()
    else:
        # Deep Blue may refuse scripted metadata requests: fall back to a copy saved next to the adaptor
        saved = [p for p in Path(__file__).parents[1].glob(f"datasets/*/{id}.json") if p.stat().st_size]
        if not saved:
            raise Exception(
                f"Failed to retrieve metadata for dataset ID {id}: {response.status_code}, and no saved copy "
                f"datasets/<name>/{id}.json (save it from {dataset_url} in a browser)."
            )
        metadata = json.loads(saved[0].read_text())
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

def id_to_downloadables_nemar(identifier):
    """
    Files of a NEMAR dataset from its published manifest.

    identifier: "<dataset>@<version>", e.g. "nm000180@v1.1.3" (pinned; "nm000180" alone means "latest").
    Annexed files carry sha256 checksums; git-tracked files only git blob hashes, which are not file hashes, so
    they get none.
    """
    dataset, _, version = identifier.partition("@")
    response = requests.get(f"https://data.nemar.org/{dataset}/{version or 'latest'}/manifest.json", timeout=60)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve NEMAR manifest for {identifier}: {response.status_code}")
    return [
        {
            "name": f["path"],
            "url": f["url"],
            "size": f["size"],
            "checksum": f"sha256:{f['checksum']}" if f["checksum_algorithm"] == "sha256" else None,
        }
        for f in response.json()
    ]

### Open Science Framework datasets must be queried hierarchically to find the downloadable files within each sub-directory.
### The tree is walked level by level: all known directories at each depth are fetched concurrently, and any
### subdirectories they contain are collected and fetched at the next level.

def doi_to_downloadables_osf(osf_id):
    """
    Get a list of downloadable files from an OSF project ID.

    Example id string format: "ag3kj"

    Returns a list of dictionaries with keys: name, url, checksum.
    """
    start_url = f"https://api.osf.io/v2/nodes/{osf_id}/files/osfstorage/"
    return asyncio.run(_walk_osf_async(start_url))


def fetch_osf_leaves_branches(osf_dir_url):
    """
    Synchronously fetch files and subdirectory URLs from one OSF directory page.
    Kept for testing and one-off use; prefer doi_to_downloadables_osf for full trees.
    """
    response = requests.get(osf_dir_url)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve metadata for URL {osf_dir_url}: {response.status_code}")

    leaves, branches = [], []
    for item in response.json()["data"]:
        if item["attributes"]["kind"] == "file":
            leaves.append({
                "name": item["attributes"]["materialized_path"].strip("/"),
                "url": item["links"]["download"],
                "checksum": "md5:" + item["attributes"]["extra"]["hashes"]["md5"],
            })
        elif item["attributes"]["kind"] == "folder":
            branches.append(item["relationships"]["files"]["links"]["related"]["href"])

    return leaves, branches


def walk_osf_directory_fetch_files(osf_dir_url, file_metadata=None):
    """
    Synchronous serial walk — kept for testing.
    Use doi_to_downloadables_osf for production (async, much faster).
    """
    if file_metadata is None:
        file_metadata = []
    leaves, branches = fetch_osf_leaves_branches(osf_dir_url)
    file_metadata.extend(leaves)
    for branch in branches:
        walk_osf_directory_fetch_files(branch, file_metadata)
    return file_metadata


async def _fetch_osf_dir_async(client, url):
    """Async version of fetch_osf_leaves_branches; follows the listing's pages (OSF returns 10 items per page by
    default) and backs off when rate-limited (HTTP 429)."""
    leaves, branches = [], []
    url = url + ("&" if "?" in url else "?") + "page[size]=100"
    while url:
        for attempt in range(8):
            response = await client.get(url)
            if response.status_code != 429:
                break
            await asyncio.sleep(2 ** attempt)
        response.raise_for_status()
        page = response.json()
        for item in page["data"]:
            if item["attributes"]["kind"] == "file":
                leaves.append({
                    "name": item["attributes"]["materialized_path"].strip("/"),
                    "url": item["links"]["download"],
                    "size": item["attributes"]["size"],
                    "checksum": "md5:" + item["attributes"]["extra"]["hashes"]["md5"],
                })
            elif item["attributes"]["kind"] == "folder":
                branches.append(item["relationships"]["files"]["links"]["related"]["href"])
        url = page["links"].get("next")
    return leaves, branches


async def _walk_osf_async(start_url):
    """
    Walk an OSF directory tree concurrently, level by level.

    Each level: all known directory URLs are fetched in parallel with asyncio.gather.
    Any subdirectories found become the next level. Continues until no directories remain.
    """
    all_files = []
    pending = [start_url]
    visited = {start_url}

    async with httpx.AsyncClient(timeout=30) as client:
        while pending:
            results = await asyncio.gather(
                *[_fetch_osf_dir_async(client, url) for url in pending]
            )
            pending = []
            for leaves, branches in results:
                all_files.extend(leaves)
                for branch in branches:
                    if branch not in visited:
                        visited.add(branch)
                        pending.append(branch)

    return all_files

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
    Collect links to downloadable files from an OpenNeuro DOI.
    Returns a list of dicts with keys: name, url, checksum.

    Example doi string format: "10.18112/openneuro.ds004703.v1.1.0"
    """
    pattern = r"^.+/openneuro\.(ds\d+)\.v(\d+\.\d+\.\d+)$"
    match = re.match(pattern, doi)
    if not match:
        raise ValueError("DOI format is incorrect. Expected format: '10.18112/openneuro.dsXXXX.vX.X.X'")
    openneuro_id, tag = match.groups()

    return asyncio.run(_walk_openneuro_async(openneuro_id, tag, endpoint))


OPENNEURO_RETRIES = 6


async def _fetch_openneuro_dir_async(client, endpoint, dataset_id, tag, branch):
    """
    Fetch one OpenNeuro directory node and return (leaves, sub_branches).
    branch is a dict with keys: id, name, dirname.
    Pass branch=None for the root level (no tree_id in the query).
    """
    query, variables = get_snapshot_files(dataset_id, tag, tree_id=branch["id"] if branch else None)
    for attempt in range(OPENNEURO_RETRIES):  # the GraphQL endpoint returns transient 502s under load
        try:
            async with OPENNEURO_LIMIT:
                response = await client.post(
                    endpoint,
                    json={"query": query, "variables": variables},
                    headers={"Content-Type": "application/json"},
                )
            if response.status_code < 500:
                break
        except httpx.TransportError:
            if attempt == OPENNEURO_RETRIES - 1:
                raise
        await asyncio.sleep(2 ** attempt)
    response.raise_for_status()

    leaves, sub_branches = [], []
    for file in response.json()["data"]["snapshot"]["files"]:
        if branch:
            full_path = os.path.join(branch["dirname"], branch["name"], file["filename"])
            parent_dirname = os.path.join(branch["dirname"], branch["name"])
        else:
            full_path = file["filename"]
            parent_dirname = ""

        if file["directory"]:
            sub_branches.append({
                "name": file["filename"],
                "id": file["id"],
                "dirname": parent_dirname,
            })
        else:
            leaves.append({
                "name": full_path,
                "url": file["urls"][0] if file["urls"] else None,
                "size": file["size"],
                "checksum": None,  # the API exposes no file hashes
            })

    return leaves, sub_branches


async def _walk_openneuro_async(dataset_id, tag, endpoint):
    """
    Walk an OpenNeuro snapshot tree concurrently, level by level.

    Starts with the root listing, then fans out across all subdirectories
    in parallel at each level until no directories remain.
    """
    global OPENNEURO_LIMIT
    OPENNEURO_LIMIT = asyncio.Semaphore(8)  # bounded fan-out; created inside the running event loop
    all_leaves = []

    async with httpx.AsyncClient(timeout=30) as client:
        # Root fetch (no branch dict, no tree_id)
        root_leaves, pending = await _fetch_openneuro_dir_async(
            client, endpoint, dataset_id, tag, branch=None
        )
        all_leaves.extend(root_leaves)

        while pending:
            results = await asyncio.gather(
                *[_fetch_openneuro_dir_async(client, endpoint, dataset_id, tag, b)
                  for b in pending]
            )
            pending = []
            for leaves, sub_branches in results:
                all_leaves.extend(leaves)
                pending.extend(sub_branches)

    return all_leaves

def resolve_doi(doi):
    url = f"https://doi.org/{doi}"
    resp = requests.head(url, allow_redirects=True, timeout=10)
    return resp.url


def id_to_downloadables_radboud_rdr(id, rdr_server="https://webdav.data.ru.nl"):
    """
    Files of a Radboud Data Repository collection, from its MANIFEST.txt (sha256 per file).

    id: a public "cls" collection, e.g. "dutch_eeg_speech_register_corpus_dsc_807_v1", or a path with the
    collection type, e.g. "dccn/DSC_3011085.05_995_v1". Collections under a data use agreement (most "dccn" ones)
    need the downloading user's WebDAV credentials in RADBOUD_USERNAME and RADBOUD_PASSWORD (data.ru.nl account
    with the agreement accepted); the manifest itself is public.
    """
    data_root = f"{rdr_server}/{id if '/' in id else 'cls/' + id}"
    response = requests.get(f"{data_root}/MANIFEST.txt", timeout=30)
    response.raise_for_status()

    headers = None
    if os.environ.get("RADBOUD_USERNAME"):
        token = base64.b64encode(f"{os.environ['RADBOUD_USERNAME']}:{os.environ['RADBOUD_PASSWORD']}".encode())
        headers = {"Authorization": f"Basic {token.decode()}"}

    # each line is "<sha256> <path>"; split once so paths containing spaces survive
    entries = [line.split(maxsplit=1) for line in response.text.strip().splitlines() if line.strip()]
    return [{"name": name, "url": f"{data_root}/{quote(name)}", "checksum": f"sha256:{checksum}", "headers": headers}
            for checksum, name in entries]


def id_to_downloadables_huggingface(repo):
    """
    Files of a Hugging Face dataset repo, e.g. "pnpl/LibriBrain" ("<repo>@<revision>" pins a revision), named
    "<repo name>/<path>" so that several repos can share one download directory.

    LFS files carry sha256 checksums; small git-tracked files only git blob hashes, so they get none.
    """
    repo, _, revision = repo.partition("@")
    revision = revision or "main"
    url = f"https://huggingface.co/api/datasets/{repo}/tree/{revision}?recursive=true"
    files = []
    while url:  # the tree listing is paginated through Link headers
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            raise Exception(f"Failed to list Hugging Face dataset {repo}: {response.status_code}")
        files += [f for f in response.json() if f["type"] == "file"]
        url = response.links.get("next", {}).get("url")
    return [
        {
            "name": f"{repo.split('/')[-1]}/{f['path']}",
            "url": f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{quote(f['path'])}",
            "size": f["size"],
            "checksum": f"sha256:{f['lfs']['oid']}" if f.get("lfs") else None,
        }
        for f in files
    ]


def listing_to_downloadables_scidb(listing):
    """
    Files of a Science Data Bank (scidb.cn) dataset, from a listing shipped with the adaptor, e.g.
    "chen2026/scidb_files.json" (relative to cnsp_datasets/datasets): the site lists files only to a browser.
    """
    path = Path(__file__).parents[1] / "datasets" / listing
    files = json.loads(path.read_text(encoding="utf-8"))["files"]
    return [{"name": f["path"], "url": f["download_url"], "size": f["size_bytes"], "checksum": f"md5:{f['md5']}"}
            for f in files]


def id_to_downloadables_gitlab_lfs(project):
    """
    Files of a public GitLab repository whose data are in Git LFS, given as "<host>/<group>/.../<project>", e.g.
    "data.anc.plus.ac.at/bids-datasets/auditory/yc_audiobook_vocoding" ("<project>@<ref>" pins a branch, tag or
    commit; default: the default branch).

    LFS files (matched by the repository's .gitattributes) carry the sha256 and size from their pointer files;
    small git-tracked files get none. Files are served by the raw-file API, which resolves LFS objects.
    """
    project, _, ref = project.partition("@")
    host, path = project.split("/", 1)
    api = f"https://{host}/api/v4/projects/{quote(path, safe='')}"
    session = requests.Session()

    def get(url):
        response = session.get(url, timeout=60)
        if response.status_code != 200:
            raise Exception(f"Failed to list GitLab project {project}: {response.status_code} for {url}")
        return response

    ref = ref or get(api).json()["default_branch"]
    raw = f"{api}/repository/files/{{}}/raw?ref={quote(ref)}"
    blobs, url = [], f"{api}/repository/tree?recursive=true&per_page=100&ref={quote(ref)}"
    while url:  # the tree listing is paginated through Link headers
        response = get(url)
        blobs += [e for e in response.json() if e["type"] == "blob"]
        url = response.links.get("next", {}).get("url")

    attributes = session.get(raw.format(".gitattributes"), timeout=60)
    lfs_patterns = [line.split()[0] for line in (attributes.text if attributes.status_code == 200 else "").splitlines()
                    if "filter=lfs" in line]

    def is_lfs(file_path):
        # a gitattributes pattern without a slash matches the basename, with one the path from the root
        return any(fnmatch(file_path if "/" in pat else file_path.rsplit("/", 1)[-1], pat.lstrip("/"))
                   for pat in lfs_patterns)

    files = []
    for blob in blobs:
        entry = {"name": blob["path"], "url": raw.format(quote(blob["path"], safe="")) + "&lfs=true",
                 "checksum": None}
        if is_lfs(blob["path"]):
            pointer = get(f"{api}/repository/blobs/{blob['id']}/raw").text
            if pointer.startswith("version https://git-lfs"):
                fields = dict(line.split(" ", 1) for line in pointer.strip().splitlines())
                entry.update(size=int(fields["size"]), checksum=fields["oid"])
        files.append(entry)
    return files
