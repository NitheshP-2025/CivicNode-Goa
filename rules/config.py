
import os
from dataclasses import dataclass, field
from pathlib import Path

# Absolute path to the rules/ directory
BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    """Central configuration for the Rules microservice."""

    service_name: str = "CivicNode-Goa Rules Service"
    environment: str = os.getenv("RULES_ENV", "development")

    host: str = os.getenv("RULES_HOST", "127.0.0.1")
    port: int = int(os.getenv("RULES_PORT", "8002"))

    # Never hardcode the internal authentication key.
    internal_api_key: str | None = os.getenv("RULES_INTERNAL_KEY")

    # Paths used by the rules engine and audit system.
    packs_dir: Path = BASE_DIR / "packs"
    database_path: Path = field(
    default_factory=lambda: Path(
        os.getenv(
            "RULES_DATABASE_PATH",
            str(BASE_DIR / "data" / "audit.db")
        )
    )
)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


def get_settings() -> Settings:
    """Return the application's configuration."""
    return Settings()


settings = get_settings()
