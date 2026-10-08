import io
import zipfile

from tests.sample_data import KML_SAMPLE, make_shapefile_zip


def _upload(client, name, content):
    return client.post("/api/files/", files={"file": (name, content, "application/octet-stream")})


def test_kml_is_processed(client):
    res = _upload(client, "survey.kml", KML_SAMPLE)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "COMPLETED"
    assert body["feature_count"] == 3
    assert body["crs"] == "EPSG:4326"


def test_kml_features(client):
    file_id = _upload(client, "survey.kml", KML_SAMPLE).json()["id"]
    features = client.get(f"/api/files/{file_id}/features/").json()

    assert [f["geometry_type"] for f in features] == ["Polygon", "LineString", "Point"]
    assert features[0]["properties"]["Name"] == "Plot A"
    assert features[0]["geometry"]["type"] == "Polygon"
    assert features[0]["crs"] == "EPSG:4326"


def test_shapefile_zip_is_processed(client, tmp_path):
    content = make_shapefile_zip(tmp_path)
    body = _upload(client, "survey.zip", content).json()
    assert body["status"] == "COMPLETED"
    assert body["feature_count"] == 3
    assert body["crs"] == "EPSG:4326"

    features = client.get(f"/api/files/{body['id']}/features/").json()
    assert [f["geometry_type"] for f in features] == ["Polygon", "Polygon", "MultiPolygon"]
    assert features[0]["properties"]["name"] == "Plot A"
    assert features[1]["properties"]["owner"] is None


def test_zip_without_shapefile_fails_gracefully(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "nothing here")
    body = _upload(client, "bad.zip", buf.getvalue()).json()
    assert body["status"] == "FAILED"
    assert "No .shp" in body["error_message"]


def test_invalid_zip_fails_gracefully(client):
    body = _upload(client, "fake.zip", b"this is not a zip").json()
    assert body["status"] == "FAILED"


def test_features_for_unknown_file(client):
    assert client.get("/api/files/nope/features/").status_code == 404