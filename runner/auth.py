from __future__ import annotations

import base64
import fcntl
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from requests import RequestException, Response

from config import get_settings

logger = logging.getLogger(__name__)

_TOKEN_SKEW_SECONDS = 30  # refresh token a little before expiry
_LOG_MAX_BODY = 500


def _redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    redacted = {k: v for k, v in headers.items() if k.lower() != "authorization"}
    if "Authorization" in headers or "authorization" in headers:
        redacted["Authorization"] = "***"
    return redacted


def _trim_body(body: Optional[str]) -> Optional[str]:
    if body is None:
        return None
    if len(body) <= _LOG_MAX_BODY:
        return body
    return body[:_LOG_MAX_BODY] + "... (truncated)"


def _serialise_body(payload: Any) -> Optional[str]:
    if payload is None:
        return None
    try:
        if isinstance(payload, (str, bytes)):
            value = payload.decode() if isinstance(payload, bytes) else payload
        else:
            value = json.dumps(payload, default=str)
    except Exception:
        value = str(payload)
    return _trim_body(value)


def _log_request(method: str, url: str, kwargs: Dict[str, Any], *, attempt: int) -> None:
    headers = _redact_headers({k: v for k, v in kwargs.get("headers", {}).items()})
    params = kwargs.get("params")
    body = None
    if "json" in kwargs:
        body = _serialise_body(kwargs.get("json"))
    elif "data" in kwargs:
        body = _serialise_body(kwargs.get("data"))
    logger.debug(
        "API request",
        extra={
            "method": method,
            "url": url,
            "attempt": attempt,
            "headers": headers,
            "params": params,
            "body": body,
        },
    )


def _log_response(response: Response, *, attempt: int) -> None:
    content_type = response.headers.get("Content-Type", "")
    body: Optional[str]
    if content_type.startswith("application/json"):
        try:
            body = _serialise_body(response.json())
        except ValueError:
            body = _trim_body(response.text)
    else:
        body = _trim_body(response.text)
    logger.debug(
        "API response",
        extra={
            "status_code": response.status_code,
            "attempt": attempt,
            "body": body,
        },
    )


class _FileLock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: Optional[int] = None

    def __enter__(self) -> "_FileLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        self._fd = fd
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


class AuthTokenManager:
    _instance: Optional["AuthTokenManager"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self.settings = get_settings()
        self._configured = all(
            [self.settings.auth_client_id, self.settings.auth_client_secret, self.settings.auth_token_url]
        )
        cache_path = self.settings.auth_token_cache_path
        if cache_path:
            self._cache_path = Path(cache_path)
        else:
            # Fallback to log root if cache path not supplied
            self._cache_path = Path(self.settings.log_root).resolve() / "auth_token.json"
        self._lock_path = self._cache_path.with_suffix(".lock")
        self._token: Optional[str] = None
        self._expires_at: float = 0.0
        self._local_lock = threading.Lock()
        if self._configured:
            self._load_from_cache()

    @classmethod
    def instance(cls) -> "AuthTokenManager":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def is_configured(self) -> bool:
        return self._configured  # type: ignore[truthy-bool]

    def get_token(self, *, force_refresh: bool = False) -> Optional[str]:
        if not self.is_configured:
            return None
        with self._local_lock:
            if not force_refresh and self._token and time.time() < (self._expires_at - _TOKEN_SKEW_SECONDS):
                return self._token
        # Acquire process-wide lock before refreshing
        with _FileLock(self._lock_path):
            self._load_from_cache()
            if not force_refresh and self._token and time.time() < (self._expires_at - _TOKEN_SKEW_SECONDS):
                return self._token
            self._refresh_token_locked()
            return self._token

    def invalidate(self) -> None:
        with self._local_lock:
            self._token = None
            self._expires_at = 0.0
        try:
            self._cache_path.unlink(missing_ok=True)
        except OSError:
            logger.debug("Failed to remove auth token cache", exc_info=True)

    def _load_from_cache(self) -> None:
        try:
            data = json.loads(self._cache_path.read_text())
            token = data.get("token")
            expires_at = float(data.get("expires_at", 0))
            if token and time.time() < (expires_at - _TOKEN_SKEW_SECONDS):
                self._token = token
                self._expires_at = expires_at
            else:
                self._token = None
                self._expires_at = 0.0
        except FileNotFoundError:
            self._token = None
            self._expires_at = 0.0
        except (json.JSONDecodeError, ValueError):
            logger.debug("Invalid token cache contents", exc_info=True)
            self._token = None
            self._expires_at = 0.0

    def _refresh_token_locked(self) -> None:
        try:
            token, expires_in = self._request_token()
        except Exception:
            logger.exception("Failed to refresh auth token")
            self._token = None
            self._expires_at = 0.0
            return
        expires_at = time.time() + max(expires_in, 0)
        cache_payload = {"token": token, "expires_at": expires_at}
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(cache_payload))
        except OSError:
            logger.warning("Unable to persist auth token cache", exc_info=True)
        with self._local_lock:
            self._token = token
            self._expires_at = expires_at

    def _request_token(self) -> tuple[str, int]:
        headers: Dict[str, str] = {
            "Authorization": "Basic " + base64.b64encode(f"{self.settings.auth_client_id}:{self.settings.auth_client_secret}".encode()).decode(),
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {"grant_type": "client_credentials"}
        if self.settings.auth_token_scope:
            payload["scope"] = self.settings.auth_token_scope
        request_kwargs: Dict[str, Any] = {"headers": headers, "json": payload, "timeout": 15}
        attempt = 1
        _log_request("POST", self.settings.auth_token_url, request_kwargs, attempt=attempt)
        response = requests.post(self.settings.auth_token_url, **request_kwargs)
        _log_response(response, attempt=attempt)
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("access_token missing from token response")
        expires_in = int(data.get("expires_in", 3600))
        return token, expires_in

    def attach_auth_header(self, headers: Dict[str, str], *, force_refresh: bool = False) -> None:
        if not self.is_configured:
            return
        token = self.get_token(force_refresh=force_refresh)
        if token:
            headers["Authorization"] = f"Bearer {token}"


def request_with_auth(method: str, url: str, **kwargs) -> Response:
    manager = AuthTokenManager.instance()
    headers: Dict[str, str] = kwargs.setdefault("headers", {})
    if manager.is_configured:
        manager.attach_auth_header(headers)
    attempt = 1
    _log_request(method, url, kwargs, attempt=attempt)
    response = requests.request(method, url, **kwargs)
    _log_response(response, attempt=attempt)
    if manager.is_configured and response.status_code in (401, 403):
        attempt += 1
        try:
            manager.invalidate()
        except Exception:
            logger.debug("Failed to invalidate auth token", exc_info=True)
        headers = kwargs.setdefault("headers", {})
        manager.attach_auth_header(headers, force_refresh=True)
        _log_request(method, url, kwargs, attempt=attempt)
        response = requests.request(method, url, **kwargs)
        _log_response(response, attempt=attempt)
    return response


_startup_manager = AuthTokenManager.instance()
if _startup_manager.is_configured:
    try:
        _startup_manager.get_token(force_refresh=True)
    except Exception:
        logger.warning("Initial auth token fetch failed", exc_info=True)
