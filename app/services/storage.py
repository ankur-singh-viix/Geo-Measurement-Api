import re
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

CHUNK_SIZE = 1024 * 1024  # 1 MB


def get_file_type(filename: str) -> str:
    """Return 'shapefile' or 'kml' based on extension, or raise 400."""
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload a .zip (shapefile) or .kml file.",
        )
    return "shapefile" if ext == ".zip" else "kml"


def _safe_name(filename: str) -> str:
    # strip any directory part and weird characters from the client supplied name
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


async def save_upload(upload: UploadFile) -> Path:
    """Stream the upload to disk in chunks and enforce the size limit."""
    folder = settings.upload_dir / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / _safe_name(upload.filename)

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    written = 0

    with open(dest, "wb") as out:
        while chunk := await upload.read(CHUNK_SIZE):
            written += len(chunk)
            if written > max_bytes:
                break
            out.write(chunk)

    if written > max_bytes:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {settings.max_upload_size_mb} MB.",
        )

    if written == 0:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    return dest
