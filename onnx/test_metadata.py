"""Assert-based self-check for read_id3v1 (no framework). Run: python onnx/test_metadata.py"""
import tempfile
from pathlib import Path

from inference import read_id3v1


def _make_id3v1_tag(title: str, artist: str, album: str, year: str, comment: str) -> bytes:
    def pad(text: str, size: int) -> bytes:
        return text.encode("latin-1")[:size].ljust(size, b"\x00")

    return b"TAG" + pad(title, 30) + pad(artist, 30) + pad(album, 30) + pad(year, 4) + pad(comment, 30) + b"\x00"


def test_reads_valid_id3v1_tag():
    tag = _make_id3v1_tag("My Title", "My Artist", "My Album", "1999", "hello")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(b"fake audio bytes" + tag)
        path = Path(f.name)

    result = read_id3v1(path)
    assert result == {
        "TITLE": "My Title",
        "ARTIST": "My Artist",
        "ALBUM": "My Album",
        "DATE": "1999",
        "COMMENT": "hello",
    }, result
    path.unlink()


def test_returns_none_without_tag_marker():
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(b"\x00" * 200)
        path = Path(f.name)

    assert read_id3v1(path) is None
    path.unlink()


if __name__ == "__main__":
    test_reads_valid_id3v1_tag()
    test_returns_none_without_tag_marker()
    print("ALL TESTS PASSED")
