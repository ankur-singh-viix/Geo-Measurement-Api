from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import storage

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/", response_model=schemas.FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a zipped shapefile (.zip) or a .kml file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing.")

    file_type = storage.get_file_type(file.filename)
    saved_path = await storage.save_upload(file)

    record = models.UploadedFile(
        filename=file.filename,
        stored_path=str(saved_path),
        file_type=file_type,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # TODO (next step): parse the file and extract features
    return record


@router.get("/{file_id}/", response_model=schemas.FileOut)
def get_file(file_id: str, db: Session = Depends(get_db)):
    record = db.get(models.UploadedFile, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return record
