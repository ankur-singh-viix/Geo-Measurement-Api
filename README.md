# Geospatial File Measurement API

A FastAPI backend that accepts a geospatial file (a zipped **Shapefile** or a **KML**),
extracts every feature from it and returns **area** (polygons) and **length** (lines)
in metric units.

Geometries are never measured in latitude/longitude degrees. Each feature is first
reprojected to the UTM zone it sits in, and the measurement is done there, in metres.

- **Framework:** FastAPI
- **Geospatial libraries:** GeoPandas, pyogrio (GDAL), Shapely, pyproj
- **Storage:** SQLite through SQLAlchemy 2.0
- **Tests:** pytest (35 tests)
- **Interactive API docs:** http://127.0.0.1:8000/docs (available once the server is running)

---

## Table of contents

1. [Setup](#setup)
2. [API](#api)
3. [Architecture](#architecture)
4. [Design decisions](#design-decisions)
5. [Testing](#testing)
6. [Known limitations](#known-limitations)
7. [What I learned](#what-i-learned)
8. [Future scope](#future-scope)

---

## Setup

**Requirements:** Python 3.10 or newer (developed on Python 3.13, Windows).

```bash
# 1. clone and enter the project
git clone <https://github.com/ankur-singh-viix/Geo-Measurement-Api>
cd geo-measurement-api

# 2. create and activate a virtual environment
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux

# 3. install dependencies
pip install -r requirements.txt

# 4. start the server
uvicorn app.main:app --reload
```

The API is now running at http://127.0.0.1:8000 and the Swagger UI is at
http://127.0.0.1:8000/docs.

The SQLite database (`geo_api.db`) and the `uploads/` folder are created automatically
on first start.

### Try it with the sample files

The `samples/` folder has a KML file ready to use. Two sample shapefiles can be generated
with a small script:

```bash
python scripts/make_sample_shapefile.py
```

This creates:

| File | CRS | What it is | Expected total area |
|---|---|---|---|
| `samples/sample.kml` | EPSG:4326 | 2 polygons, 1 line, 1 point (in two folders) | 33,647.581 m² / 609.274 m line |
| `samples/sample_plots_wgs84.zip` | EPSG:4326 | 2 polygons in lat/lon | 33,647.581 m² |
| `samples/sample_plots_utm.zip` | EPSG:32643 | a 100x100 m and a 50x200 m rectangle | exactly 20,000 m² |

Upload one in Swagger (`POST /api/files/` -> *Try it out* -> choose file -> *Execute*) or with curl:

```bash
curl -X POST http://127.0.0.1:8000/api/files/ -F "file=@samples/sample.kml"
```

> On Windows PowerShell use `curl.exe` instead of `curl`.

### Run the tests

```bash
pytest
```

### Configuration (optional)

Settings have sensible defaults. To change them, create a `.env` file in the project root:

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///geo_api.db` (project root) | SQLAlchemy database URL |
| `UPLOAD_DIR` | `uploads/` | where uploaded files are stored |
| `MAX_UPLOAD_SIZE_MB` | `50` | upload size limit |

---

## API

Base URL: `http://127.0.0.1:8000`

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/files/` | Upload and process a `.zip` (shapefile) or `.kml` |
| `GET` | `/api/files/{id}/` | File information and processing status |
| `GET` | `/api/files/{id}/features/` | Extracted features: index, geometry type, geometry, CRS, properties |
| `GET` | `/api/files/{id}/measurements/` | Area / length for every feature, plus totals |
| `GET` | `/health` | Health check |

### `POST /api/files/`

Uploads a file as `multipart/form-data` (field name: `file`) and processes it straight away.

```bash
curl -X POST http://127.0.0.1:8000/api/files/ -F "file=@samples/sample.kml"
```

**Response: `201 Created`**

```json
{
  "id": "d1c7ebd403dd",
  "filename": "sample.kml",
  "file_type": "kml",
  "feature_count": 4,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2026-10-08T07:19:32.742324"
}
```

`status` is one of `UPLOADED`, `PROCESSING`, `COMPLETED` or `FAILED`.

If the file is saved but cannot be read (for example a corrupt KML), the upload still
returns `201` with `"status": "FAILED"` and an `error_message`, so the client keeps the `id`:

```json
{
  "id": "6ce65d3e0905",
  "filename": "broken.kml",
  "file_type": "kml",
  "feature_count": 0,
  "crs": null,
  "status": "FAILED",
  "error_message": "Could not read KML file. Make sure it is a valid KML document.",
  "created_at": "2026-10-08T07:19:32.841395"
}
```

### `GET /api/files/{id}/`

```bash
curl http://127.0.0.1:8000/api/files/d1c7ebd403dd/
```

**Response: `200 OK`**

```json
{
  "id": "d1c7ebd403dd",
  "filename": "sample.kml",
  "file_type": "kml",
  "feature_count": 4,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2026-10-08T07:19:32.742324"
}
```

### `GET /api/files/{id}/features/`

Returns the raw features exactly as read from the file (geometry is GeoJSON in the
file's original CRS). Output below is shortened to two features.

```bash
curl http://127.0.0.1:8000/api/files/d1c7ebd403dd/features/
```

```json
[
  {
    "feature_index": 0,
    "geometry_type": "Polygon",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[77.59, 12.97], [77.591, 12.97], [77.591, 12.971], [77.59, 12.971], [77.59, 12.97]]]
    },
    "crs": "EPSG:4326",
    "properties": { "Name": "Plot A", "description": "Residential plot" }
  },
  {
    "feature_index": 3,
    "geometry_type": "Point",
    "geometry": { "type": "Point", "coordinates": [77.5905, 12.9705] },
    "crs": "EPSG:4326",
    "properties": { "Name": "Gate", "description": null }
  }
]
```

### `GET /api/files/{id}/measurements/`

```bash
curl http://127.0.0.1:8000/api/files/d1c7ebd403dd/measurements/
```

**Response: `200 OK`**

```json
{
  "file_id": "d1c7ebd403dd",
  "filename": "sample.kml",
  "feature_count": 4,
  "measured_count": 3,
  "total_area_sq_m": 33647.581,
  "total_length_m": 609.274,
  "units": { "area": "square_meters", "length": "meters" },
  "measurements": [
    {
      "feature_index": 0,
      "geometry_type": "Polygon",
      "source_crs": "EPSG:4326",
      "projected_crs": "EPSG:32643",
      "area_sq_m": 12016.97,
      "length_m": null,
      "note": null
    },
    {
      "feature_index": 1,
      "geometry_type": "Polygon",
      "source_crs": "EPSG:4326",
      "projected_crs": "EPSG:32643",
      "area_sq_m": 21630.611,
      "length_m": null,
      "note": null
    },
    {
      "feature_index": 2,
      "geometry_type": "LineString",
      "source_crs": "EPSG:4326",
      "projected_crs": "EPSG:32643",
      "area_sq_m": null,
      "length_m": 609.274,
      "note": null
    },
    {
      "feature_index": 3,
      "geometry_type": "Point",
      "source_crs": "EPSG:4326",
      "projected_crs": null,
      "area_sq_m": null,
      "length_m": null,
      "note": "No measurement is defined for Point."
    }
  ]
}
```

Points (and any unsupported or empty geometry) are returned with `null` measurements and an
explanation in `note`, instead of an error.

### Error responses

| Status | When | Example `detail` |
|---|---|---|
| `400` | wrong extension, empty file, missing filename | `Unsupported file type '.txt'. Upload a .zip (shapefile) or .kml file.` |
| `404` | unknown file id | `File not found.` |
| `409` | measurements requested for a file whose status is not `COMPLETED` | `File is not ready for measurements (status: FAILED).` |
| `413` | file larger than the size limit | `File too large. Max size is 50 MB.` |
| `422` | request body is malformed (no `file` field) | FastAPI validation error |

---

## Architecture

### Application structure

```
geo-measurement-api/
├── app/
│   ├── main.py                 # FastAPI app, logging, router registration
│   ├── config.py               # settings (env / .env)
│   ├── database.py             # SQLAlchemy engine and session
│   ├── models.py               # UploadedFile and Feature tables
│   ├── schemas.py              # Pydantic response models
│   ├── routers/
│   │   └── files.py            # the HTTP endpoints (thin, no geo logic)
│   └── services/
│       ├── storage.py          # validate extension, stream upload to disk
│       ├── parser.py           # read shapefile zip / KML into a GeoDataFrame
│       ├── processor.py        # orchestrates parse -> measure -> save
│       └── measurement.py      # CRS selection, reprojection, area / length
├── tests/                      # 35 tests
├── samples/                    # sample KML (+ generated sample shapefiles)
├── scripts/
│   └── make_sample_shapefile.py
├── uploads/                    # uploaded files (git-ignored)
└── requirements.txt
```

The code is split into layers so each part has one job: the **router** handles HTTP,
**services** hold the logic, and **models/schemas** describe the data. The geo code
does not know about FastAPI, which makes it easy to test on its own.

### File-processing flow

1. `POST /api/files/` receives the upload.
2. `storage.py` checks the extension (`.zip` or `.kml`, case-insensitive), streams the file to
   `uploads/<random-id>/` in 1 MB chunks, and rejects empty or oversized files (`400` / `413`).
   The filename is sanitised before it touches the disk.
3. A row is saved in `uploaded_files` with status `UPLOADED`.
4. `processor.process_file` sets the status to `PROCESSING` and calls `parser.py`:
   - **Shapefile:** the zip is checked for unsafe paths (zip-slip) and size, extracted, and the
     `.shp` is read. A shapefile with no `.prj` (no CRS) is rejected with a clear message.
   - **KML:** every layer (KML folders show up as layers in GDAL) is read and merged. KML is
     always WGS84, so EPSG:4326 is assumed if none is reported. Styling-only columns
     (`tessellate`, `extrude`, `drawOrder`...) are dropped.
5. For each feature the processor stores: index, geometry type, GeoJSON geometry, CRS and
   properties, and then runs the measurement (below).
6. All features are saved in one transaction and the file is marked `COMPLETED`
   (or `FAILED` with an `error_message` if parsing failed).

Errors never escape as a `500`: expected problems become a `FAILED` status with a readable
message, and unexpected ones are logged with the full traceback while the client only gets a
short generic message (so server paths are never exposed).

### Measurement calculation flow

For every feature, `measurement.measure_geometry`:

1. **Skips what has no measurement:** `Point`/`MultiPoint` -> note; `GeometryCollection`,
   empty or missing geometry -> note (graceful, no crash).
2. Finds the feature's **centroid** and converts it to lon/lat.
3. Picks the **UTM zone** for that point (see below).
4. **Reprojects** the geometry from its source CRS into that UTM zone.
5. Measures in metres: `area` for `Polygon`/`MultiPolygon`, `length` for
   `LineString`/`MultiLineString`.
6. Checks the result is a finite number and flags invalid geometries (for example a
   self-intersecting polygon) in `note`.

The values are rounded to 3 decimals and saved on the feature row, so
`GET .../measurements/` is just a database read.

### CRS handling

- The file's CRS is read from the file (`.prj` for shapefiles, WGS84 for KML) and reported as
  an EPSG code, for example `EPSG:4326`.
- **Measurements are always done in a projected CRS, in metres, never in degrees.**
- The projected CRS is the **UTM zone of the feature's centroid**:
  `zone = floor((lon + 180) / 6) + 1`, EPSG `326xx` for the northern hemisphere and
  `327xx` for the southern one. Near the poles (latitude >= 84 or <= -80), where UTM is not
  defined, polar stereographic (`EPSG:32661` / `EPSG:32761`) is used.
- Files that are **already projected** (for example EPSG:32643) go through the same process,
  so behaviour is consistent. This also protects against CRSs that distort areas or use feet.
- Coordinates are always handled in (x, y) = (lon, lat) order (`always_xy=True`) to avoid
  the classic axis-order bug.
- **Accuracy check:** on the sample plot, the UTM-based area differs from a geodesic
  calculation (`pyproj.Geod`) by about **0.12%**, and the line length by about **0.06%**.

---

## Design decisions

| Decision | What I chose | Alternatives considered | Why |
|---|---|---|---|
| Framework | **FastAPI** | Django + DRF | The API is small and file-focused. FastAPI gives validation, typed responses and Swagger docs with very little code. Django would add an ORM, admin and settings that this project doesn't need. |
| Reading files | **GeoPandas + pyogrio** | Fiona, `fastkml`, calling GDAL directly | One library reads both formats, returns shapely geometries and a CRS, and pyogrio ships GDAL inside its wheel (no manual GDAL install on Windows). |
| Choosing the projected CRS | **UTM zone per feature** | One fixed CRS for everything; equal-area CRS such as EPSG:6933; geodesic `pyproj.Geod` | UTM is accurate to a small fraction of a percent at survey scale, uses metres, and works anywhere on Earth. A single fixed CRS is wrong for most locations. Geodesic is more exact but the assignment asks for projection, so I used UTM and verified it against geodesic in the tests. |
| Reprojecting already-projected files | **Always reproject to UTM** | Trust the file's own projected CRS | The file's CRS may use feet or distort area (for example Web Mercator). One consistent path is also simpler to reason about and test. |
| Processing model | **Synchronous**, inside the upload request | Background tasks / Celery queue | Files in scope are small, so the result is ready in the upload response. The `status` field already exists, so moving to a queue later would not change the API. |
| When to measure | **At processing time**, store the results | Compute on every `GET .../measurements/` | Measuring once avoids repeating the reprojection on every read. The geometry is stored too, so recomputing is always possible. |
| Storage | **SQLite + SQLAlchemy 2.0** | In-memory dict; PostgreSQL/PostGIS | Zero setup for a reviewer, but still a real database with relations. The SQLAlchemy code would work unchanged with PostgreSQL. |
| Geometry storage | GeoJSON in a JSON column | PostGIS geometry column | Keeps the project runnable anywhere with no extensions. A spatial database would be the next step if spatial queries were needed. |
| Failed processing | `201` with `status: FAILED` | Return `4xx` | The file is already stored and has an id, so the client can look it up later and see why it failed. Bad file types and sizes are still `400` / `413`. |
| Unsupported geometries | Return `null` + `note` | Skip the feature or return an error | The client still sees every feature and learns why it has no measurement. |
| Multi-geometries | Also measure `MultiPolygon` / `MultiLineString` | Only the types in the brief | Real shapefiles often contain multi-part features, so supporting them was low effort and avoids surprising gaps. |
| Security | Zip-slip check, size limits, sanitised filenames, no server paths in errors | None | Uploaded archives are untrusted input, so these protections belong in the first version. |

---

## Testing

```bash
pytest
```

35 tests cover:

- **Upload and file info:** valid and invalid files, empty files, unknown ids, oversized
  uploads, uppercase extensions.
- **Parsing:** KML, zipped shapefile, KML with several folders, KML with altitude values,
  zip with no shapefile, invalid zip, shapefile without `.prj`, malicious zip (zip-slip).
- **Measurements:** area and length values checked against an independent geodesic
  calculation (`pyproj.Geod`), UTM zone selection (north, south, polar, antimeridian),
  a projected 100x100 m square giving exactly 10,000 m², multipolygons, points, unsupported
  and missing geometry, invalid (self-intersecting) polygons.
- **API behaviour:** measurements endpoint output, `409` for failed files, `404` for unknown
  ids, and error messages not exposing server paths.

Test files are generated in code (no binary fixtures committed) and every test uses a fresh
in-memory database and a temporary upload folder.

---

## Known limitations

- **Synchronous processing.** Large files would block the request. A job queue is the fix.
- **Features spanning several UTM zones** are measured in the zone of their centroid, so the
  error grows with the size of the feature.
- **UTM is not strictly equal-area.** The error is around 0.1% at survey scale (see the
  accuracy note above). Geodesic calculation would be exact.
- **Only the first `.shp`** is read if a zip contains several shapefiles.
- **Shapefiles without a `.prj`** are rejected instead of guessing the CRS.
- **No migrations.** Tables are created with `create_all`. If the schema changes, delete
  `geo_api.db` and restart (Alembic would be the proper fix).
- **Uploaded files are never deleted** from `uploads/`.
- **No authentication or rate limiting.**
- **No pagination** on `/features/` and `/measurements/`.

---

## What I learned

- **Degrees are not metres.** The core idea of the project: a 0.001 degree square at this
  latitude is about 12,000 m², so measuring in lat/lon would give a meaningless number.
  Reprojecting first, and then checking against an independent geodesic calculation in the
  tests, made me trust the numbers.
- **File formats have quirks.** A shapefile can only hold one geometry type, a missing `.prj`
  means no CRS, and KML folders appear as separate GDAL layers. KML also carries a lot of
  styling columns that are noise for this use case.
- **Axis order matters.** Different CRS definitions order coordinates differently, so
  `always_xy=True` is needed to keep (lon, lat) consistent.
- **Treat uploads as untrusted.** Zip-slip, size limits and sanitised filenames are easy to
  forget. Even error messages need care: my first version leaked a server file path from a
  library error, which I only noticed by reading the real response.
- **Separate layers early.** Keeping HTTP code, parsing and measurement apart made it simple
  to test the measurement logic with plain shapely geometries, without starting the API.
- **Test against a reference.** Comparing against `pyproj.Geod` is a much stronger check than
  asserting that "some number came back".
- **Keep the tooling current.** Newer shapely versions deprecate `shapely.ops.transform`, so I
  moved to `shapely.transform` instead of leaving warnings in the project.
- **Develop small and commit often.** Building in steps (upload -> parsing -> measurements ->
  polish -> docs) kept each change testable.

---

## Future scope

- **Background processing** (Celery or FastAPI background tasks) with status polling for large files.
- **Geodesic measurements** with `pyproj.Geod` as an option, and a query parameter to choose the method.
- **Split features that cross UTM zones** or use a local equal-area projection for very large features.
- **More input formats:** GeoJSON, GeoPackage, KMZ.
- **Perimeter** for polygons, and optional unit conversion (hectares, acres, kilometres, feet).
- **PostgreSQL + PostGIS** with Alembic migrations, enabling spatial queries and indexes.
- **Pagination, filtering and sorting** on the features and measurements endpoints.
- **Cleanup job** for old uploads and a `DELETE /api/files/{id}/` endpoint.
- **Authentication** and per-user file ownership, plus rate limiting.
- **Docker + docker-compose** and a GitHub Actions workflow that runs the tests on every push.
- **Support multiple shapefiles** per zip, and let the client supply a CRS for files without a `.prj`.