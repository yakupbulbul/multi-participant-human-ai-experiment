import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from . import db
from .config import ExperimentConfig, load_config
from .engine import Lobby

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_config()  # invalid config.yml -> startup fails loudly
    cfg: ExperimentConfig = app.state.config
    # Server log only. Never expose participant kinds through any API or WebSocket payload.
    log.info("config ok: %d human slot(s), %d ai slot(s)", cfg.human_count, 3 - cfg.human_count)
    await db.init_db()
    app.state.lobby = Lobby(cfg)
    yield
    await app.state.lobby.reset()
    await db.engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict:
    # Deliberately no condition/participant info here (blind condition).
    return {"status": "ok", "db": await db.ping()}


if os.environ.get("DEV_MODE") == "1":

    @app.post("/api/dev/reset")
    async def dev_reset() -> dict:
        """Abort the live session and forget it. Only registered when DEV_MODE=1."""
        await app.state.lobby.reset()
        return {"status": "reset"}


@app.websocket("/ws/session")
async def ws_session(ws: WebSocket, token: str | None = None) -> None:
    """One participant connection. First message is the full state; then updates.

    Client -> server: {"type": "message", "content": str} | {"type": "vote", "candidate": "Player X"}
    Server -> client: {"type": "welcome", "token": str} once for a new join, then {"type": "state", ...}
    """
    await ws.accept()
    attached = await ws.app.state.lobby.attach(ws, token)
    if attached is None:
        await ws.send_json({"type": "error", "code": "session_in_progress"})
        await ws.close()
        return
    runner, player, new_token = attached
    try:
        if new_token is not None:
            await ws.send_json({"type": "welcome", "token": new_token})
        await ws.send_json(runner.state_for(player))  # snapshot on every connect
        await runner.broadcast()  # tell the others (count / reconnect)
        while True:
            try:
                data = await ws.receive_json()
            except ValueError:
                continue  # not JSON: ignore
            if not isinstance(data, dict):
                continue
            if data.get("type") == "message":
                await runner.submit_message(player, str(data.get("content", "")))
            elif data.get("type") == "vote":
                await runner.submit_vote(player, str(data.get("candidate", "")))
    except WebSocketDisconnect:
        pass
    finally:
        await runner.detach(player, ws)
