import os
import time
import hashlib
import requests

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm


class DataDownloader:
    """
    A class to download files from URLs with optional checksum verification and progress bar.
    """

    def __init__(self, download_dir, max_workers=1, retries=3, skip_existing=True, verify_checksum=True):
        """
        Initialize the DataDownloader.

        Parameters:
        - download_dir (str): Directory to save downloaded files.
        - max_workers (int): Number of parallel download workers. If None, defaults to 5 times the number of processors.
        - retries (int): Number of retries for failed downloads.
        - skip_existing (bool): Skip files that already exist and match the expected checksum.
        """
        self.download_dir = download_dir
        self.max_workers = max_workers
        self.retries = retries
        self.skip_existing = skip_existing
        self.verify_checksum = verify_checksum
        os.makedirs(download_dir, exist_ok=True)

    def _checksum_matches(self, file_path, expected_checksum):
        """
        Check if a file matches the expected checksum.

        Parameters:
        - file_path (str): Path to the file.
        - expected_checksum (str): Expected hash, optionally prefixed with algorithm (e.g., 'md5:abcd', 'sha256:abcd').

        Returns:
        - bool: True if checksum matches, False otherwise.
        """
        if ':' in expected_checksum:
            algo, expected = expected_checksum.split(':', 1)
        else:
            algo, expected = 'md5', expected_checksum

        try:
            hash_func = getattr(hashlib, algo.lower())()
        except AttributeError:
            raise ValueError(f"Unsupported checksum algorithm: {algo}")

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest() == expected.lower()

    def _download_one(self, url, destination, expected_checksum=None):
        """
        Download a single file with retries, optional checksum validation, and progress bar.

        Parameters:
        - url (str): URL of the file to download.
        - destination (str or Path): Local file path where the file will be saved.
        - expected_checksum (str, optional): Expected checksum to verify integrity, e.g. "md5:abcd1234".

        Returns:
        - str: Status message indicating success, skip, or failure.
        """
        if self.skip_existing and os.path.exists(destination):
            if expected_checksum is None or self._checksum_matches(destination, expected_checksum):
                return f"Skipped (exists): {os.path.basename(destination)}"
            else:
                print(f"Checksum mismatch. Re-downloading: {os.path.basename(destination)}")

        attempt = 0
        while attempt <= self.retries:
            try:
                response = requests.get(url, stream=True, timeout=(30, None))
                if response.status_code == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    with open(destination, 'wb') as f, tqdm(
                        desc=f"Downloading {os.path.basename(destination)}",
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        leave=False
                    ) as bar:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            bar.update(len(chunk))
                    if self.verify_checksum and expected_checksum and not self._checksum_matches(destination, expected_checksum):
                        raise Exception("Checksum mismatch after download.")
                    return f"Downloaded: {os.path.basename(destination)}"
                else:
                    raise Exception(f"HTTP {response.status_code}")
            except Exception as e:
                attempt += 1
                if attempt > self.retries:
                    return f"Failed: {os.path.basename(destination)} ({e})"
                time.sleep(2 ** attempt)

    def download_batch(self, file_metadata, parallel=True):
        """
        Download a batch of files.

        Parameters:
        - file_metadata (list of dict): Each dict should have keys:
            - 'url': URL of the file.
            - 'name': Filename or relative path to save the file as.
            - 'checksum' (optional): Expected MD5 checksum, e.g. "md5:abcd1234".
        - parallel (bool): Whether to download files in parallel.
        """
        tasks = []

        for each_file_metadata in file_metadata:
            filename = each_file_metadata["name"]
            destination = Path(self.download_dir) / Path(filename)
            url = each_file_metadata["url"]
            expected_checksum = each_file_metadata.get("checksum")
            if expected_checksum is None:
                print(f"Warning: No checksum provided for {filename}.")

            if not os.path.exists(destination.parent):
                os.makedirs(destination.parent, exist_ok=True)

            # Skip check here before queueing
            if self.skip_existing and destination.exists():
                if expected_checksum is None or self._checksum_matches(destination, expected_checksum):
                    print(f"Skipped (exists): {filename}")
                    continue
                else:
                    print(f"Checksum mismatch. Re-downloading: {filename}")

            tasks.append((url, destination, expected_checksum))

        results = []

        if parallel and self.max_workers > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._download_one, url, dest, chksum): (url, dest)
                    for url, dest, chksum in tasks
                }
                for future in as_completed(futures):
                    results.append(future.result())
        else:
            for url, dest, chksum in tasks:
                results.append(self._download_one(url, dest, chksum))

        self._print_summary(results)

    def _print_summary(self, results):
        """
        Print a summary of the download session.

        Parameters:
        - results (list of str): Status messages from each download attempt.
        """
        print("\nDownload Summary:")
        for result in results:
            print(" -", result)