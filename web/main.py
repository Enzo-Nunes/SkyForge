import asyncio
import contextlib
import json
import logging
import os
import secrets
import sys
import typing
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

formatter = logging.Formatter("%(asctime)s - web - %(levelname)s - %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger = logging.getLogger("web")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# /results is served on the public port, so only callers holding this per-start token may publish.
# It is shared with the calculator through a volume that is never exposed outside the compose network.
RESULTS_TOKEN_FILE = Path(os.getenv("RESULTS_TOKEN_FILE", "/run/skyforge/results_token"))
_results_token = secrets.token_urlsafe(32)
RESULTS_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
RESULTS_TOKEN_FILE.write_text(_results_token, encoding="utf-8")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    logger.info(f"Shutting down: notifying {len(_clients)} client(s)...")
    shutdown_payload = json.dumps({"type": "shutdown"})
    for ws in list(_clients):
        try:
            await ws.send_text(shutdown_payload)
            await ws.close()
        except Exception:
            pass
    _clients.clear()


class ResultsPayload(BaseModel):
    profits: list[dict[str, typing.Any]]
    calculated_at: str
    coverage_seconds: int | None = None


app = FastAPI(lifespan=lifespan)

# Active browser connections
_clients: set[WebSocket] = set()
_latest: ResultsPayload | None = None


async def _broadcast(payload: ResultsPayload) -> None:
    data = json.dumps(payload.model_dump())
    dead: set[WebSocket] = set()
    # Iterate over a copy: clients can connect or disconnect while a send is awaited.
    for ws in list(_clients):
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


@app.post("/results")
async def post_results(payload: ResultsPayload, authorization: str | None = Header(default=None)) -> dict[str, int]:
    if authorization is None or not secrets.compare_digest(authorization, f"Bearer {_results_token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    global _latest
    _latest = payload
    await _broadcast(payload)
    logger.info(f"Broadcast {len(payload.profits)} profit entries to {len(_clients)} client(s).")
    return {"broadcast_to": len(_clients)}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    logger.info(f"Browser connected. Total clients: {len(_clients)}")
    try:
        if _latest:
            await ws.send_text(json.dumps(_latest.model_dump()))
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"ping": True}))
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)
        logger.info(f"Browser disconnected. Total clients: {len(_clients)}")


app.mount("/", StaticFiles(directory="static", html=True), name="static")
