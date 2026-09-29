import asyncio
import gzip
import json
import os
import tarfile
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cnsp_datasets.download import download_helpers


# ── extract_archives ──────────────────────────────────────────────────────────

class TestExtractArchives:

    def test_extracts_zip(self, tmp_path):
        inner = tmp_path / "inner.txt"
        inner.write_text("hello")
        zpath = tmp_path / "archive.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.write(inner, "inner.txt")
        inner.unlink()

        download_helpers.extract_archives(str(tmp_path))

        assert (tmp_path / "inner.txt").exists()
        assert not zpath.exists()

    def test_extracts_tar_gz(self, tmp_path):
        inner = tmp_path / "data.csv"
        inner.write_text("a,b,c")
        tpath = tmp_path / "archive.tar.gz"
        with tarfile.open(tpath, "w:gz") as tf:
            tf.add(inner, arcname="data.csv")
        inner.unlink()

        download_helpers.extract_archives(str(tmp_path))

        assert (tmp_path / "data.csv").exists()
        assert not tpath.exists()

    def test_extracts_gz_single_file(self, tmp_path):
        content = b"compressed data"
        gpath = tmp_path / "file.bin.gz"
        with gzip.open(gpath, "wb") as f:
            f.write(content)

        download_helpers.extract_archives(str(tmp_path))

        assert (tmp_path / "file.bin").read_bytes() == content
        assert not gpath.exists()

    def test_does_not_extract_nii_gz(self, tmp_path):
        nii = tmp_path / "brain.nii.gz"
        nii.write_bytes(b"fake nifti")

        download_helpers.extract_archives(str(tmp_path))

        assert nii.exists()

    def test_non_archive_files_untouched(self, tmp_path):
        mat = tmp_path / "data.mat"
        mat.write_bytes(b"matlab data")

        download_helpers.extract_archives(str(tmp_path))

        assert mat.exists()


# ── mutable default argument guard ───────────────────────────────────────────

class TestOSFWalkMutableDefault:

    def test_no_state_leaks_between_calls(self):
        """
        walk_osf_directory_fetch_files must not accumulate state across calls
        via a mutable default argument.
        """
        fake_leaves = [{"name": "f.txt", "url": "http://x.com/f", "checksum": "md5:abc"}]

        with patch.object(download_helpers, "fetch_osf_leaves_branches",
                          return_value=(fake_leaves, [])):
            first = download_helpers.walk_osf_directory_fetch_files("http://fake/")
            second = download_helpers.walk_osf_directory_fetch_files("http://fake/")

        assert len(first) == 1
        assert len(second) == 1


# ── Zenodo ────────────────────────────────────────────────────────────────────

class TestZenodo:

    def _mock_response(self, files):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"files": files}
        return resp

    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_returns_name_url_checksum(self, mock_get):
        mock_get.return_value = self._mock_response([
            {"key": "data.mat", "links": {"self": "http://zenodo.org/dl/data.mat"}, "checksum": "md5:abc123"},
        ])

        result = download_helpers.doi_to_downloadables_zenodo("10.5281/zenodo.1234567")

        assert len(result) == 1
        assert result[0]["name"] == "data.mat"
        assert result[0]["url"] == "http://zenodo.org/dl/data.mat"
        assert result[0]["checksum"] == "md5:abc123"

    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_raises_on_http_error(self, mock_get):
        resp = MagicMock()
        resp.status_code = 404
        mock_get.return_value = resp

        with pytest.raises(Exception, match="Failed"):
            download_helpers.doi_to_downloadables_zenodo("10.5281/zenodo.9999999")

    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_extracts_record_id_from_doi(self, mock_get):
        mock_get.return_value = self._mock_response([])
        download_helpers.doi_to_downloadables_zenodo("10.5281/zenodo.7778289")

        called_url = mock_get.call_args.args[0]
        assert "7778289" in called_url


# ── OpenNeuro DOI parsing ─────────────────────────────────────────────────────

class TestOpenneuro:

    def test_parses_doi_correctly(self):
        expected = [{"name": "README.md", "url": "http://s3.x/README.md", "checksum": "sha1:abc"}]

        async def mock_walk(dataset_id, tag, endpoint):
            assert dataset_id == "ds004703"
            assert tag == "1.1.0"
            return expected

        with patch.object(download_helpers, "_walk_openneuro_async", mock_walk):
            result = download_helpers.doi_to_downloadables_openneuro("10.18112/openneuro.ds004703.v1.1.0")

        assert result == expected

    def test_raises_on_bad_doi_format(self):
        with pytest.raises(ValueError, match="DOI format"):
            download_helpers.doi_to_downloadables_openneuro("10.18112/openneuro.BADFORMAT")


# ── Dryad error reporting ─────────────────────────────────────────────────────

class TestAsyncOSFWalk:

    def _osf_page(self, files=(), folders=()):
        """Build a minimal OSF API response dict."""
        data = []
        for name, url, md5 in files:
            data.append({
                "attributes": {
                    "kind": "file",
                    "materialized_path": f"/{name}",
                    "extra": {"hashes": {"md5": md5}},
                },
                "links": {"download": url},
            })
        for folder_url in folders:
            data.append({
                "attributes": {"kind": "folder"},
                "relationships": {"files": {"links": {"related": {"href": folder_url}}}},
            })
        return {"data": data}

    def test_single_level_no_subdirs(self):
        page = self._osf_page(files=[("data.mat", "http://osf.io/dl/data", "abc123")])

        async def fake_get(url, **kwargs):
            r = MagicMock()
            r.json.return_value = page
            r.raise_for_status = MagicMock()
            return r

        with patch_async_client(fake_get):
            result = asyncio.run(download_helpers._walk_osf_async("http://osf.io/root/"))

        assert len(result) == 1
        assert result[0]["name"] == "data.mat"
        assert result[0]["checksum"] == "md5:abc123"

    def test_two_level_tree(self):
        root_page = self._osf_page(
            files=[("root.txt", "http://osf.io/dl/root", "aaa")],
            folders=["http://osf.io/sub/"],
        )
        sub_page = self._osf_page(files=[("sub/child.mat", "http://osf.io/dl/child", "bbb")])

        pages = {
            "http://osf.io/root/": root_page,
            "http://osf.io/sub/": sub_page,
        }

        async def fake_get(url, **kwargs):
            r = MagicMock()
            r.json.return_value = pages[url]
            r.raise_for_status = MagicMock()
            return r

        with patch_async_client(fake_get):
            result = asyncio.run(download_helpers._walk_osf_async("http://osf.io/root/"))

        names = {f["name"] for f in result}
        assert names == {"root.txt", "sub/child.mat"}

    def test_does_not_revisit_directories(self):
        """A directory URL that appears in two places should only be fetched once."""
        visited = []

        root_page = self._osf_page(folders=["http://osf.io/dir/", "http://osf.io/dir/"])
        dir_page = self._osf_page(files=[("f.mat", "http://osf.io/dl/f", "ccc")])

        pages = {"http://osf.io/root/": root_page, "http://osf.io/dir/": dir_page}

        async def fake_get(url, **kwargs):
            visited.append(url)
            r = MagicMock()
            r.json.return_value = pages[url]
            r.raise_for_status = MagicMock()
            return r

        with patch_async_client(fake_get):
            asyncio.run(download_helpers._walk_osf_async("http://osf.io/root/"))

        assert visited.count("http://osf.io/dir/") == 1


def patch_async_client(fake_get):
    """Patch httpx.AsyncClient with a stub whose .get is fake_get."""
    mock_client = MagicMock()
    mock_client.get = fake_get

    async def async_enter(self):
        return mock_client

    async def async_exit(self, *args):
        pass

    mock_client.__aenter__ = async_enter
    mock_client.__aexit__ = async_exit
    return patch("httpx.AsyncClient", return_value=mock_client)


class TestDryad:

    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_reports_correct_status_on_files_endpoint_failure(self, mock_get):
        """The error message must use the failing response's status code, not the first response's."""
        dataset_resp = MagicMock()
        dataset_resp.status_code = 200
        dataset_resp.json.return_value = {
            "_links": {"stash:version": {"href": "v1"}}
        }

        files_resp = MagicMock()
        files_resp.status_code = 503

        mock_get.side_effect = [dataset_resp, files_resp]

        with pytest.raises(Exception) as exc_info:
            download_helpers.doi_to_downloadables_dryad("10.5061/dryad.abc")

        assert "503" in str(exc_info.value)
