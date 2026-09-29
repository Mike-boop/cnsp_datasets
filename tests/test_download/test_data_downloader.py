import hashlib
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from cnsp_datasets.download.data_downloader import DataDownloader


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def downloader(tmp_dir):
    return DataDownloader(tmp_dir, max_workers=1, retries=2, skip_existing=True, verify_checksum=True)


def _write_file(path: Path, content: bytes) -> str:
    path.write_bytes(content)
    return hashlib.md5(content).hexdigest()


def _make_response(content=b"data", status=200, content_length=None):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"content-length": str(content_length or len(content))}
    resp.iter_content = MagicMock(side_effect=lambda chunk_size: iter([content]))
    resp.__enter__.return_value = resp
    return resp


@pytest.fixture
def mock_get():
    """Patch requests.Session so every session's .get is this one mock."""
    with patch("cnsp_datasets.download.data_downloader.requests.Session") as session_cls:
        yield session_cls.return_value.get


# ── _checksum_matches ─────────────────────────────────────────────────────────

class TestChecksumMatches:

    def test_md5_prefix(self, downloader, tmp_path):
        content = b"hello world"
        path = tmp_path / "f.bin"
        digest = _write_file(path, content)
        assert downloader._checksum_matches(str(path), f"md5:{digest}")

    def test_md5_no_prefix_defaults_to_md5(self, downloader, tmp_path):
        content = b"hello world"
        path = tmp_path / "f.bin"
        digest = _write_file(path, content)
        assert downloader._checksum_matches(str(path), digest)

    def test_sha256(self, downloader, tmp_path):
        content = b"hello world"
        path = tmp_path / "f.bin"
        path.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        assert downloader._checksum_matches(str(path), f"sha256:{digest}")

    def test_mismatch_returns_false(self, downloader, tmp_path):
        path = tmp_path / "f.bin"
        path.write_bytes(b"actual content")
        assert not downloader._checksum_matches(str(path), "md5:deadbeef00000000")

    def test_unknown_algorithm_raises(self, downloader, tmp_path):
        path = tmp_path / "f.bin"
        path.write_bytes(b"x")
        with pytest.raises(ValueError, match="Unsupported"):
            downloader._checksum_matches(str(path), "crc32:abcd")


# ── _download_one ─────────────────────────────────────────────────────────────

class TestDownloadOne:

    def test_successful_download(self, mock_get, downloader, tmp_path):
        content = b"file content"
        mock_get.return_value = _make_response(content)
        dest = str(tmp_path / "out.bin")

        result = downloader._download_one("http://example.com/f", dest)

        assert "Downloaded" in result
        assert Path(dest).read_bytes() == content

    def test_skip_existing_valid_checksum(self, mock_get, downloader, tmp_path):
        content = b"existing"
        dest = tmp_path / "out.bin"
        digest = _write_file(dest, content)
        resp = _make_response(content)
        mock_get.return_value = resp

        result = downloader._download_one("http://example.com/f", str(dest), f"md5:{digest}")

        assert "Skipped" in result
        resp.iter_content.assert_not_called()  # only the headers were used

    def test_skip_existing_with_known_size_makes_no_request(self, mock_get, downloader, tmp_path):
        content = b"existing"
        dest = tmp_path / "out.bin"
        digest = _write_file(dest, content)

        result = downloader._download_one("http://example.com/f", str(dest), f"md5:{digest}", len(content))

        assert "Skipped" in result
        mock_get.assert_not_called()

    def test_redownload_truncated_file(self, mock_get, tmp_dir, tmp_path):
        # no checksum verification: the size mismatch alone must trigger a re-download
        downloader = DataDownloader(tmp_dir, retries=0, skip_existing=True, verify_checksum=False)
        content = b"the full file content"
        dest = tmp_path / "out.bin"
        dest.write_bytes(content[:5])
        mock_get.return_value = _make_response(content)

        result = downloader._download_one("http://example.com/f", str(dest))

        assert "Downloaded" in result
        assert dest.read_bytes() == content

    def test_size_match_does_not_hash_without_verify(self, mock_get, tmp_dir, tmp_path):
        downloader = DataDownloader(tmp_dir, retries=0, skip_existing=True, verify_checksum=False)
        dest = tmp_path / "out.bin"
        dest.write_bytes(b"12345")

        with patch.object(downloader, "_checksum_matches") as checksum:
            result = downloader._download_one("http://example.com/f", str(dest), "md5:whatever", 5)

        assert "Skipped" in result
        checksum.assert_not_called()

    def test_redownload_on_checksum_mismatch(self, mock_get, downloader, tmp_path):
        content = b"new content"
        dest = tmp_path / "out.bin"
        _write_file(dest, b"old content")  # same size, so only the checksum differs
        mock_get.return_value = _make_response(content)
        new_digest = hashlib.md5(content).hexdigest()

        result = downloader._download_one("http://example.com/f", str(dest), f"md5:{new_digest}")

        assert "Downloaded" in result
        mock_get.assert_called_once()

    @patch("cnsp_datasets.download.data_downloader.time.sleep")
    def test_short_stream_is_retried(self, mock_sleep, mock_get, downloader, tmp_path):
        # server promises 100 bytes but the stream ends after 4
        mock_get.return_value = _make_response(b"data", content_length=100)
        dest = str(tmp_path / "out.bin")

        result = downloader._download_one("http://example.com/f", dest)

        assert "Failed" in result and "Incomplete" in result
        assert mock_get.call_count == 3

    @patch("cnsp_datasets.download.data_downloader.time.sleep")
    def test_retries_on_http_error(self, mock_sleep, mock_get, downloader, tmp_path):
        mock_get.return_value = _make_response(status=503)
        dest = str(tmp_path / "out.bin")

        result = downloader._download_one("http://example.com/f", dest)

        assert "Failed" in result
        # retries=2 means 3 total attempts (initial + 2 retries)
        assert mock_get.call_count == 3

    @patch("cnsp_datasets.download.data_downloader.time.sleep")
    def test_retry_uses_exponential_backoff(self, mock_sleep, mock_get, downloader, tmp_path):
        mock_get.return_value = _make_response(status=500)
        dest = str(tmp_path / "out.bin")

        downloader._download_one("http://example.com/f", dest)

        sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
        # Each sleep should be 2^attempt plus up to 1 s of jitter
        assert [int(s) for s in sleep_args] == [2, 4]

    def test_uses_connect_and_read_timeout(self, mock_get, downloader, tmp_path):
        mock_get.return_value = _make_response()
        dest = str(tmp_path / "out.bin")

        downloader._download_one("http://example.com/f", dest)

        _, kwargs = mock_get.call_args
        # (connect, read): the read timeout bounds stalls between chunks, not total time
        connect_t, read_t = kwargs["timeout"]
        assert connect_t > 0
        assert read_t == downloader.timeout[1]

    def test_session_reused_within_thread(self, downloader, tmp_path):
        with patch("cnsp_datasets.download.data_downloader.requests.Session") as session_cls:
            session_cls.return_value.get.return_value = _make_response()
            downloader._download_one("http://example.com/a", str(tmp_path / "a.bin"))
            downloader._download_one("http://example.com/b", str(tmp_path / "b.bin"))

        session_cls.assert_called_once()


# ── download_batch ────────────────────────────────────────────────────────────

class TestDownloadBatch:

    def test_downloads_all_files(self, mock_get, downloader, tmp_path):
        mock_get.return_value = _make_response(b"x")

        files = [
            {"url": "http://example.com/a", "name": "a.bin"},
            {"url": "http://example.com/b", "name": "b.bin"},
        ]
        downloader.download_batch(files, parallel=False)

        assert (tmp_path / "a.bin").exists()
        assert (tmp_path / "b.bin").exists()

    def test_skips_existing_files(self, mock_get, downloader, tmp_path):
        content = b"cached"
        dest = tmp_path / "cached.bin"
        digest = _write_file(dest, content)

        files = [{"url": "http://example.com/cached", "name": "cached.bin",
                  "checksum": f"md5:{digest}", "size": len(content)}]
        downloader.download_batch(files, parallel=False)

        mock_get.assert_not_called()

    def test_warns_when_no_checksum(self, mock_get, capsys, downloader, tmp_path):
        mock_get.return_value = _make_response(b"x")

        downloader.download_batch([{"url": "http://example.com/f", "name": "f.bin"}], parallel=False)

        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Warning" in captured.err


# ── download log ──────────────────────────────────────────────────────────────

def _read_log(path):
    header, *rows = Path(path).read_text().splitlines()
    return header.split("\t"), [dict(zip(header.split("\t"), r.split("\t"))) for r in rows]


class TestDownloadLog:

    def test_logs_success_skip_and_failure(self, mock_get, downloader, tmp_path):
        content = b"cached"
        (tmp_path / "sub").mkdir()
        digest = _write_file(tmp_path / "sub" / "cached.bin", content)

        def get(url, **kwargs):
            if url.endswith("/bad"):
                return _make_response(status=404)
            return _make_response(b"x")
        mock_get.side_effect = get

        with patch("cnsp_datasets.download.data_downloader.time.sleep"):
            downloader.download_batch([
                {"url": "http://example.com/good", "name": "good.bin"},
                {"url": "http://example.com/cached", "name": "sub/cached.bin",
                 "checksum": f"md5:{digest}", "size": len(content)},
                {"url": "http://example.com/bad", "name": "bad.bin"},
            ], parallel=False)

        header, rows = _read_log(tmp_path / "download_log.tsv")
        assert header == ["timestamp", "status", "file", "url", "message"]
        by_file = {r["file"]: r for r in rows}
        assert by_file["good.bin"]["status"] == "downloaded"
        assert by_file[os.path.join("sub", "cached.bin")]["status"] == "skipped"
        assert by_file["bad.bin"]["status"] == "failed"
        assert by_file["bad.bin"]["url"] == "http://example.com/bad"
        assert "HTTP 404" in by_file["bad.bin"]["message"]

    def test_log_appends_across_runs(self, mock_get, downloader, tmp_path):
        mock_get.return_value = _make_response(b"x")
        files = [{"url": "http://example.com/f", "name": "f.bin"}]

        downloader.download_batch(files, parallel=False)
        downloader.download_batch(files, parallel=False)

        _, rows = _read_log(tmp_path / "download_log.tsv")
        assert len(rows) == 2

    def test_custom_log_path(self, mock_get, tmp_path):
        log_path = tmp_path / "logs" / "my_log.tsv"
        dl = DataDownloader(str(tmp_path / "data"), max_workers=1, retries=0, log_path=str(log_path))
        mock_get.return_value = _make_response(b"x")

        dl.download_batch([{"url": "http://example.com/f", "name": "f.bin"}], parallel=False)

        _, rows = _read_log(log_path)
        assert rows[0]["status"] == "downloaded"
        assert not (tmp_path / "data" / "download_log.tsv").exists()

    def test_parallel_logs_every_file(self, mock_get, tmp_path):
        dl = DataDownloader(str(tmp_path), max_workers=4, retries=0)
        mock_get.side_effect = lambda url, **kw: _make_response(b"x")

        dl.download_batch([{"url": f"http://example.com/{i}", "name": f"{i}.bin"} for i in range(10)])

        _, rows = _read_log(tmp_path / "download_log.tsv")
        assert sorted(r["file"] for r in rows) == sorted(f"{i}.bin" for i in range(10))
        assert all(r["url"] == f"http://example.com/{r['file'][:-4]}" for r in rows)
