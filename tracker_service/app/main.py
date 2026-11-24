import json
import os

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.logic import build_progress_key, validate_and_calculate_progress

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

app = FastAPI(title="VaporShelf - Reading Tracker Service")


class ProgressUpdate(BaseModel):
    user_id: str
    current_page: int
    total_pages: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.put("/documents/{document_id}/progress")
def update_progress(document_id: str, progress: ProgressUpdate):
    try:
        percentage = validate_and_calculate_progress(
            progress.current_page, progress.total_pages
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    key = build_progress_key(progress.user_id, document_id)
    data = {
        "user_id": progress.user_id,
        "current_page": progress.current_page,
        "total_pages": progress.total_pages,
        "percentage": percentage,
    }
    r.set(key, json.dumps(data))
    return {"document_id": document_id, **data}


@app.get("/documents/{document_id}/progress")
def get_progress(document_id: str, user_id: str = "usr-102"):
    key = build_progress_key(user_id, document_id)
    raw = r.get(key)
    if not raw:
        raise HTTPException(status_code=404, detail="Progress not found")
    return {"document_id": document_id, **json.loads(raw)}
