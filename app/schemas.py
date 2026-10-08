from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import FileStatus


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    feature_count: int
    crs: str | None
    status: FileStatus
    error_message: str | None = None
    created_at: datetime
