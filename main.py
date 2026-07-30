"""
main.py
-------
FastAPI wrapper around the agent. Keeps conversation history in memory per
session_id (swap this dict for a real DB — Postgres/SQLite — once you move
past prototyping).
"""

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from agent import run_agent

load_dotenv()

app = FastAPI(title="Jarvis-style Agent")

# session_id -> message history. In-memory only: resets on server restart.
SESSIONS: dict[str, list] = {}


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    history = SESSIONS.get(req.session_id, [])
    reply, updated_history = run_agent(req.message, history)
    SESSIONS[req.session_id] = updated_history
    return ChatResponse(reply=reply)


@app.get("/health")
def health():
    return {"status": "ok"}