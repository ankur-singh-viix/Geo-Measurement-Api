from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import processor, storage

router = APIRouter(prefix="/api/files", tags=["files"])


def _get_file_or_404(db: Session, file_id: str) -> models.UploadedFile:
    record = db.get(models.UploadedFile, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return record


@router.post("/", response_model=schemas.FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a zipped shapefile (.zip) or a .kml file and process it."""
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

    # processed synchronously for now, status tells the client how it went
    return processor.process_file(db, record)


@router.get("/{file_id}/", response_model=schemas.FileOut)
def get_file(file_id: str, db: Session = Depends(get_db)):
    return _get_file_or_404(db, file_id)


@router.get("/{file_id}/features/", response_model=list[schemas.FeatureOut])
def get_features(file_id: str, db: Session = Depends(get_db)):
    """Raw features (geometry + attributes) extracted from the file."""
    _get_file_or_404(db, file_id)
    stmt = (
        select(models.Feature)
        .where(models.Feature.file_id == file_id)
        .order_by(models.Feature.feature_index)
    )
    return db.scalars(stmt).all()