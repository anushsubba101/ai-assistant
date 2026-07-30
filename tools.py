"""
tools.py
--------
Each tool has two parts:
1. A schema (tells the LLM what the tool does and what params it needs)
2. An executor function (the actual Python code that runs)

Add new tools by:
  a) adding an entry to TOOL_SCHEMAS
  b) adding a matching function to TOOL_EXECUTORS
"""

import os
import datetime
import httpx

# ---------------------------------------------------------------------------
# Sandbox: all file tools are locked to this directory so the agent can never
# read/write arbitrary paths on your machine.
# ---------------------------------------------------------------------------
SANDBOX_DIR = os.path.join(os.path.dirname(__file__), "sandbox")
os.makedirs(SANDBOX_DIR, exist_ok=True)


def _safe_path(filename: str) -> str:
    """Resolve a filename inside the sandbox dir, rejecting path traversal."""
    path = os.path.abspath(os.path.join(SANDBOX_DIR, filename))
    if not path.startswith(os.path.abspath(SANDBOX_DIR)):
        raise ValueError("Path traversal outside sandbox is not allowed.")
    return path


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def get_current_time(_input: dict) -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_weather(input: dict) -> str:
    """Uses Open-Meteo (free, no API key needed) via city geocoding."""
    city = input["city"]
    try:
        geo = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        ).json()
        if not geo.get("results"):
            return f"Could not find location: {city}"
        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]

        weather = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": True},
            timeout=10,
        ).json()
        cw = weather["current_weather"]
        return f"{city}: {cw['temperature']}°C, windspeed {cw['windspeed']} km/h"
    except Exception as e:
        return f"Error fetching weather: {e}"


def read_file(input: dict) -> str:
    path = _safe_path(input["filename"])
    if not os.path.exists(path):
        return f"File not found: {input['filename']}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(input: dict) -> str:
    path = _safe_path(input["filename"])
    with open(path, "w", encoding="utf-8") as f:
        f.write(input["content"])
    return f"Saved {input['filename']} ({len(input['content'])} chars)"


def list_files(_input: dict) -> str:
    files = os.listdir(SANDBOX_DIR)
    return "\n".join(files) if files else "(sandbox is empty)"


# ---------------------------------------------------------------------------
# Schemas the model sees. Descriptions matter a lot — be specific.
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "name": "get_current_time",
        "description": "Get the current date and time.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_weather",
        "description": "Get the current weather for a named city.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name"}},
            "required": ["city"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file from the agent's sandboxed notes directory.",
        "input_schema": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
        },
    },
    {
        "name": "write_file",
        "description": "Write/overwrite a file in the agent's sandboxed notes directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files currently in the agent's sandboxed notes directory.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

TOOL_EXECUTORS = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
}


def execute_tool(name: str, input: dict) -> str:
    if name not in TOOL_EXECUTORS:
        return f"Unknown tool: {name}"
    try:
        return TOOL_EXECUTORS[name](input)
    except Exception as e:
        return f"Tool '{name}' raised an error: {e}"


# ---------------------------------------------------------------------------
# Groq (and OpenAI-compatible APIs generally) expect tool schemas in a
# slightly different shape than Anthropic: {"type": "function", "function":
# {"name", "description", "parameters"}} instead of a flat
# {"name", "description", "input_schema"}. Keep TOOL_SCHEMAS above as the one
# source of truth and convert it here, rather than maintaining two lists.
# ---------------------------------------------------------------------------
def to_openai_format(schemas: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": s["name"],
                "description": s["description"],
                "parameters": s["input_schema"],
            },
        }
        for s in schemas
    ]


TOOL_SCHEMAS_GROQ = to_openai_format(TOOL_SCHEMAS)