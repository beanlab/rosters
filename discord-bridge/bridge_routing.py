from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def load_default_env() -> None:
    cwd_env = Path(os.getcwd()) / ".env"
    load_dotenv(cwd_env)
    if cwd_env.exists():
        return
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    if (project_root / ".env").exists():
        return
    fallback_env = project_root.parent / "discord-server" / ".env"
    load_dotenv(fallback_env)


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--api-base-url", default=os.getenv("BRIDGE_API_BASE_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--api-token", default=os.getenv("BRIDGE_API_TOKEN", ""))
    parser.add_argument("--workspace-id")
    parser.add_argument("--session-id")
    parser.add_argument("--agent-id")
    parser.add_argument("--agent-name")
    parser.add_argument("--agent-kind", choices=["top_level", "subagent"])
    parser.add_argument("--discord-guild-id")
    return parser


def routing_from_args(args: argparse.Namespace) -> dict[str, str]:
    agent_kind = args.agent_kind or _default_agent_kind()
    if agent_kind == "subagent":
        agent_name, agent_id = _subagent_identity_from_args(args)
        workspace_id = _subagent_workspace_id(args)
        session_id = _subagent_session_id(args)
    else:
        agent_name, agent_id = resolve_top_level_identity(args.agent_id, args.agent_name)
        workspace_id = args.workspace_id or _default_workspace_id()
        session_id = args.session_id or _default_session_id()

    return {
        "workspace_id": workspace_id,
        "session_id": session_id,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "agent_kind": agent_kind,
        "discord_guild_id": args.discord_guild_id or os.getenv("DISCORD_GUILD_ID", ""),
        "timestamp": utc_now_iso(),
    }


def subagent_log_routing_from_args(args: argparse.Namespace) -> dict[str, str]:
    if getattr(args, "command", "") != "subagent-log":
        return routing_from_args(args)
    agent_kind = args.agent_kind or _default_agent_kind()
    if agent_kind == "subagent":
        workspace_id = _subagent_workspace_id(args)
        session_id = _subagent_session_id(args)
        agent_name, agent_id = resolve_parent_top_level_identity(
            getattr(args, "parent_agent_id", ""),
            getattr(args, "parent_agent_name", ""),
        )
    else:
        workspace_id = args.workspace_id or _default_workspace_id()
        session_id = args.session_id or _default_session_id()
        agent_name, agent_id = resolve_top_level_identity(args.agent_id, args.agent_name)
    # Coordination logs land in the caller's top-level coordination channel.
    # For subagents, prefer the explicit parent top-level identity and fall
    # back to a neutral top-level placeholder only if no parent identity is
    # available. Legacy --log-* flags are ignored.
    return {
        "workspace_id": workspace_id,
        "session_id": session_id,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "agent_kind": "top_level",
        "discord_guild_id": args.discord_guild_id or os.getenv("DISCORD_GUILD_ID", ""),
        "timestamp": utc_now_iso(),
    }


def _slug(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts) or "main"


def _default_workspace_id() -> str:
    return os.getenv("BRIDGE_WORKSPACE_ID", Path(os.getcwd()).resolve().name)


def _default_session_id() -> str:
    return os.getenv("BRIDGE_SESSION_ID", "default-session")


def _default_agent_kind() -> str:
    agent_kind = os.getenv("BRIDGE_AGENT_KIND", "").strip()
    if agent_kind:
        return agent_kind
    if _has_explicit_subagent_identity():
        return "subagent"
    if _has_ambiguous_thread_identity():
        raise SystemExit(
            "ambiguous bridge routing: only CODEX_THREAD_ID is available. "
            "Pass --agent-kind explicitly or use .myteam/discord-bridge/bridge_main.py / "
            ".myteam/discord-bridge/bridge_subagent.py."
        )
    return "top_level"


def _spawn_name_env() -> str:
    for key in ("CODEX_SPAWN_NAME", "CODEX_AGENT_NAME", "MYTEAM_AGENT_NAME", "BRIDGE_AGENT_NAME"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _spawn_id_env() -> str:
    for key in ("CODEX_SPAWN_ID", "CODEX_AGENT_ID", "MYTEAM_AGENT_ID", "CODEX_THREAD_ID"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _thread_id_env() -> str:
    return os.getenv("CODEX_THREAD_ID", "").strip()


def _top_level_name_env() -> str:
    for key in ("BRIDGE_AGENT_NAME", "CODEX_AGENT_NAME", "MYTEAM_AGENT_NAME"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _top_level_id_env() -> str:
    for key in ("BRIDGE_AGENT_ID", "CODEX_AGENT_ID", "MYTEAM_AGENT_ID", "CODEX_THREAD_ID"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _parent_top_level_name_env() -> str:
    for key in ("BRIDGE_PARENT_AGENT_NAME", "BRIDGE_TOP_LEVEL_AGENT_NAME"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _parent_top_level_id_env() -> str:
    for key in ("BRIDGE_PARENT_AGENT_ID", "BRIDGE_TOP_LEVEL_AGENT_ID"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _has_explicit_subagent_identity() -> bool:
    # Only treat the caller as a subagent by default when the runtime provides
    # spawn-specific identity. A bare thread ID is too broad and can leak into
    # the top-level agent environment, which collapses Main into a subagent
    # channel unless callers override agent-kind explicitly.
    if any(os.getenv(key, "").strip() for key in ("CODEX_SPAWN_ID", "CODEX_AGENT_ID", "MYTEAM_AGENT_ID")):
        return True
    if any(os.getenv(key, "").strip() for key in ("CODEX_SPAWN_NAME", "CODEX_AGENT_NAME", "MYTEAM_AGENT_NAME")):
        return True
    return False


def _has_ambiguous_thread_identity() -> bool:
    return bool(_thread_id_env()) and not _has_explicit_subagent_identity()


def resolve_subagent_identity(agent_id: str = "", agent_name: str = "") -> tuple[str, str]:
    spawn_name = _spawn_name_env()
    spawn_id = _spawn_id_env()
    resolved_name = (agent_name or spawn_name).strip()
    resolved_id = (agent_id or spawn_id).strip()
    if not resolved_id:
        resolved_id = _thread_id_env()
    if not resolved_id and resolved_name:
        raise SystemExit(
            "missing subagent routing agent_id: pass --agent-id or set CODEX_SPAWN_ID, "
            "CODEX_AGENT_ID, MYTEAM_AGENT_ID, or CODEX_THREAD_ID; agent_name alone is not enough"
        )
    if not resolved_id:
        raise SystemExit(
            "missing subagent routing agent_id: pass --agent-id or set CODEX_SPAWN_ID, "
            "CODEX_AGENT_ID, MYTEAM_AGENT_ID, or CODEX_THREAD_ID"
        )
    if not resolved_name:
        resolved_name = resolved_id
    return resolved_name, resolved_id


def resolve_top_level_identity(agent_id: str = "", agent_name: str = "") -> tuple[str, str]:
    resolved_name = (agent_name or _top_level_name_env()).strip()
    resolved_id = (agent_id or _top_level_id_env()).strip()
    if not resolved_id:
        resolved_id = _slug(resolved_name or "top-level")
    if not resolved_name:
        resolved_name = resolved_id
    return resolved_name, resolved_id


def resolve_parent_top_level_identity(agent_id: str = "", agent_name: str = "") -> tuple[str, str]:
    resolved_name = (agent_name or _parent_top_level_name_env()).strip()
    resolved_id = (agent_id or _parent_top_level_id_env()).strip()
    if resolved_id:
        if not resolved_name:
            resolved_name = resolved_id
        return resolved_name, resolved_id
    if resolved_name:
        return resolved_name, _slug(resolved_name)
    return "top-level", "top-level"


def _subagent_identity_from_args(args: argparse.Namespace) -> tuple[str, str]:
    # Prefer spawn-specific IDs when the runtime provides them. Fall back to
    # the Codex thread ID only after the caller has explicitly declared that
    # it is routing as a subagent.
    return resolve_subagent_identity(args.agent_id, args.agent_name)


def _subagent_workspace_id(args: argparse.Namespace) -> str:
    workspace_id = (args.workspace_id or os.getenv("BRIDGE_WORKSPACE_ID", "")).strip()
    if workspace_id:
        return workspace_id
    return _default_workspace_id()


def _subagent_session_id(args: argparse.Namespace) -> str:
    session_id = (args.session_id or os.getenv("BRIDGE_SESSION_ID", "")).strip()
    if session_id:
        return session_id
    return _default_session_id()
