
from rules.config import settings
from rules.config import get_settings, BASE_DIR

def test_service_configuration():
    assert settings.service_name == "CivicNode-Goa Rules Service"
    assert settings.port == 8002
    assert settings.environment == "development"


def test_rule_pack_directory():
    assert settings.packs_dir.exists()
    assert settings.packs_dir.is_dir()

def test_database_path_uses_default_when_env_missing(monkeypatch):
    monkeypatch.delenv("RULES_DATABASE_PATH", raising=False)

    settings = get_settings()

    assert settings.database_path == BASE_DIR / "data" / "audit.db"


def test_database_path_uses_environment_variable(monkeypatch, tmp_path):
    custom_path = tmp_path / "custom_audit.db"
    monkeypatch.setenv("RULES_DATABASE_PATH", str(custom_path))

    settings = get_settings()

    assert settings.database_path == custom_path