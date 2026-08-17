import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def csv_ints(name: str) -> set[int]:
    return {int(x.strip()) for x in os.getenv(name, "").split(",") if x.strip()}


@dataclass
class Settings:
    discord_token: str = os.getenv("DISCORD_TOKEN", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    moderation_model: str = os.getenv("MODERATION_MODEL", "omni-moderation-latest")
    threshold: float = float(os.getenv("MODERATION_THRESHOLD", "8.0"))
    test_mode: bool = os.getenv("TEST_MODE", "false").lower() == "true"
    timeout_minutes: int = int(os.getenv("TIMEOUT_MINUTES", "10"))
    log_channel_id: int | None = int(os.environ["MOD_LOG_CHANNEL_ID"]) if os.getenv("MOD_LOG_CHANNEL_ID") else None
    alert_channel_id: int | None = int(os.environ["MOD_ALERT_CHANNEL_ID"]) if os.getenv("MOD_ALERT_CHANNEL_ID") else None
    admin_channel_id: int | None = int(os.environ["ADMIN_CHANNEL_ID"]) if os.getenv("ADMIN_CHANNEL_ID") else None
    database_path: str = os.getenv("DATABASE_PATH", "moderation.db")
    ignored_channel_ids: set[int] = field(default_factory=lambda: csv_ints("IGNORED_CHANNEL_IDS"))
    ignored_role_ids: set[int] = field(default_factory=lambda: csv_ints("IGNORED_ROLE_IDS"))


settings = Settings()

if not settings.discord_token:
    raise RuntimeError("DISCORD_TOKEN is required")
if not settings.openai_api_key:
    raise RuntimeError("OPENAI_API_KEY is required")
