import importlib
import sys
from pathlib import Path

import pytest
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

    yield


@pytest.fixture()
def client(temp_env):
    import app.main as main

    with TestClient(main.app) as c:
        yield c

