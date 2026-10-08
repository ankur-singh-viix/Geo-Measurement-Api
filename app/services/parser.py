"""Reads Shapefile (.zip) and KML files into a GeoDataFrame."""
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio

MAX_UNZIPPED_MB = 200


class ParsingError(Exception):
    """Raised when a file can't be read as valid geospatial data."""


def crs_label(crs) -> str | None:
    """Short readable name for a CRS, e.g. 'EPSG:4326'."""
    if crs is None:
        return None
    authority = crs.to_authority()
    if authority:
        return f"{authority[0]}:{authority[1]}"
    return crs.name[:50]


def _extract_zip(zip_path: Path) -> Path:
    """Extract the zip next to itself and return the extraction folder."""
    target = zip_path.parent / "extracted"
    target.mkdir(exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path) as zf:
            total = sum(info.file_size for info in zf.infolist())
            if total > MAX_UNZIPPED_MB * 1024 * 1024:
                raise ParsingError("Zip file is too large once extracted.")

            for info in zf.infolist():
                # guard against "zip slip" (../../ paths inside the archive)
                dest = (target / info.filename).resolve()
                if not str(dest).startswith(str(target.resolve())):
                    raise ParsingError("Zip contains an unsafe file path.")
            zf.extractall(target)
    except zipfile.BadZipFile:
        raise ParsingError("The uploaded file is not a valid zip archive.")

    return target


def read_shapefile_zip(zip_path: Path) -> gpd.GeoDataFrame:
    folder = _extract_zip(zip_path)
    # ignore macOS junk folders that sometimes end up in zips
    shp_files = sorted(
        p for p in folder.rglob("*.shp") if "__MACOSX" not in p.parts
    )
    if not shp_files:
        raise ParsingError("No .shp file found inside the zip.")

    # if there are several shapefiles we only read the first one
    shp = shp_files[0]
    try:
        gdf = gpd.read_file(shp, engine="pyogrio")
    except Exception as exc:
        raise ParsingError(f"Could not read shapefile '{shp.name}': {exc}")

    if gdf.crs is None:
        raise ParsingError(
            "Shapefile has no CRS (.prj file missing), so measurements would be unreliable."
        )
    return gdf


def read_kml(kml_path: Path) -> gpd.GeoDataFrame:
    try:
        layers = pyogrio.list_layers(kml_path)
    except Exception as exc:
        raise ParsingError(f"Could not read KML file: {exc}")

    if len(layers) == 0:
        raise ParsingError("KML file does not contain any layers.")

    # KML folders show up as separate layers, so read all of them
    frames = []
    for layer_name, _geom_type in layers:
        try:
            frames.append(gpd.read_file(kml_path, layer=layer_name, engine="pyogrio"))
        except Exception:
            continue  # skip a broken layer rather than failing the whole file

    frames = [f for f in frames if len(f) > 0]
    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")  # KML spec: always WGS84
    return gdf


def read_geodata(path: Path, file_type: str) -> gpd.GeoDataFrame:
    if file_type == "shapefile":
        return read_shapefile_zip(path)
    if file_type == "kml":
        return read_kml(path)
    raise ParsingError(f"Unsupported file type: {file_type}")