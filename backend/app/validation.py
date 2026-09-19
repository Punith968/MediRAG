"""Input validation helpers for MediRAG uploads."""

from fastapi import HTTPException

ALLOWED_EXTENSIONS = {
    "text": {".pdf", ".txt"},
    "image": {".png", ".jpg", ".jpeg"},
    "audio": {".mp3", ".wav", ".m4a"},
}
MAX_FILE_SIZE = 20 * 1024 * 1024


def validate_file(filename: str, file_size: int) -> None:
    """Validate an uploaded file's extension and size."""
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=(
                "File too large. Maximum size is 20MB, "
                f"got {file_size / (1024 * 1024):.1f}MB"
            ),
        )

    parts = (filename or "").replace("..", ".").split(".")
    ext = "." + parts[-1].lower() if len(parts) > 1 else ""
    all_allowed = set().union(*ALLOWED_EXTENSIONS.values())

    if ext not in all_allowed:
        allowed_list = ", ".join(sorted(all_allowed))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Allowed formats: {allowed_list}",
        )
