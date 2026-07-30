"""
agent.py (Groq version)
------------------------
Same agent loop concept as before, adapted to Groq's OpenAI-compatible
chat completions API:
  - tool schemas are wrapped as {"type": "function", "function": {...}}
  - the model returns response.choices[0].message.tool_calls (if any)
  - each tool_call.function.arguments is a JSON *string* -- must be parsed
  - tool results are sent back as their own {"role": "tool", ...} messages
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq
from tools import TOOL_SCHEMAS_GROQ, execute_tool

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Pick a current tool-capable model from https://console.groq.com/docs/models
# llama-3.3-70b-versatile is a solid general-purpose default; swap for a
# faster/smaller one (e.g. an 8B model) if you want lower latency.
MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_ITERATIONS = 8  # safety cap against infinite tool-calling loops

SYSTEM_PROMPT = """You are a helpful personal assistant with access to tools.
Use tools when they help answer the request accurately (e.g. current time,
weather, or reading/writing notes). If a task doesn't need a tool, just
answer directly. Be concise."""


def run_agent(user_message: str, history: list | None = None) -> tuple[str, list]:
    """
    Runs one full agent turn (which may include several tool calls).
    `history` is the prior message list (for multi-turn conversations).
    Returns (final_text_response, updated_history).
    """
    messages = list(history) if history else [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": user_message})

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS_GROQ,
            tool_choice="auto",
        )

        message = response.choices[0].message

        if not message.tool_calls:
            # Model gave a final answer -- no more tools needed.
            messages.append({"role": "assistant", "content": message.content})
            return message.content, messages

        # Record the assistant's tool-call request in history, then execute
        # every requested tool call and feed results back.
        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            }
        )

        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result = execute_tool(tool_call.function.name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result),
                }
            )

    return "Stopped: too many tool iterations without a final answer.", messages