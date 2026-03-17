from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class BridgeConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    api_token: str = "change-me"
    bot_key: str = ""
    default_guild_id: str = ""
    category_id: str = ""
    general_channel_name: str = "general"
    clear_all_parallelism: int = 4
    reply_timeout_seconds: int = 300
    typing_heartbeat_seconds: int = 8
    enable_bot: bool = True

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def load_config(env_file: str | None = None) -> BridgeConfig:
    if env_file:
        load_dotenv(Path(env_file))
    else:
        load_dotenv(Path(".env"))

    return BridgeConfig(
        host=os.getenv("BRIDGE_HOST", "127.0.0.1"),
        port=int(os.getenv("BRIDGE_PORT", "8080")),
        api_token=os.getenv("BRIDGE_API_TOKEN", "change-me"),
        bot_key=os.getenv("BOT_KEY", ""),
        default_guild_id=os.getenv("DISCORD_GUILD_ID", ""),
        category_id=os.getenv("DISCORD_CATEGORY_ID", ""),
        general_channel_name=os.getenv("DISCORD_GENERAL_CHANNEL_NAME", "general"),
        clear_all_parallelism=max(1, int(os.getenv("BRIDGE_CLEAR_ALL_PARALLELISM", "4"))),
        reply_timeout_seconds=int(os.getenv("BRIDGE_REPLY_TIMEOUT_SECONDS", "300")),
        typing_heartbeat_seconds=int(os.getenv("BRIDGE_TYPING_HEARTBEAT_SECONDS", "8")),
        enable_bot=env_flag("BRIDGE_ENABLE_BOT", True),
    )
