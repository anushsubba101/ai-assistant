# Jarvis-style Agent — Stage 1 Scaffold

A minimal but real tool-calling agent built with FastAPI + the Anthropic API.
This is Stage 1 of the roadmap: text-based agent with real tools. No voice
yet, no long-term memory yet — just get the agent loop and tool mechanics
solid first.

## Setup

```bash
cd jarvis-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste in your GROQ_API_KEY (get one free at console.groq.com)
```

## Run

```bash
uvicorn main:app --reload
```

Then test it:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "me", "message": "What time is it, and what is the weather in Kathmandu?"}'
```

The model will call `get_current_time` and `get_weather` on its own, you'll
see the tool executions happen server-side, and you'll get back a single
final answer combining both.

Try the file tools too:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "me", "message": "Save a note called todo.txt with my grocery list: eggs, milk, bread"}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "me", "message": "What does my todo.txt note say?"}'
```

## Project layout

```
jarvis-agent/
├── main.py        # FastAPI app, /chat endpoint, session storage
├── agent.py        # The agent loop: call Claude, execute tools, repeat
├── tools.py        # Tool schemas + implementations (sandboxed file I/O, weather, time)
├── sandbox/        # Where read_file/write_file operate (safe, contained directory)
├── requirements.txt
└── .env.example
```

## How it works

1. `POST /chat` sends your message into `run_agent()`.
2. Claude either answers directly, or returns a `tool_use` block.
3. If it's a tool call, `execute_tool()` runs the matching Python function
   in `tools.py` and the result is sent back to Claude.
4. This repeats (capped at `MAX_TOOL_ITERATIONS`) until Claude gives a final
   text answer, which is returned to you.

Conversation history is kept in memory per `session_id` — restart the server
and it's gone. That's fine for prototyping; swap `SESSIONS` for a real
database when you're ready for Stage 3 (persistent memory).

## Adding your own tools

In `tools.py`:
1. Write a function `def my_tool(input: dict) -> str: ...`
2. Add a schema entry to `TOOL_SCHEMAS` describing name/params
3. Register it in `TOOL_EXECUTORS`

That's it — no other file needs to change. Good next tools to add for a
"Jarvis" feel: calendar lookup (Google Calendar API), sending a message
(email/Slack), or a controlled shell command runner (sandbox this heavily —
allowlist specific commands, don't allow arbitrary execution).

## Safety notes for this scaffold

- File tools are locked to `sandbox/` — path traversal is blocked.
- Tool iteration count is capped to prevent infinite loops.
- No destructive/irreversible tools are included yet (no shell exec, no
  "send email" for real) — add those deliberately, and consider requiring
  explicit user confirmation before executing anything irreversible.

## Next stages (once this works end-to-end)

- **Stage 2:** Add voice — Whisper for speech-to-text, ElevenLabs/Piper for
  text-to-speech, wrapping this same `/chat` endpoint.
- **Stage 3:** Swap in-memory `SESSIONS` for Postgres + a vector store
  (Chroma) for long-term memory/personalization.
- **Stage 4:** Wake-word detection for always-on listening (Porcupine).
- **Stage 5:** More tools — smart home (Home Assistant API), OS automation,
  proactive reminders.