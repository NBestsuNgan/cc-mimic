import asyncio
import json
import logging
import os
import re
import time
import tomllib
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import shutil

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
from pydantic import BaseModel

from src.agent.agent import Agent
from src.agent.events import AgentEventType
from src.agent.persistence import PersistenceManager
from src.config.config import ApprovalPolicy, Config
from src.config.loader import load_config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")

CONVEX_SITE_URL = os.environ.get("CONVEX_SITE_URL", "https://festive-salamander-172.convex.site")
# comma-separated; must list the exact Vercel origin in production
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
jwks = PyJWKClient(f"{CONVEX_SITE_URL}/api/auth/convex/jwks", cache_keys=True)
bearer = HTTPBearer()


def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        key = jwks.get_signing_key_from_jwt(cred.credentials).key
        return jwt.decode(
            cred.credentials,
            key,
            algorithms=["RS256"],
            audience="convex",
            issuer=CONVEX_SITE_URL,
        )
    except (jwt.PyJWTError, jwt.PyJWKClientError) as e:
        log.warning("auth failed: %s: %s", type(e).__name__, e)
        raise HTTPException(401, str(e))


WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", Path.cwd() / ".workspace"))


def _safe(part: str) -> str:
    """Reject anything that isn't a single path segment (traversal, separators, empty)."""
    if not part or part != Path(part).name or part in (".", ".."):
        raise HTTPException(400, "bad id")
    return part


def resolve_workspace(user_id: str, session_id: str | None) -> tuple[Path, str]:
    """New session when session_id is None; otherwise it must already exist under this user."""
    user_dir = WORKSPACE / _safe(user_id)
    if session_id is None:
        session_id = str(uuid.uuid4())
        ws = user_dir / session_id
        ws.mkdir(parents=True)
        return ws, session_id
    ws = user_dir / _safe(session_id)
    if not ws.is_dir():
        raise HTTPException(404, "unknown session")
    return ws, session_id


# ponytail: sessions live in this process's memory, so run one worker
# (`uvicorn app:app --workers 1`). Move to a broker + worker pool to scale out.
_sessions: dict[str, tuple[Agent, asyncio.Lock]] = {}


async def get_session(session_id: str, workspace: Path) -> tuple[Agent, asyncio.Lock]:
    """One long-lived Agent per chat — keeps context and MCP servers warm between turns.
    Config is read once here, so changing config.toml requires drop_session()."""
    if session_id not in _sessions:
        Config(cwd=workspace).initial_start_dir()
        config = load_config(workspace)
        config.cwd = workspace
        # No human on the other end of an HTTP request: safe commands only, never prompt.
        config.approval = ApprovalPolicy.NEVER
        agent = Agent(config=config, confirmation_callback=lambda _c: False)
        await agent.__aenter__()
        agent.session.session_id = session_id
        _sessions[session_id] = (agent, asyncio.Lock())
    return _sessions[session_id]


async def drop_session(session_id: str) -> None:
    """Shut an agent down so the next turn rebuilds it from the config on disk."""
    entry = _sessions.pop(session_id, None)
    if entry:
        try:
            await entry[0].__aexit__(None, None, None)
        except Exception:
            log.exception("closing agent %s", session_id)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    for session_id in list(_sessions):
        await drop_session(session_id)


app = FastAPI(lifespan=lifespan)


# ponytail: in-process fixed-window counter — fine for one worker on a small VM.
# Put Cloudflare or a real limiter in front if this ever sees serious traffic.
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MIN", "60"))
_hits: dict[str, tuple[int, int]] = {}


def rate_limited(client_ip: str) -> bool:
    """Runs before auth, so an unauthenticated flood costs a dict lookup, not a JWKS call."""
    minute = int(time.time() // 60)
    window, count = _hits.get(client_ip, (minute, 0))
    if window != minute:
        window, count = minute, 0
    count += 1
    _hits[client_ip] = (window, count)
    if len(_hits) > 10_000:  # bound memory: drop entries from earlier minutes
        for ip, (w, _) in list(_hits.items()):
            if w != minute:
                del _hits[ip]
    return count > RATE_LIMIT


# Registered before CORSMiddleware so CORS ends up outermost and a 429 still carries
# CORS headers — otherwise the browser reports an opaque CORS failure instead of 429.
@app.middleware("http")
async def limit_requests(request, call_next):
    # behind Caddy, so the real client address is in X-Forwarded-For
    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "?")
    if rate_limited(client_ip):
        log.warning("rate limited %s", client_ip)
        return Response("rate limit exceeded", status_code=429)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def is_secret(rel: Path) -> bool:
    """.env* is the only thing in a workspace that holds credentials. Everything else,
    .ai-agent/config.toml included, is meant to be readable — it's the demo."""
    return any(part.startswith(".env") for part in rel.parts)


def visible_files(workspace: Path) -> list[dict]:
    files = []
    for p in workspace.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(workspace)
        if is_secret(rel):
            continue
        files.append({"path": str(rel), "size": p.stat().st_size})
    files.sort(key=lambda f: f["path"])
    return files


MODELS_URL = "https://openrouter.ai/api/v1/models"
MODELS_TTL = 3600  # the catalogue changes rarely; don't hammer OpenRouter per page load
_models_cache: tuple[float, list[dict]] = (0.0, [])


async def free_tool_models() -> list[dict]:
    """Models that cost nothing for input AND output and can call tools —
    the same filter as openrouter.ai/models?max_price=0&max_output_price=0&supported_parameters=tools"""
    global _models_cache
    fetched_at, cached = _models_cache
    if cached and time.time() - fetched_at < MODELS_TTL:
        return cached

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(MODELS_URL)
        response.raise_for_status()
        data = response.json()["data"]

    models = [
        {
            "id": m["id"],
            "name": m.get("name") or m["id"],
            "context_length": m.get("context_length"),
        }
        for m in data
        if m.get("pricing", {}).get("prompt") == "0"
        and m.get("pricing", {}).get("completion") == "0"
        and "tools" in (m.get("supported_parameters") or [])
    ]
    models.sort(key=lambda m: m["name"].lower())
    _models_cache = (time.time(), models)
    return models


@app.get("/models")
async def get_models():
    try:
        models = await free_tool_models()
    except httpx.HTTPError as e:
        log.warning("openrouter model fetch failed: %s", e)
        raise HTTPException(502, "could not reach OpenRouter")
    return {"models": models}


CONFIG_REL = Path(".ai-agent") / "config.toml"


def read_config_model(workspace: Path) -> str | None:
    try:
        return tomllib.loads((workspace / CONFIG_REL).read_text()).get("model", {}).get("name")
    except (OSError, tomllib.TOMLDecodeError):
        return None


def write_config_model(workspace: Path, model: str) -> None:
    """Rewrite `name` inside the [model] table, leaving the rest of the file alone.
    `model` must already be allowlisted — see set_session_model."""
    path = workspace / CONFIG_REL
    text = path.read_text()

    def in_model_table(match: re.Match[str]) -> str:
        body = re.sub(
            r"(?m)^(\s*name\s*=\s*).*$", lambda m: f'{m.group(1)}"{model}"', match.group(2), count=1
        )
        return match.group(1) + body

    updated, count = re.subn(r"(?ms)^(\[model\]\s*?\n)(.*?)(?=^\[|\Z)", in_model_table, text, count=1)
    if not count or f'"{model}"' not in updated:
        raise HTTPException(500, "config.toml has no [model] name to update")
    tomllib.loads(updated)  # never write something we can't read back
    path.write_text(updated)


class ModelChoice(BaseModel):
    model: str

class ChatRequest(BaseModel):
    session_id: str | None = None  # omit to start a new conversation
    message: str


# Which key of AgentEvent.data carries the human-readable text, and who "said" it.
_TEXT = {
    AgentEventType.AGENT_START: ("message", "user"),
    AgentEventType.TEXT_DELTA: ("content", "assistant"),
    AgentEventType.TEXT_COMPLETE: ("content", "assistant"),
    AgentEventType.TOOL_CALL_START: ("name", "tool"),
    AgentEventType.TOOL_CALL_COMPLETE: ("output", "tool"),
    AgentEventType.AGENT_END: ("response", "assistant"),
    AgentEventType.AGENT_ERROR: ("error", "assistant"),
}


@app.put("/sessions/{session_id}/model")
async def set_session_model(session_id: str, choice: ModelChoice, user=Depends(current_user)):
    """Point this session's .ai-agent/config.toml at another model. The agent reads that
    file at startup, so the cached one is dropped and rebuilt on the next turn."""
    workspace, _ = resolve_workspace(user["sub"], session_id)

    # Allowlist: only ids OpenRouter reports as free + tool-capable. This is also what
    # keeps an arbitrary string out of the TOML we are about to write.
    try:
        allowed = {m["id"] for m in await free_tool_models()}
    except httpx.HTTPError:
        raise HTTPException(502, "could not reach OpenRouter to verify the model")
    if choice.model not in allowed:
        raise HTTPException(400, "unknown or non-free model")

    Config(cwd=workspace).initial_start_dir()  # no-op if config.toml already exists
    write_config_model(workspace, choice.model)
    await drop_session(session_id)
    return {"model": choice.model}


@app.get("/sessions")
async def list_sessions(user=Depends(current_user)):
    """Every session this user owns, newest first. The workspace dirs are the source of
    truth — they're created by resolve_workspace and already scoped per user."""
    user_dir = WORKSPACE / _safe(user["sub"])
    if not user_dir.is_dir():
        return {"sessions": []}
    sessions = [
        {
            "session_id": d.name,
            "updated_at": d.stat().st_mtime,
            "file_count": len(visible_files(d)),
            "model": read_config_model(d),
        }
        for d in user_dir.iterdir()
        if d.is_dir() and not d.is_symlink()
    ]
    sessions.sort(key=lambda s: s["updated_at"], reverse=True)
    return {"sessions": sessions}


@app.get("/sessions/{session_id}/messages")
async def session_messages(session_id: str, user=Depends(current_user)):
    """Replay a past conversation. resolve_workspace 404s unless the caller owns it."""
    user_id = user["sub"]
    resolve_workspace(user_id, session_id)
    snapshot = PersistenceManager().load_session(session_id)
    if not snapshot:
        return {"messages": []}
    return {
        "messages": [
            {
                "user_id": user_id,
                "session_id": session_id,
                "role": m["role"],
                "message": m.get("content") or "",
            }
            for m in snapshot.messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
    }


@app.get("/sessions/{session_id}/files")
async def list_files(session_id: str, user=Depends(current_user)):
    """resolve_workspace 404s unless this session belongs to the caller."""
    workspace, _ = resolve_workspace(user["sub"], session_id)
    return {"session_id": session_id, "files": visible_files(workspace)}


@app.get("/sessions/{session_id}/files/{path:path}")
async def download_file(session_id: str, path: str, user=Depends(current_user)):
    workspace, _ = resolve_workspace(user["sub"], session_id)
    # resolve() follows symlinks too, so the containment check catches both
    # ../.. traversal and a symlink pointing outside the workspace
    target = (workspace / path).resolve()
    if (
        not target.is_relative_to(workspace.resolve())
        or not target.is_file()
        or is_secret(target.relative_to(workspace.resolve()))
    ):
        raise HTTPException(404, "no such file")
    return FileResponse(target, filename=target.name)

@app.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, user=Depends(current_user)):
    """Drop the live agent, then remove the workspace. resolve_workspace 404s
    unless this session belongs to the caller."""
    workspace, _ = resolve_workspace(user["sub"], session_id)
    await drop_session(session_id)
    try:
        shutil.rmtree(workspace.resolve())
    except OSError as e:
        raise HTTPException(500, f"could not delete: {e}")
    return Response(status_code=204)


@app.post("/chat/completions")
async def chat(req: ChatRequest, user=Depends(current_user)):
    user_id = user["sub"]

    async def stream():
        session_id = ""

        def frame(event: str, message: str | None, role: str = "assistant") -> str:
            """Every frame is the same JSON shape; the `event:` line says which kind it is."""
            data = {"user_id": user_id, "session_id": session_id, "role": role, "message": message or ""}
            return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

        try:
            workspace, session_id = resolve_workspace(user_id, req.session_id)
            agent, lock = await get_session(session_id, workspace)
        except HTTPException as e:
            # headers already went out as 200 text/event-stream, so report this in-band
            yield frame("agent_error", str(e.detail))
            return

        # tells the client which session to send its next turn to
        yield frame("session", "", "system")
        if lock.locked():
            yield frame("agent_error", "session is already streaming a turn")
            return
        async with lock:
            try:
                async for event in agent.run(req.message, PersistenceManager()):
                    key, role = _TEXT[event.type]
                    yield frame(event.type.value, event.data.get(key), role)
            except asyncio.CancelledError:  # client hung up
                raise
            except Exception as e:
                log.exception("agent failed")
                yield frame("agent_error", f"{type(e).__name__}: {e}")

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
