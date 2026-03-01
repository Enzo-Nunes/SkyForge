import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

formatter = logging.Formatter("%(asctime)s - web - %(levelname)s - %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger = logging.getLogger("web")
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@asynccontextmanager
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
    profits: list[dict[str, Any]]
    calculated_at: str
    uptime_seconds: int | None = None


app = FastAPI(lifespan=lifespan)

# Active browser connections
_clients: set[WebSocket] = set()
_latest: ResultsPayload | None = None


async def _broadcast(payload: ResultsPayload) -> None:
    data = json.dumps(payload.model_dump())
    dead: set[WebSocket] = set()
    for ws in _clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


@app.post("/results")
async def post_results(payload: ResultsPayload) -> dict[str, int]:
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
    if _latest:
        await ws.send_text(json.dumps(_latest.model_dump()))
    try:
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"ping": True}))
    except (WebSocketDisconnect, asyncio.CancelledError) as exc:
        _clients.discard(ws)
        logger.info(f"Browser disconnected. Total clients: {len(_clients)}")
        if isinstance(exc, asyncio.CancelledError):
            raise


app.mount("/", StaticFiles(directory="static", html=True), name="static")
