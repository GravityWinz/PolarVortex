import json
from pathlib import Path

import pytest

from app import main
from app.project_service import project_service


def _create_project(client, name="Project"):
    resp = client.post("/projects", json={"name": name})
    assert resp.status_code == 200
    return resp.json()


def test_root_and_health(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["status"] == "running"

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "healthy"
    assert "arduino_connected" in body


def test_status_connected_and_disconnected(client):
    status = client.get("/status").json()
    assert status["connected"] is True

    main.plotter_service.arduino = None
    status = client.get("/status").json()
    assert status["connected"] is False
    assert status["status"] == "Arduino not connected"


def test_plotter_ports_connect_disconnect_and_log(client):
    ports = client.get("/plotter/ports").json()
    assert ports["ports"]

    conn = client.post("/plotter/connect", json={"port": "TEST", "baud_rate": 115200})
    assert conn.status_code == 200
    assert conn.json()["success"] is True

    # gcode send
    gcode = client.post("/plotter/gcode", json={"command": "G0 X0"}).json()
    assert gcode["success"] is True

    # log clear / fetch
    log_resp = client.get("/plotter/log").json()
    assert "log" in log_resp
    cleared = client.post("/plotter/log/clear").json()
    assert cleared["success"] is True

    disc = client.post("/plotter/disconnect").json()
    assert disc["success"] is True


def test_preprint_stop_pause(client):
    preprint = client.post("/plotter/gcode/preprint").json()
    assert preprint["success"] is True

    stop = client.post("/plotter/stop").json()
    assert stop["success"] is True

    pause = client.post("/plotter/pause").json()
    assert pause["success"] is True


def test_project_crud_and_listing(client):
    created = _create_project(client, "My Project")
    fetched = client.get(f"/projects/{created['id']}").json()
    assert fetched["name"] == "My Project"

    listing = client.get("/projects").json()
    assert listing["total"] >= 1

    deleted = client.delete(f"/projects/{created['id']}").json()
    assert deleted["success"] is True


def test_image_upload_and_fetch(client, tmp_path):
    project = _create_project(client, "ImgProj")
    files = {"file": ("img.png", b"data", "image/png")}
    resp = client.post(
        f"/projects/{project['id']}/image_upload",
        files=files,
        data={"settings": json.dumps({})},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    images = client.get(f"/projects/{project['id']}/images").json()
    assert images["count"] >= 1


def test_image_upload_rejects_bad_type(client):
    project = _create_project(client, "BadImg")
    files = {"file": ("bad.txt", b"not-an-image", "text/plain")}
    resp = client.post(
        f"/projects/{project['id']}/image_upload",
        files=files,
        data={"settings": "{}"},
    )
    assert resp.status_code == 400
    assert "File type not allowed" in resp.json().get("detail", "")


def test_project_image_and_thumbnail_and_delete(client):
    project = _create_project(client, "ImgFetch")
    # upload valid image
    files = {"file": ("img.png", b"content", "image/png")}
    client.post(f"/projects/{project['id']}/image_upload", files=files, data={"settings": "{}"})

    # fetch thumbnail
    thumb = client.get(f"/projects/{project['id']}/thumbnail")
    assert thumb.status_code in {200, 404}  # thumbnail path may vary, endpoint handled

    # file traversal protection
    traversal = client.get(f"/projects/{project['id']}/images/../../etc/passwd")
    assert traversal.status_code == 400

    # delete uploaded file
    project_dir = project_service._get_project_directory(project["id"])
    uploaded = next(project_dir.glob("*.png"))
    delete_resp = client.delete(f"/projects/{project['id']}/images/{uploaded.name}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True


def test_gcode_upload_and_analysis(client):
    project = _create_project(client, "GcodeProj")
    # reject bad extension
    bad = client.post(f"/projects/{project['id']}/gcode_upload", files={"file": ("bad.txt", b"G0", "text/plain")})
    assert bad.status_code == 400

    good = client.post(
        f"/projects/{project['id']}/gcode_upload",
        files={"file": ("file.gcode", b"G1 X0 Y0", "text/plain")},
    )
    assert good.status_code == 200
    filename = good.json()["relative_path"]

    # analysis requires file to be registered
    analysis = client.get(f"/projects/{project['id']}/gcode/{filename}/analysis")
    assert analysis.status_code == 200
    assert "bounds" in analysis.json()


def test_svg_analysis_and_conversion(client, tmp_path):
    project = _create_project(client, "SvgProj")
    project_dir = project_service._get_project_directory(project["id"])
    project_dir.mkdir(parents=True, exist_ok=True)
    svg_path = project_dir / "test.svg"
    svg_path.write_text("<svg></svg>")

    convert = client.post(
        f"/projects/{project['id']}/svg_to_gcode",
        json={"filename": "test.svg", "paper_size": "A4", "pen_mapping": {}},
    )
    assert convert.status_code == 200
    assert convert.json()["success"] is True

    svg_analysis = client.get(f"/projects/{project['id']}/svg/test.svg/analysis")
    assert svg_analysis.status_code == 200
    assert svg_analysis.json()["paths"] == 1


def test_run_project_gcode_and_job_status(client):
    project = _create_project(client, "RunProj")
    project_dir = project_service._get_project_directory(project["id"])
    gcode_file = project_dir / "gcode" / "run.gcode"
    gcode_file.parent.mkdir(parents=True, exist_ok=True)
    gcode_file.write_text("G1 X0 Y0\nG1 X1 Y1\n")
    project_service.add_project_gcode_file(project["id"], str(Path("gcode") / "run.gcode"))

    resp = client.post(f"/projects/{project['id']}/gcode/run", json={"filename": str(Path('gcode') / 'run.gcode')})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["queued"] == 2


def test_vectorization_endpoints(client):
    files = {"file": ("img.png", b"content", "image/png")}
    vectorize = client.post("/vectorize", files=files, data={"settings": json.dumps({})})
    assert vectorize.status_code == 200

    quick = client.post(
        "/quick-vectorize",
        files=files,
        data={"blur": "1", "posterize": "2", "simplify": "1.0"},
    )
    assert quick.status_code == 200
    presets = client.get("/vectorize/presets")
    assert presets.status_code == 200
    assert presets.json()["presets"]


def test_configuration_endpoints(client):
    all_cfg = client.get("/config")
    assert all_cfg.status_code == 200

    gcode_cfg = client.get("/config/gcode")
    assert gcode_cfg.status_code == 200

    updated = client.put("/config/gcode", json={"on_connect": ["G28"], "before_print": []})
    assert updated.status_code == 200
    assert "G28" in updated.json()["on_connect"]

    # plotter CRUD
    plotter = client.post("/config/plotters", json={"name": "TestPlotter", "paper_size": "A4"}).json()
    listed = client.get("/config/plotters").json()
    assert any(p["id"] == plotter["id"] for p in listed["plotters"])
    fetched = client.get(f"/config/plotters/{plotter['id']}").json()
    assert fetched["name"] == "TestPlotter"

    # paper CRUD
    paper = client.post("/config/papers", json={"name": "TestPaper", "paper_size": "Letter", "width": 8.5, "height": 11}).json()
    papers = client.get("/config/papers").json()
    assert any(p["id"] == paper["id"] for p in papers["papers"])

    default_plotter = client.get("/config/plotters/default")
    assert default_plotter.status_code in {200, 404}

    default_paper = client.get("/config/papers/default")
    assert default_paper.status_code in {200, 404}

    rebuilt = client.post("/config/rebuild").json()
    assert rebuilt["success"] is True


def test_websocket_ping_pong(client):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"type": "ping"}))
        msg = websocket.receive_text()
        assert "connection_established" in msg or "pong" in msg

