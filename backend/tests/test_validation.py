import pytest
from fastapi import HTTPException

from app.validation import MAX_FILE_SIZE, validate_file


@pytest.mark.parametrize("filename", ["report.pdf", "notes.txt", "scan.png", "photo.jpg", "voice.mp3"])
def test_accepts_supported_file_types(filename):
    validate_file(filename, 1024)


def test_rejects_unsupported_extension():
    with pytest.raises(HTTPException) as exc:
        validate_file("payload.exe", 1024)

    assert exc.value.status_code == 400
    assert "Unsupported file format" in exc.value.detail


def test_rejects_oversized_file():
    with pytest.raises(HTTPException) as exc:
        validate_file("report.pdf", MAX_FILE_SIZE + 1)

    assert exc.value.status_code == 400
    assert "File too large" in exc.value.detail


def test_empty_filename_is_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_file("", 1024)

    assert exc.value.status_code == 400
    assert "Unsupported file format" in exc.value.detail
