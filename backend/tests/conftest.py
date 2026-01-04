import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _reload_app_modules():
    """
    Reload backend modules so they pick up environment overrides for PV_CONFIG
    and storage paths. This keeps tests isolated without relying on global
    singletons from a previous import.
    """
    module_names = [
        "app.config",
        "app.config_service",
        "app.project_service",
        "app.main",
    ]
    for name in module_names:
        if name in sys.modules:
            importlib.reload(sys.modules[name])
        else:
            importlib.import_module(name)


class DummyArduino:
    """Lightweight serial stub used in tests."""

    def __init__(self):
        self.is_open = True
        self.writes: List[bytes] = []
        self._response = b"ok\n"

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    def readline(self) -> bytes:
        return self._response

    @property
    def in_waiting(self) -> int:
        return 1

    def close(self) -> None:
        self.is_open = False

    def reset_input_buffer(self) -> None:
        return None


class DummyImageHelper:
    """Minimal image helper that writes bytes to disk and returns predictable metadata."""

    allowed_types = {"image/png", "image/jpeg", "image/jpg"}

    def sanitize_filename(self, filename: str) -> str:
        return Path(filename).stem

    def get_project_directory(self, project_id: str) -> Path:
        base = Path(os.getenv("PROJECT_STORAGE", "."))
        project_dir = base / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def process_upload(
        self,
        file_content: bytes,
        file_content_type: str,
        file_size: int,
        file_name: str,
        settings_json: str,
        project_id: str,
    ) -> Dict[str, Any]:
        if file_content_type not in self.allowed_types:
            raise HTTPException(status_code=400, detail="File type not allowed")

        project_dir = self.get_project_directory(project_id)
        filename = f"{self.sanitize_filename(file_name)}{Path(file_name).suffix or '.bin'}"
        original_path = project_dir / filename
        original_path.write_bytes(file_content or b"data")

        thumb_path = project_dir / f"thumb_{filename}"
        thumb_path.write_bytes(b"thumb")

        return {
            "success": True,
            "original_size": file_size,
            "original_path": str(original_path),
            "thumbnail_path": str(thumb_path),
            "filename": filename,
        }

    def get_project_images(self, project_id: str) -> Dict[str, Any]:
        project_dir = self.get_project_directory(project_id)
        images = [str(p.name) for p in project_dir.glob("*") if p.is_file()]
        return {"images": images, "count": len(images)}

    # Vectorization stubs
    def vectorize_image(self, contents: bytes, settings: Dict[str, Any]):
        return {
            "vectorization_result": {
                "total_paths": 1,
                "colors_detected": 1,
                "processing_time": 0.1,
            },
            "svg_path": "dummy.svg",
        }

    def quick_vectorize(self, contents: bytes, blur: int, posterize: int, simplify: float):
        return {"success": True, "paths": 1, "blur": blur, "posterize": posterize, "simplify": simplify}

    def get_vectorization_settings_presets(self):
        return {"presets": [{"name": "default"}]}


def _apply_mocks(storage_root: Path, monkeypatch: pytest.MonkeyPatch):
    import app.main as main

    # Patch serial to avoid hardware
    monkeypatch.setattr(main, "serial", type("SerialModule", (), {"Serial": lambda *a, **k: DummyArduino(), "tools": main.serial.tools})())

    dummy_helper = DummyImageHelper()
    monkeypatch.setattr(main, "ImageHelper", lambda: dummy_helper)
    monkeypatch.setattr(main, "image_helper", dummy_helper)

    dummy_arduino = DummyArduino()
    main.plotter_service.arduino = dummy_arduino
    main.plotter_service.current_status.update({"connected": True, "port": "TEST", "baud_rate": 115200})
    main.plotter_service.command_log = []
    main.plotter_service.gcode_jobs = {}
    main.plotter_service.gcode_cancel_all.clear()
    main.plotter_service.gcode_pause_all.clear()

    async def fake_connect(request):
        main.plotter_service.arduino = DummyArduino()
        main.plotter_service.current_status["connected"] = True
        return {"success": True, "port": request.port, "baud_rate": request.baud_rate}

    async def fake_disconnect():
        main.plotter_service.arduino = None
        main.plotter_service.current_status["connected"] = False
        return {"success": True, "message": "Disconnected"}

    async def fake_gcode(req):
        return {"success": True, "command": req.command, "response": "ok"}

    async def fake_preprint():
        return {"success": True, "results": [], "message": "No pre-print G-code configured"}

    async def fake_stop():
        return {"success": True, "message": "Stop requested", "stop_sent": False, "canceled_jobs": []}

    async def fake_pause():
        paused = not main.plotter_service.gcode_pause_all.is_set()
        if paused:
            main.plotter_service.gcode_pause_all.set()
        else:
            main.plotter_service.gcode_pause_all.clear()
        return {"success": True, "paused": paused}

    monkeypatch.setattr(main.plotter_service, "get_available_ports", lambda: {"ports": [{"device": "TEST", "description": "Test Port"}]})
    monkeypatch.setattr(main.plotter_service, "connect_plotter", fake_connect)
    monkeypatch.setattr(main.plotter_service, "disconnect_plotter", fake_disconnect)
    monkeypatch.setattr(main.plotter_service, "send_gcode_command", fake_gcode)
    monkeypatch.setattr(main.plotter_service, "run_preprint_gcode", fake_preprint)
    monkeypatch.setattr(main.plotter_service, "stop_plotter", fake_stop)
    monkeypatch.setattr(main.plotter_service, "pause_plotter", fake_pause)

    # Analysis / conversion stubs
    async def fake_convert_svg_to_gcode_file(svg_path, output_path, **kwargs):
        output_path.write_text("; dummy gcode")
        return True

    def fake_analyze_gcode_file(file_path):
        return {"bounds": [0, 0, 1, 1], "distance": 1.0, "estimated_time_seconds": 1}

    def fake_analyze_svg_file(file_path):
        return {"bounds": [0, 0, 1, 1], "paths": 1}

    monkeypatch.setattr(main, "convert_svg_to_gcode_file", fake_convert_svg_to_gcode_file)
    monkeypatch.setattr(main, "analyze_gcode_file", fake_analyze_gcode_file)
    monkeypatch.setattr(main, "analyze_svg_file", fake_analyze_svg_file)

    # Ensure project storage exists
    from app.project_service import project_service as proj_service

    proj_service.project_storage_path = storage_root / "projects"
    proj_service._ensure_project_storage_exists()


@pytest.fixture()
def temp_env(tmp_path, monkeypatch):
    """
    Provide isolated local_storage and config file for each test.
    """
    storage = tmp_path / "local_storage"
    storage.mkdir(parents=True, exist_ok=True)
    cfg_path = storage / "config" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("PV_CONFIG", str(cfg_path))
    monkeypatch.setenv("LOCAL_STORAGE", str(storage))
    monkeypatch.setenv("PROJECT_STORAGE", str(storage / "projects"))

    _reload_app_modules()

    from app.config_service import config_service as cfg_service
    from app.project_service import project_service as proj_service

    # Ensure fresh config and project storage
    cfg_service.config_file_path = Path(cfg_path)
    cfg_service.config_data = cfg_service._get_default_config()
    cfg_service._save_configurations()

    proj_service.project_storage_path = Path(cfg_service.config.project_storage)
    proj_service._ensure_project_storage_exists()

    yield storage


@pytest.fixture()
def client(temp_env, monkeypatch):
    import app.main as main

    _apply_mocks(temp_env, monkeypatch)

    with TestClient(main.app) as c:
        yield c

