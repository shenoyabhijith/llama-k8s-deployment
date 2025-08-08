import os
import json
import hashlib
import uuid
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from redis.asyncio import Redis


def get_env(name: str, default: str) -> str:
    value = os.getenv(name, default)
    return value


REDIS_URL = get_env("REDIS_URL", "redis://redis:6379/0")
RESULT_TTL_SECONDS = int(get_env("RESULT_TTL_SECONDS", "86400"))
CACHE_TTL_SECONDS = int(get_env("CACHE_TTL_SECONDS", "86400"))

app = FastAPI(title="LLM Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateJob(BaseModel):
    text: str
    max_tokens: int = 256
    temperature: float = 0.7
    stream: bool = True


def compute_cache_key(text: str, max_tokens: int, temperature: float) -> str:
    payload = json.dumps({"t": text, "m": max_tokens, "temp": temperature}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@app.on_event("startup")
async def on_startup() -> None:
    app.state.redis = Redis.from_url(REDIS_URL, decode_responses=True)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if hasattr(app.state, "redis"):
        await app.state.redis.close()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/jobs")
async def create_job(job: GenerateJob) -> dict:
    redis: Redis = app.state.redis
    request_id = uuid.uuid4().hex
    cache_key = compute_cache_key(job.text, job.max_tokens, job.temperature)

    # If cached, short-circuit and return request_id with immediate result path
    cached = await redis.get(f"cache:{cache_key}")
    if cached is not None:
        result_key = f"result:{request_id}"
        await redis.set(result_key, cached, ex=RESULT_TTL_SECONDS)
        # Also publish cached tokens to the token channel to keep UX consistent
        channel = f"tokens:{request_id}"
        try:
            data = json.loads(cached)
            text = data.get("response", "")
        except Exception:
            text = cached
        for token in text.split():
            await redis.publish(channel, token)
        await redis.publish(channel, "__DONE__")
        return {
            "request_id": request_id,
            "cached": True,
            "ws_url": f"/ws/{request_id}",
            "result_url": f"/result/{request_id}",
        }

    # Enqueue new job
    payload = {
        "request_id": request_id,
        "text": job.text,
        "max_tokens": job.max_tokens,
        "temperature": job.temperature,
        "cache_key": cache_key,
    }
    await redis.rpush("jobs", json.dumps(payload))
    return {
        "request_id": request_id,
        "cached": False,
        "ws_url": f"/ws/{request_id}",
        "result_url": f"/result/{request_id}",
    }


@app.get("/result/{request_id}")
async def fetch_result(request_id: str) -> dict:
    redis: Redis = app.state.redis
    data = await redis.get(f"result:{request_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Result not ready")
    try:
        return json.loads(data)
    except Exception:
        return {"response": data}


@app.websocket("/ws/{request_id}")
async def websocket_tokens(ws: WebSocket, request_id: str) -> None:
    await ws.accept()
    redis: Redis = app.state.redis
    pubsub = redis.pubsub()
    channel = f"tokens:{request_id}"
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if data == "__DONE__":
                await ws.send_text("[DONE]")
                break
            await ws.send_text(str(data))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            pass
        await pubsub.close()


