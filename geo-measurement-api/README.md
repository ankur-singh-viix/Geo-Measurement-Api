# Geospatial File Measurement API

A FastAPI backend that accepts a geospatial file (zipped Shapefile or KML),
extracts the features and returns area / length measurements.

> Work in progress. Full documentation will be added once the project is complete.

## Run locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger docs: http://127.0.0.1:8000/docs

## Tests

```bash
pytest
```
