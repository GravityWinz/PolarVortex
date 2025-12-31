def test_create_and_get_project(client):
    resp = client.post("/projects", json={"name": "My Project"})
    assert resp.status_code == 200
    created = resp.json()
    assert created["name"] == "My Project"

    fetched = client.get(f"/projects/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


def test_image_upload_rejects_bad_type(client):
    # Create project
    proj = client.post("/projects", json={"name": "ImgProj"}).json()
    files = {"file": ("bad.txt", b"not-an-image", "text/plain")}
    resp = client.post(
        f"/projects/{proj['id']}/image_upload",
        files=files,
        data={"settings": "{}"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "File type not allowed" in body.get("detail", "")


def test_get_project_image_rejects_traversal(client):
    proj = client.post("/projects", json={"name": "SecProj"}).json()
    # Attempt to escape project directory
    resp = client.get(f"/projects/{proj['id']}/images/../../etc/passwd")
    assert resp.status_code == 400
    assert "Invalid file path" in resp.json().get("detail", "")


def test_gcode_upload_rejects_bad_extension(client):
    proj = client.post("/projects", json={"name": "GcodeProj"}).json()
    files = {"file": ("bad.txt", b"G1 X0 Y0", "text/plain")}
    resp = client.post(f"/projects/{proj['id']}/gcode_upload", files=files)
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json().get("detail", "")

