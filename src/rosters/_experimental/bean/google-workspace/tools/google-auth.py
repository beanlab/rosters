#!/usr/bin/env python3
"""Manage local Google Workspace user OAuth credentials safely.

This helper owns authorization, refresh, account verification, and token-file
storage. It does not call Google Workspace service APIs or display credential
secrets. Run ``google-auth.py --help`` for the supported interface.

The ``status`` command uses only the Python standard library. Run the Google
Workspace bootstrap before using ``authorize`` or ``refresh``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence, Tuple

DEFAULT_WORKSPACE = Path("~/.agents/scratch/google-workspace").expanduser()
CLIENT_FILENAME = "oauth-client.json"
IDENTITY_SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
)
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
ALLOWED_AUTH_URIS = {
    "https://accounts.google.com/o/oauth2/auth",
    "https://accounts.google.com/o/oauth2/v2/auth",
}
ALLOWED_TOKEN_URIS = {"https://oauth2.googleapis.com/token"}
SAFE_OAUTH_ERROR_CODES = {
    "access_denied",
    "admin_policy_enforced",
    "consent_required",
    "interaction_required",
    "invalid_client",
    "invalid_grant",
    "invalid_scope",
    "server_error",
    "temporarily_unavailable",
    "unauthorized_client",
}


class HelperError(Exception):
    """An expected, safely reportable helper failure."""


def build_parser() -> argparse.ArgumentParser:
    examples = """examples:
  %(prog)s status
  %(prog)s refresh --account user@example.com
  %(prog)s authorize --account user@example.com \\
      --scope https://www.googleapis.com/auth/drive.readonly

Authorization always adds the openid and userinfo.email identity scopes.
Existing scopes for the account are retained. Credentials default to:
  ~/.agents/scratch/google-workspace/oauth-client.json
  ~/.agents/scratch/google-workspace/tokens/<google-email>.json
"""
    parser = argparse.ArgumentParser(
        description=(
            "Authorize, inspect, and refresh local Google Workspace OAuth "
            "credentials without displaying secrets."
        ),
        epilog=examples,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help="credential workspace (default: %(default)s)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "status",
        help="list stored accounts, refresh-token presence, and scopes",
        description=(
            "Inspect stored credential files without making network requests or "
            "requiring Google Python packages."
        ),
    )

    refresh = subparsers.add_parser(
        "refresh",
        help="refresh and validate one account's credentials",
    )
    refresh.add_argument(
        "--account",
        required=True,
        type=account_email,
        help="expected Google account email",
    )

    authorize = subparsers.add_parser(
        "authorize",
        help="run browser OAuth and atomically save one account's credentials",
    )
    authorize.add_argument(
        "--account",
        required=True,
        type=account_email,
        help="expected Google account email",
    )
    authorize.add_argument(
        "--scope",
        action="append",
        default=[],
        metavar="SCOPE",
        help=(
            "required service scope; repeat for multiple scopes. Identity scopes "
            "and previously stored scopes are added automatically"
        ),
    )

    return parser


def account_email(value: str) -> str:
    normalized = value.strip().lower()
    if (
        normalized.count("@") != 1
        or normalized.startswith("@")
        or normalized.endswith("@")
        or normalized in {".", ".."}
        or any(character.isspace() or not character.isprintable() for character in normalized)
        or any(character in normalized for character in "/\\")
    ):
        raise argparse.ArgumentTypeError("account must be a safe email filename")
    return normalized


def workspace_paths(workspace: Path) -> Tuple[Path, Path]:
    root = workspace.expanduser().resolve()
    return root / CLIENT_FILENAME, root / "tokens"


def token_path(tokens_dir: Path, account: str) -> Path:
    # account_email rejects path separators; this containment check is defense in depth.
    candidate = (tokens_dir / f"{account}.json").resolve()
    if candidate.parent != tokens_dir.resolve():
        raise HelperError("Account would resolve outside the token directory.")
    return candidate


def ensure_private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise HelperError(f"Credential directory is not a regular directory: {path}")
    path.chmod(0o700)


def require_regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise HelperError(f"{label} is missing or is not a regular file: {path}")


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    require_regular_file(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise HelperError(f"{label} is not valid JSON: {path}") from error
    if not isinstance(value, dict):
        raise HelperError(f"{label} must contain a JSON object: {path}")
    return value


def validate_client_file(path: Path) -> None:
    client = read_json_object(path, "OAuth client configuration")
    installed = client.get("installed")
    if not isinstance(installed, dict):
        raise HelperError(
            "OAuth client configuration is not a Desktop app ('installed') client."
        )
    required = ("client_id", "auth_uri", "token_uri")
    if any(not isinstance(installed.get(field), str) or not installed[field] for field in required):
        raise HelperError("OAuth client configuration is missing required installed-client fields.")
    if installed["auth_uri"] not in ALLOWED_AUTH_URIS:
        raise HelperError("OAuth client configuration uses an untrusted authorization endpoint.")
    if installed["token_uri"] not in ALLOWED_TOKEN_URIS:
        raise HelperError("OAuth client configuration uses an untrusted token endpoint.")
    path.chmod(0o600)


def validate_token_endpoint(value: dict[str, Any]) -> None:
    if value.get("token_uri") not in ALLOWED_TOKEN_URIS:
        raise HelperError("Credential file uses an untrusted token endpoint.")


def validate_scope(scope: str) -> str:
    if (
        not scope
        or any(character.isspace() or not character.isprintable() for character in scope)
    ):
        raise HelperError("Credential data contains an invalid OAuth scope.")
    return scope


def scopes_from_mapping(value: dict[str, Any]) -> set[str]:
    raw = value.get("scopes", [])
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {validate_scope(scope) for scope in raw.split() if scope}
    if isinstance(raw, list) and all(isinstance(scope, str) for scope in raw):
        return {validate_scope(scope) for scope in raw if scope}
    raise HelperError("Credential file contains an invalid scopes field.")


def existing_scopes(path: Path) -> set[str]:
    if not path.exists():
        return set()
    value = read_json_object(path, "Account credential")
    validate_token_endpoint(value)
    return scopes_from_mapping(value)


def normalize_scopes(scopes: Iterable[str]) -> list[str]:
    normalized = set(IDENTITY_SCOPES)
    for scope in scopes:
        normalized.add(validate_scope(scope.strip()))
    return sorted(normalized)


def load_google_dependencies() -> Tuple[Any, Any, Any]:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ModuleNotFoundError as error:
        raise HelperError(
            "Google OAuth dependencies are missing. Run the Google Workspace bootstrap."
        ) from error
    return Request, Credentials, InstalledAppFlow


def credential_scopes(credentials: Any) -> list[str]:
    granted = getattr(credentials, "granted_scopes", None)
    requested = getattr(credentials, "scopes", None)
    return sorted(set(granted or requested or []))


def require_scopes(credentials: Any, required: Sequence[str]) -> None:
    if not credentials.has_scopes(required):
        actual = set(credential_scopes(credentials))
        missing = sorted(set(required) - actual)
        raise HelperError(
            "Google did not grant all required scopes. Missing: " + ", ".join(missing)
        )


def fetch_identity(credentials: Any) -> str:
    token = getattr(credentials, "token", None)
    if not token:
        raise HelperError("Credentials do not contain a usable access token.")

    request = urllib.request.Request(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise HelperError(
            f"Google account identity validation failed with HTTP {error.code}."
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise HelperError("Google account identity validation could not reach Google.") from error
    except (UnicodeError, json.JSONDecodeError) as error:
        raise HelperError("Google returned an invalid account identity response.") from error

    if not isinstance(payload, dict):
        raise HelperError("Google returned an invalid account identity response.")
    email = payload.get("email")
    if not isinstance(email, str):
        raise HelperError("Google did not return an email for the authorized account.")
    try:
        normalized = account_email(email)
    except argparse.ArgumentTypeError as error:
        raise HelperError("Google returned an invalid account email.") from error
    if payload.get("email_verified") is not True:
        raise HelperError("Google did not report the authorized account email as verified.")
    return normalized


def atomic_write_credentials(path: Path, serialized: str) -> None:
    ensure_private_directory(path.parent)
    temporary: Optional[Path] = None
    descriptor: Optional[int] = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        data = (serialized.rstrip("\n") + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        path.chmod(0o600)
        fsync_directory(path.parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def command_authorize(args: argparse.Namespace) -> int:
    client_file, tokens_dir = workspace_paths(args.workspace)
    ensure_private_directory(client_file.parent)
    ensure_private_directory(tokens_dir)
    validate_client_file(client_file)

    destination = token_path(tokens_dir, args.account)
    requested = normalize_scopes([*existing_scopes(destination), *args.scope])
    Request, _, InstalledAppFlow = load_google_dependencies()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_file), scopes=requested
        )
        credentials = flow.run_local_server(
            host="localhost",
            port=0,
            authorization_prompt_message=(
                "Open this URL in a browser to authorize the requested Google account:\n{url}"
            ),
            success_message="Authorization received. You may close this browser window.",
            open_browser=True,
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            login_hint=args.account,
        )
        if not getattr(credentials, "refresh_token", None):
            raise HelperError(
                "Google did not issue a refresh token; existing credentials were preserved."
            )
        require_scopes(credentials, requested)
        credentials.refresh(Request())
        require_scopes(credentials, requested)
        actual_account = fetch_identity(credentials)
        if actual_account != args.account:
            raise HelperError(
                f"Authorized account {actual_account} does not match requested account "
                f"{args.account}; existing credentials were preserved."
            )
        atomic_write_credentials(destination, credentials.to_json())
    except HelperError:
        raise
    except Exception as error:
        raise HelperError(external_failure("OAuth authorization", error)) from error

    print(f"Authorized account: {args.account}")
    print("Refresh validation: succeeded")
    print_scopes(credential_scopes(credentials))
    return 0


def command_refresh(args: argparse.Namespace) -> int:
    _, tokens_dir = workspace_paths(args.workspace)
    ensure_private_directory(tokens_dir.parent)
    ensure_private_directory(tokens_dir)
    path = token_path(tokens_dir, args.account)
    value = read_json_object(path, "Account credential")
    validate_token_endpoint(value)
    path.chmod(0o600)
    Request, Credentials, _ = load_google_dependencies()

    try:
        credentials = Credentials.from_authorized_user_file(str(path))
        if not getattr(credentials, "refresh_token", None):
            raise HelperError("Account credential does not contain a refresh token.")
        credentials.refresh(Request())
        actual_account = fetch_identity(credentials)
        if actual_account != args.account:
            raise HelperError(
                f"Credential belongs to {actual_account}, not {args.account}; file was preserved."
            )
        atomic_write_credentials(path, credentials.to_json())
    except HelperError:
        raise
    except Exception as error:
        raise HelperError(external_failure("Credential refresh", error)) from error

    print(f"Account: {args.account}")
    print("Refresh validation: succeeded")
    print_scopes(credential_scopes(credentials))
    return 0


def command_status(args: argparse.Namespace) -> int:
    _, tokens_dir = workspace_paths(args.workspace)
    if not tokens_dir.exists():
        print("No stored account credentials.")
        return 0
    if tokens_dir.is_symlink() or not tokens_dir.is_dir():
        raise HelperError(f"Token path is not a regular directory: {tokens_dir}")

    files = sorted(tokens_dir.glob("*.json"), key=lambda path: path.name.lower())
    if not files:
        print("No stored account credentials.")
        return 0

    had_error = False
    for index, path in enumerate(files):
        if index:
            print()
        inferred_account = path.stem.lower()
        print(f"Account: {inferred_account}")
        try:
            if account_email(inferred_account) != inferred_account:
                raise HelperError("filename is not a valid account email")
            value = read_json_object(path, "Account credential")
            validate_token_endpoint(value)
            scopes = sorted(scopes_from_mapping(value))
            refreshable = isinstance(value.get("refresh_token"), str) and bool(
                value["refresh_token"]
            )
            print(f"Refresh token: {'present' if refreshable else 'missing'}")
            print_scopes(scopes)
        except (HelperError, argparse.ArgumentTypeError) as error:
            had_error = True
            print(f"Stored credential: invalid ({error})")

    return 1 if had_error else 0


def print_scopes(scopes: Sequence[str]) -> None:
    print("Granted scopes:")
    if not scopes:
        print("  (none recorded)")
        return
    for scope in scopes:
        print(f"  {scope}")


def external_failure(operation: str, error: BaseException) -> str:
    """Describe an upstream failure using only allowlisted, non-secret fields."""
    error_code = allowlisted_oauth_error(error)
    status = http_status(error)
    details = []
    if error_code:
        details.append(f"OAuth error {error_code}")
    if status is not None:
        details.append(f"HTTP {status}")
    suffix = f" ({', '.join(details)})" if details else ""
    return f"{operation} failed{suffix}; existing credentials were preserved."


def allowlisted_oauth_error(error: BaseException) -> Optional[str]:
    candidates = [getattr(error, "error", None)]
    for argument in getattr(error, "args", ()):
        if isinstance(argument, dict):
            candidates.append(argument.get("error"))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate in SAFE_OAUTH_ERROR_CODES:
            return candidate
    return None


def http_status(error: BaseException) -> Optional[int]:
    response = getattr(error, "response", None)
    candidates = (
        getattr(response, "status_code", None),
        getattr(response, "status", None),
        getattr(error, "status_code", None),
    )
    for candidate in candidates:
        if isinstance(candidate, int) and 100 <= candidate <= 599:
            return candidate
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            return command_status(args)
        if args.command == "refresh":
            return command_refresh(args)
        if args.command == "authorize":
            return command_authorize(args)
        parser.error(f"unknown command: {args.command}")
    except HelperError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Error: local credential filesystem operation failed.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Error: interrupted; existing credentials were preserved.", file=sys.stderr)
        return 130
    except Exception:
        print("Error: unexpected OAuth helper failure.", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
