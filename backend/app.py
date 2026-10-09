"""Run with: uvicorn backend.app:app --reload --port 8000"""
from __future__ import annotations

from threading import Lock
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.economy import Economy, PUBLIC_SPEC, VARIANTS

app = FastAPI(title='Game Economy Sandbox API', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:8501', 'http://127.0.0.1:8501'], allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
SESSIONS: dict[str, Economy] = {}
LOCK = Lock()


class CreateSession(BaseModel):
    variant: str = 'secure'


class PerformAction(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


def get_session(session_id: str) -> Economy:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return session


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.get('/api/spec')
def spec():
    return PUBLIC_SPEC


@app.post('/api/sessions')
def new_session(req: CreateSession):
    if req.variant not in VARIANTS:
        raise HTTPException(status_code=400, detail=f'variant must be one of {VARIANTS}')
    with LOCK:
        sid = str(uuid4())
        SESSIONS[sid] = Economy(variant=req.variant)
        return {'session_id': sid, 'state': SESSIONS[sid].observable()}


@app.get('/api/sessions/{session_id}')
def session_state(session_id: str):
    with LOCK:
        return {'session_id': session_id, 'state': get_session(session_id).observable()}


@app.post('/api/sessions/{session_id}/actions')
def do_action(session_id: str, req: PerformAction):
    with LOCK:
        session = get_session(session_id)
        try:
            return session.perform(req.action, req.params)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
