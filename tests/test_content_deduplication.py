"""Tests for content-based image/video download de-duplication."""
import os

from media_downloader import _move_to_download_path_if_unique, app


def test_duplicate_content_is_removed_while_other_files_still_move(tmp_path):
    download_root = tmp_path / "downloads"
    nested = download_root / "old"
    nested.mkdir(parents=True)
    (nested / "existing.mp4").write_bytes(b"same video bytes")
    temp_duplicate = tmp_path / "temp-duplicate"
    temp_unique = tmp_path / "temp-unique"
    temp_duplicate.write_bytes(b"same video bytes")
    temp_unique.write_bytes(b"another video")

    previous_save_path = app.save_path
    app.save_path = str(download_root)
    try:
        duplicate = _move_to_download_path_if_unique(
            str(temp_duplicate), str(download_root / "duplicate.mp4")
        )
        unique = _move_to_download_path_if_unique(
            str(temp_unique), str(download_root / "unique.mp4")
        )
    finally:
        app.save_path = previous_save_path

    assert duplicate == os.path.join(str(nested), "existing.mp4")
    assert not temp_duplicate.exists()
    assert not (download_root / "duplicate.mp4").exists()
    assert unique is None
    assert (download_root / "unique.mp4").read_bytes() == b"another video"
