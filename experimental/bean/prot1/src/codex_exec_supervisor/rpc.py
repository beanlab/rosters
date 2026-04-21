from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


JSON_RPC_VERSION = "2.0"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
UNKNOWN_SESSION = -32010
UNKNOWN_WORKER = -32011
STALE_WORKER = -32012


class JsonRpcError(Exception):
    def __init__(self, code: int, message: str, data: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            payload["data"] = self.data
        return payload


@dataclass(frozen=True)
class JsonRpcRequest:
    request_id: str | int | None
    method: str
    params: dict[str, Any]


@dataclass(frozen=True)
class JsonRpcResponse:
    request_id: str | int | None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


def decode_request_line(line: str) -> JsonRpcRequest:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise JsonRpcError(PARSE_ERROR, "invalid JSON", {"detail": str(exc)}) from exc
    if not isinstance(payload, dict):
        raise JsonRpcError(INVALID_REQUEST, "request must be an object")
    if payload.get("jsonrpc") != JSON_RPC_VERSION:
        raise JsonRpcError(INVALID_REQUEST, "jsonrpc must be '2.0'")
    method = payload.get("method")
    if not isinstance(method, str) or not method:
        raise JsonRpcError(INVALID_REQUEST, "method must be a non-empty string")
    params = payload.get("params", {})
    if not isinstance(params, dict):
        raise JsonRpcError(INVALID_PARAMS, "params must be an object")
    request_id = payload.get("id")
    if request_id is not None and not isinstance(request_id, (str, int)):
        raise JsonRpcError(INVALID_REQUEST, "id must be a string, integer, or null")
    return JsonRpcRequest(request_id=request_id, method=method, params=params)


def decode_response_line(line: str) -> JsonRpcResponse:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise JsonRpcError(PARSE_ERROR, "invalid JSON", {"detail": str(exc)}) from exc
    if not isinstance(payload, dict):
        raise JsonRpcError(INVALID_REQUEST, "response must be an object")
    if payload.get("jsonrpc") != JSON_RPC_VERSION:
        raise JsonRpcError(INVALID_REQUEST, "jsonrpc must be '2.0'")
    request_id = payload.get("id")
    result = payload.get("result")
    error = payload.get("error")
    if result is not None and error is not None:
        raise JsonRpcError(INVALID_REQUEST, "response cannot include both result and error")
    if result is None and error is None:
        raise JsonRpcError(INVALID_REQUEST, "response must include result or error")
    if error is not None and not isinstance(error, dict):
        raise JsonRpcError(INVALID_REQUEST, "error must be an object")
    if result is not None and not isinstance(result, dict):
        raise JsonRpcError(INVALID_REQUEST, "result must be an object")
    return JsonRpcResponse(request_id=request_id, result=result, error=error)


def encode_success(request_id: str | int | None, result: dict[str, Any]) -> str:
    return json.dumps(
        {"jsonrpc": JSON_RPC_VERSION, "id": request_id, "result": result},
        sort_keys=True,
    )


def encode_error(request_id: str | int | None, error: JsonRpcError) -> str:
    return json.dumps(
        {"jsonrpc": JSON_RPC_VERSION, "id": request_id, "error": error.to_payload()},
        sort_keys=True,
    )
