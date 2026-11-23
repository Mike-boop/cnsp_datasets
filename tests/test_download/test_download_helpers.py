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
                    "size": 1,
                    "extra": {"hashes": {"md5": md5}},
                },
                "links": {"download": url},
            })
        for folder_url in folders:
            data.append({
                "attributes": {"kind": "folder"},
                "relationships": {"files": {"links": {"related": {"href": folder_url}}}},
            })
        return {"data": data, "links": {"next": None}}

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
            r.json.return_value = pages[url.split("?")[0]]
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
            visited.append(url.split("?")[0])
            r = MagicMock()
            r.json.return_value = pages[url.split("?")[0]]
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


class TestDryadAuth:
    def _responses(self):
        dataset = MagicMock(status_code=200)
        dataset.json.return_value = {"_links": {"stash:version": {"href": "/api/v2/versions/1"}}}
        files = MagicMock(status_code=200)
        files.json.return_value = {"_embedded": {"stash:files": [{
            "path": "a.zip", "size": 10, "digest": "abc", "digestType": "md5",
            "_links": {"self": {"href": "/api/v2/files/7"}},
        }]}}
        return [dataset, files]

    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_files_carry_size_checksum_and_token(self, mock_get, monkeypatch):
        for var in ("DRYAD_CLIENT_ID", "DRYAD_CLIENT_SECRET"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("DRYAD_TOKEN", "tok")
        mock_get.side_effect = self._responses()
        [f] = download_helpers.doi_to_downloadables_dryad("10.5061/dryad.x")
        assert f == {"name": "a.zip", "url": "https://datadryad.org/api/v2/files/7/download", "size": 10,
                     "checksum": "md5:abc", "headers": {"Authorization": "Bearer tok"}}

    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_without_credentials_lists_files_and_explains(self, mock_get, monkeypatch, capsys):
        for var in ("DRYAD_TOKEN", "DRYAD_CLIENT_ID", "DRYAD_CLIENT_SECRET"):
            monkeypatch.delenv(var, raising=False)
        mock_get.side_effect = self._responses()
        [f] = download_helpers.doi_to_downloadables_dryad("10.5061/dryad.x")
        assert f["headers"] is None and f["checksum"] == "md5:abc"
        out = capsys.readouterr().out
        assert "DRYAD_TOKEN" in out and "skip_existing=True" in out and "a.zip" in out

    @patch("cnsp_datasets.download.download_helpers.requests.post")
    def test_client_credentials_exchanged_for_token(self, mock_post, monkeypatch):
        monkeypatch.delenv("DRYAD_TOKEN", raising=False)
        monkeypatch.setenv("DRYAD_CLIENT_ID", "id")
        monkeypatch.setenv("DRYAD_CLIENT_SECRET", "secret")
        mock_post.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"access_token": "t2"}))
        assert download_helpers._dryad_token() == "t2"
        assert mock_post.call_args.kwargs["data"]["grant_type"] == "client_credentials"

    @patch("cnsp_datasets.download.download_helpers.requests.post")
    def test_client_credentials_preferred_and_fresh_per_call(self, mock_post, monkeypatch):
        monkeypatch.setenv("DRYAD_TOKEN", "stale")
        monkeypatch.setenv("DRYAD_CLIENT_ID", "id")
        monkeypatch.setenv("DRYAD_CLIENT_SECRET", "secret")
        mock_post.side_effect = [MagicMock(status_code=200, json=MagicMock(return_value={"access_token": t}))
                                 for t in ("t1", "t2")]
        assert [download_helpers._dryad_token(), download_helpers._dryad_token()] == ["t1", "t2"]

    @patch("cnsp_datasets.download.download_helpers.requests.post")
    def test_failed_token_request_raises(self, mock_post, monkeypatch):
        monkeypatch.setenv("DRYAD_CLIENT_ID", "id")
        monkeypatch.setenv("DRYAD_CLIENT_SECRET", "bad")
        mock_post.return_value = MagicMock(status_code=401, text="invalid_client")
        with pytest.raises(Exception, match="401"):
            download_helpers._dryad_token()


class TestScidbListing:
    def test_listing_file(self, tmp_path):
        listing = tmp_path / "scidb_files.json"  # an absolute path overrides the datasets directory
        listing.write_text(json.dumps({"files": [{"path": "PassiveListening/sub-01.zip", "size_bytes": 3,
                                                   "md5": "abc", "download_url": "https://scidb/x"}]}))
        assert download_helpers.listing_to_downloadables_scidb(str(listing)) == [
            {"name": "PassiveListening/sub-01.zip", "url": "https://scidb/x", "size": 3, "checksum": "md5:abc"}]


class TestDrum:
    def _json(self, payload):
        return MagicMock(status_code=200, json=MagicMock(return_value=payload))

    @staticmethod
    def _bitstream(name, uuid):
        return {"name": name, "sizeBytes": 5, "checkSum": {"checkSumAlgorithm": "MD5", "value": "abc"},
                "_links": {"content": {"href": f"https://api/core/bitstreams/{uuid}/content"}}}

    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_original_bundle_all_pages(self, mock_get):
        bundles = {"_embedded": {"bundles": [
            {"name": "THUMBNAIL", "_links": {"bitstreams": {"href": "https://api/thumbs"}}},
            {"name": "ORIGINAL", "_links": {"bitstreams": {"href": "https://api/orig"}}},
        ]}}
        page1 = {"_embedded": {"bitstreams": [self._bitstream("S01.zip", "u1")]},
                 "_links": {"next": {"href": "https://api/orig?page=1&size=100"}}}
        page2 = {"_embedded": {"bitstreams": [self._bitstream("S02.zip", "u2")]}, "_links": {}}
        mock_get.side_effect = [self._json(bundles), self._json(page1), self._json(page2)]

        files = download_helpers.id_to_downloadables_drum("item-uuid")

        assert [f["name"] for f in files] == ["S01.zip", "S02.zip"]
        assert files[0] == {"name": "S01.zip", "url": "https://api/core/bitstreams/u1/content", "size": 5,
                            "checksum": "md5:abc"}
        assert "items/item-uuid/bundles" in mock_get.call_args_list[0].args[0]
        assert mock_get.call_args_list[1].args[0] == "https://api/orig?size=100"


class TestEprints:
    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_public_files_with_md5(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"documents": [
            {"security": "public", "files": [{"filename": "a.bdf", "filesize": "12", "hash_type": "MD5",
                                              "hash": "abc", "uri": "https://e/id/file/1"}]},
            {"security": "staffonly", "files": [{"filename": "b.zip", "filesize": "3", "uri": "https://e/id/file/2"}]},
        ]}))

        files = download_helpers.id_to_downloadables_eprints("438737")

        assert files == [{"name": "a.bdf", "url": "https://e/id/file/1", "size": 12, "checksum": "md5:abc"}]
        assert "/cgi/export/eprint/438737/JSON/" in mock_get.call_args.args[0]


class TestGitlabLfs:
    @patch("cnsp_datasets.download.download_helpers.requests.Session")
    def test_lfs_pointers_give_size_and_sha256(self, mock_session):
        api = "https://lab.org/api/v4/projects/grp%2Fproj"
        tree = [{"type": "tree", "path": "sub-01", "id": "t"},
                {"type": "blob", "path": "README.md", "id": "b1"},
                {"type": "blob", "path": "sub-01/a_meg.fif", "id": "b2"}]
        responses = {
            f"{api}/repository/tree?recursive=true&per_page=100&ref=v1": MagicMock(
                status_code=200, json=MagicMock(return_value=tree), links={}),
            f"{api}/repository/files/.gitattributes/raw?ref=v1": MagicMock(
                status_code=200, text="*.fif filter=lfs diff=lfs merge=lfs -text\n"),
            f"{api}/repository/blobs/b2/raw": MagicMock(
                status_code=200, text="version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 42\n"),
        }
        mock_session.return_value.get.side_effect = lambda url, timeout: responses[url]

        files = download_helpers.id_to_downloadables_gitlab_lfs("lab.org/grp/proj@v1")

        assert files == [
            {"name": "README.md", "url": f"{api}/repository/files/README.md/raw?ref=v1&lfs=true", "checksum": None},
            {"name": "sub-01/a_meg.fif", "url": f"{api}/repository/files/sub-01%2Fa_meg.fif/raw?ref=v1&lfs=true",
             "checksum": "sha256:abc", "size": 42},
        ]


class TestHuggingface:
    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_token_sent_with_listing_and_files(self, mock_get, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "tok")
        mock_get.return_value = MagicMock(status_code=200, links={}, json=MagicMock(return_value=[
            {"type": "directory", "path": "data"},
            {"type": "file", "path": "data/a b.parquet", "size": 5, "lfs": {"oid": "abc"}},
        ]))

        [f] = download_helpers.id_to_downloadables_huggingface("org/repo@v1")

        assert f == {"name": "repo/data/a b.parquet",
                     "url": "https://huggingface.co/datasets/org/repo/resolve/v1/data/a%20b.parquet",
                     "size": 5, "checksum": "sha256:abc", "headers": {"Authorization": "Bearer tok"}}
        assert mock_get.call_args.kwargs["headers"] == {"Authorization": "Bearer tok"}

    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_no_token_no_header(self, mock_get, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        mock_get.return_value = MagicMock(status_code=200, links={}, json=MagicMock(return_value=[
            {"type": "file", "path": "README.md", "size": 1}]))

        [f] = download_helpers.id_to_downloadables_huggingface("org/repo")

        assert f["headers"] is None and f["checksum"] is None


class TestRadboudRdr:
    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_dccn_path_and_credentials(self, mock_get, monkeypatch):
        monkeypatch.setenv("RADBOUD_USERNAME", "u")
        monkeypatch.setenv("RADBOUD_PASSWORD", "p")
        mock_get.return_value = MagicMock(status_code=200, text="abc sub-01/a b.wav\ndef README.txt\n")

        files = download_helpers.id_to_downloadables_radboud_rdr("dccn/DSC_1_v1")

        assert mock_get.call_args.args[0] == "https://webdav.data.ru.nl/dccn/DSC_1_v1/MANIFEST.txt"
        assert files[0] == {"name": "sub-01/a b.wav", "url": "https://webdav.data.ru.nl/dccn/DSC_1_v1/sub-01/a%20b.wav",
                            "checksum": "sha256:abc", "headers": {"Authorization": "Basic dTpw"}}

    @patch("cnsp_datasets.download.download_helpers.requests.get")
    def test_public_collection_without_credentials(self, mock_get, monkeypatch):
        monkeypatch.delenv("RADBOUD_USERNAME", raising=False)
        mock_get.return_value = MagicMock(status_code=200, text="abc f.wav\n")
        [f] = download_helpers.id_to_downloadables_radboud_rdr("corpus_v1")
        assert f["url"] == "https://webdav.data.ru.nl/cls/corpus_v1/f.wav" and f["headers"] is None
