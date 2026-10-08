"""Turns an uploaded file into Feature rows in the database."""
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app import models
from app.services.parser import ParsingError, crs_label, read_geodata

logger = logging.getLogger(__name__)


def process_file(db: Session, record: models.UploadedFile) -> models.UploadedFile:
    record.status = models.FileStatus.PROCESSING
    db.commit()

    try:
        gdf = read_geodata(Path(record.stored_path), record.file_type)
        file_crs = crs_label(gdf.crs)

        # to_json gives us clean, JSON-safe geometry + properties (handles NaN, dates...)
        geojson = json.loads(gdf.to_json(drop_id=True))

        features = []
        for index, (gj_feature, shapely_geom) in enumerate(
            zip(geojson["features"], gdf.geometry)
        ):
            if shapely_geom is None or shapely_geom.is_empty:
                geom_type = "None"
            else:
                geom_type = shapely_geom.geom_type

            features.append(
                models.Feature(
                    file_id=record.id,
                    feature_index=index,
                    geometry_type=geom_type,
                    geometry=gj_feature["geometry"],
                    crs=file_crs,
                    properties=gj_feature["properties"] or {},
                )
            )

        db.add_all(features)
        record.feature_count = len(features)
        record.crs = file_crs
        record.status = models.FileStatus.COMPLETED
        record.error_message = None
        db.commit()

    except ParsingError as exc:
        db.rollback()
        record.status = models.FileStatus.FAILED
        record.error_message = str(exc)
        db.commit()
    except Exception:
        # anything unexpected - log the details, give the client a short message
        logger.exception("Unexpected error while processing file %s", record.id)
        db.rollback()
        record.status = models.FileStatus.FAILED
        record.error_message = "Unexpected error while processing the file."
        db.commit()

    db.refresh(record)
    return record