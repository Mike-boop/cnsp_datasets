import os
import time
import random
import threading
import hashlib
import requests

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm


class DataDownloader:
    """
    A class to download files from URLs with optional checksum verification and progress bar.
    """

    def __init__(self, download_dir, max_workers=1, retries=10, skip_existing=True, verify_checksum=True, read_timeout=15):
        """
        Initialize the DataDownloader.

        Parameters:
        - download_dir (str): Directory to save downloaded files.
        - max_workers (int): Number of parallel download workers. If None, defaults to 5 times the number of processors.
        - retries (int): Number of retries for failed downloads.
        - skip_existing (bool): Skip files that already exist with the expected size
          (and checksum, if verify_checksum is set).
        - verify_checksum (bool): Verify checksums after download and for existing files.
        - read_timeout (float): Seconds to wait for the server to send more data before the
          attempt is abandoned and retried. This bounds stalls, not total download time.
        """
        self.download_dir = download_dir
        self.max_workers = max_workers
        self.retries = retries
        self.skip_existing = skip_existing
        self.verify_checksum = verify_checksum
        self.timeout = (30, read_timeout)  # (connect, read)
        self._local = threading.local()
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

    def _session(self):
        """Return this thread's requests.Session, so connections are reused across files."""
        session = getattr(self._local, "session", None)
        if session is None:
            session = self._local.session = requests.Session()
        return session

    def _is_complete(self, file_path, expected_size=None, expected_checksum=None):
        """
        Check whether an existing file matches what we expect to download.

        Compares the size first (cheap; catches truncated files), and only hashes the
        file if verify_checksum is enabled. With neither a size nor checksum
        verification available, an existing file is assumed complete.
        """
        if expected_size is not None and os.path.getsize(file_path) != expected_size:
            return False
        if self.verify_checksum and expected_checksum:
            return self._checksum_matches(file_path, expected_checksum)
        return True

    @staticmethod
    def _response_size(response):
        """Size of the file being served, or None if the server doesn't say (or compresses it)."""
        if "content-encoding" in response.headers:
            return None  # content-length counts compressed bytes, not what we write
        length = response.headers.get("content-length")
        return int(length) if length else None

    def _download_one(self, url, destination, expected_checksum=None, expected_size=None):
        """
        Download a single file with retries, optional checksum validation, and progress bar.

        Parameters:
        - url (str): URL of the file to download.
        - destination (str or Path): Local file path where the file will be saved.
        - expected_checksum (str, optional): Expected checksum to verify integrity, e.g. "md5:abcd1234".
        - expected_size (int, optional): Expected size in bytes. If omitted, the response's
          content-length is used to check existing files.

        Returns:
        - str: Status message indicating success, skip, or failure.
        """
        name = os.path.basename(destination)

        # with a known size, existing files can be checked without contacting the server
        if self.skip_existing and expected_size is not None and os.path.exists(destination):
            if self._is_complete(destination, expected_size, expected_checksum):
                return f"Skipped (exists): {name}"
            tqdm.write(f"Incomplete or mismatched. Re-downloading: {name}")

        attempt = 0
        while attempt <= self.retries:
            try:
                with self._session().get(url, stream=True, timeout=self.timeout) as response:
                    if response.status_code != 200:
                        raise Exception(f"HTTP {response.status_code}")
                    total_size = self._response_size(response)

                    # otherwise use the response headers; the body is never read if we skip
                    if self.skip_existing and expected_size is None and os.path.exists(destination):
                        if self._is_complete(destination, total_size, expected_checksum):
                            return f"Skipped (exists): {name}"
                        tqdm.write(f"Incomplete or mismatched. Re-downloading: {name}")

                    written = 0
                    with open(destination, 'wb') as f, tqdm(
                        desc=f"Downloading {name}",
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        leave=False
                    ) as bar:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            written += len(chunk)
                            bar.update(len(chunk))

                if total_size is not None and written != total_size:
                    raise Exception(f"Incomplete download ({written} of {total_size} bytes).")
                if self.verify_checksum and expected_checksum and not self._checksum_matches(destination, expected_checksum):
                    raise Exception("Checksum mismatch after download.")
                return f"Downloaded: {name}"
            except Exception as e:
                attempt += 1
                if attempt > self.retries:
                    tqdm.write(f"Failed: {name} ({type(e).__name__}: {e})")
                    return f"Failed: {name} ({type(e).__name__}: {e})"
                # capped exponential backoff with jitter; the Radboud WebDAV server returns
                # spurious 404s under load, so failures are usually transient
                time.sleep(min(2 ** attempt, 60) + random.uniform(0, 1))

    def download_batch(self, file_metadata, parallel=True):
        """
        Download a batch of files.

        Parameters:
        - file_metadata (list of dict): Each dict should have keys:
            - 'url': URL of the file.
            - 'name': Filename or relative path to save the file as.
            - 'checksum' (optional): Expected checksum, e.g. "md5:abcd1234" or "sha256:...".
            - 'size' (optional): Expected size in bytes; lets existing files be checked offline.
        - parallel (bool): Whether to download files in parallel.

        Existing files (with skip_existing) are checked inside the workers, so a large
        batch starts downloading immediately instead of first hashing every file on disk.
        """
        tasks = []

        for each_file_metadata in file_metadata:
            filename = each_file_metadata["name"]
            destination = Path(self.download_dir) / Path(filename)
            url = each_file_metadata["url"]
            expected_checksum = each_file_metadata.get("checksum")
            expected_size = each_file_metadata.get("size")
            if expected_checksum is None:
                print(f"Warning: No checksum provided for {filename}.")

            if not os.path.exists(destination.parent):
                os.makedirs(destination.parent, exist_ok=True)

            tasks.append((url, destination, expected_checksum, expected_size))

        results = []
        counts = {"downloaded": 0, "skipped": 0, "failed": 0}

        # overall bar pinned at the top; per-file bars take the free positions below it
        with tqdm(total=len(tasks), desc="Total", unit="file", position=0) as overall:

            def record(result):
                results.append(result)
                key = result.split(":", 1)[0].split(" ", 1)[0].lower()  # "Skipped (exists): x" -> "skipped"
                if key in counts:
                    counts[key] += 1
                overall.set_postfix(counts, refresh=False)
                overall.update(1)

            if parallel and self.max_workers > 1:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(self._download_one, *task): task
                        for task in tasks
                    }
                    for future in as_completed(futures):
                        record(future.result())
            else:
                for task in tasks:
                    record(self._download_one(*task))

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