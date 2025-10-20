"""Simple FastAPI proxy to log webhook calls from Celery workers."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request, Response

LOG_FILE = Path("proxy_logs.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [proxy] %(message)s",
)
logger = logging.getLogger("proxy")

app = FastAPI(title="Celery Webhook Proxy", version="0.1.0")


def _append_log(entry: Dict[str, Any]) -> None:
    LOG_FILE.write_text("", encoding="utf-8") if not LOG_FILE.exists() else None
    with LOG_FILE.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")


@app.post("/webhooks/monday")
async def monday_webhook(request: Request) -> Dict[str, Any]:
    payload = await request.json()
    entry = {
        "received_at": datetime.utcnow().isoformat(),
        "path": str(request.url.path),
        "payload": payload,
    }
    _append_log(entry)
    logger.info("Received Monday webhook: %s", payload)
    return {"status": "ok"}


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def catch_all(full_path: str, request: Request) -> Response:
    body_bytes = await request.body()
    try:
        body_json = json.loads(body_bytes) if body_bytes else None
    except json.JSONDecodeError:
        body_json = None

    entry = {
        "received_at": datetime.utcnow().isoformat(),
        "method": request.method,
        "path": "/" + full_path,
        "query": dict(request.query_params),
        "headers": dict(request.headers),
        "body": body_json if body_json is not None else body_bytes.decode("utf-8", errors="ignore"),
    }
    _append_log(entry)
    logger.info("Logged request %s %s", request.method, "/" + full_path)
    return Response(content=json.dumps({"status": "logged"}), media_type="application/json")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    logger.debug("Incoming request %s %s body=%s", request.method, request.url.path, body)
    response: Response = await call_next(request)
    logger.debug(
        "Outgoing response %s status=%s", request.url.path, response.status_code
    )
    return response


@app.get("/logs")
async def get_logs() -> Response:
    content = LOG_FILE.read_text(encoding="utf-8") if LOG_FILE.exists() else ""
    return Response(content=content, media_type="text/plain")


@app.delete("/logs")
async def clear_logs() -> Dict[str, str]:
    LOG_FILE.unlink(missing_ok=True)
    return {"status": "cleared"}


@app.get("/healthz")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_proxy:app", host="0.0.0.0", port=8070, reload=False)
