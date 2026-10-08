from tests.sample_data import KML_SAMPLE


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_kml(client):
    res = client.post(
        "/api/files/",
        files={"file": ("survey.kml", KML_SAMPLE, "application/vnd.google-earth.kml+xml")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["filename"] == "survey.kml"
    assert body["file_type"] == "kml"
    assert body["status"] == "COMPLETED"


def test_upload_invalid_kml_is_kept_but_marked_failed(client):
    res = client.post("/api/files/", files={"file": ("broken.kml", b"<kml></kml>", "text/plain")})
    assert res.status_code == 201
    assert res.json()["status"] == "FAILED"


def test_upload_rejects_unsupported_extension(client):
    res = client.post("/api/files/", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert res.status_code == 400


def test_upload_rejects_empty_file(client):
    res = client.post("/api/files/", files={"file": ("empty.kml", b"", "text/plain")})
    assert res.status_code == 400


def test_get_file_info(client):
    created = client.post(
        "/api/files/", files={"file": ("a.kml", KML_SAMPLE, "text/plain")}
    ).json()
    res = client.get(f"/api/files/{created['id']}/")
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]


def test_get_file_not_found(client):
    assert client.get("/api/files/doesnotexist/").status_code == 404