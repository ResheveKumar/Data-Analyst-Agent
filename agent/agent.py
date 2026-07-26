"""
DataAnalystAgent: a natural-language -> SQL -> insight agent built on
NVIDIA's OpenAI-compatible NIM API. This is the centerpiece of the project —
it shows an agentic loop (not a single API call): the model can inspect the
schema, run a query, see the result (or an error), and decide whether to
refine the query or answer the user, up to a bounded number of steps.
"""

import json
import os
from openai import OpenAI

from agent.tools import get_schema, run_query, SQLValidationError

# Any NVIDIA NIM model that supports OpenAI-style tool calling works here.
# meta/llama-3.1-405b-instruct is a solid default; swap in something like
# nvidia/nemotron-3-super or nvidia/nemotron-3-ultra-550b-a55b if you want to
# try a different model from the catalog at build.nvidia.com.
MODEL = "llama-3.3-70b-versatile"
NVIDIA_BASE_URL = "https://api.groq.com/openai/v1"
MAX_AGENT_STEPS = 6

SYSTEM_PROMPT = """You are a data analyst agent. You answer business questions about an \
e-commerce database by writing and running read-only SQL queries, then explaining the \
result in plain language.

Rules:
- Always call get_database_schema before writing your first query in a conversation, \
unless you already have the schema in context.
- Only ever write SELECT queries. You cannot modify data.
- If a query fails or returns something unexpected, look at the error and try again \
with a corrected query rather than giving up.
- When you have enough information, give a clear, concise final answer in plain \
English. Include the concrete numbers. Don't just say "the query ran successfully."
- If the question is ambiguous (e.g. "recent" or "top" without a number), state the \
assumption you made (e.g. "last 90 days", "top 5") rather than asking a follow-up.
"""

# OpenAI-style tool/function schema (NVIDIA NIM's chat completions endpoint
# follows the OpenAI Chat Completions tool-calling format).
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_database_schema",
            "description": "Return the table and column definitions for the e-commerce database.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql_query",
            "description": (
                "Execute a read-only SELECT query against the e-commerce SQLite database "
                "and return the resulting rows. Only SELECT statements are allowed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A single SQL SELECT statement."}
                },
                "required": ["query"],
            },
        },
    },
]


class DataAnalystAgent:
    def __init__(self, api_key: str | None = None, verbose: bool = True):
        self.client = OpenAI(
            api_key=api_key or os.environ.get("GROQ_API_KEY"),
            base_url=NVIDIA_BASE_URL,
        )
        self.verbose = verbose

    def _log(self, message: str):
        if self.verbose:
            print(message)

    def _execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "get_database_schema":
            self._log("  [tool] get_database_schema()")
            return get_schema()

        if name == "run_sql_query":
            query = tool_input.get("query", "")
            self._log(f"  [tool] run_sql_query: {query}")
            try:
                result = run_query(query)
                return json.dumps(result)
            except SQLValidationError as e:
                return json.dumps({"error": str(e)})
            except Exception as e:  # sqlite errors, syntax errors, etc.
                return json.dumps({"error": f"Query failed: {e}"})

        return json.dumps({"error": f"Unknown tool: {name}"})

    def ask(self, question: str) -> str:
        """Run the agent loop for a single question and return the final text answer."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        for step in range(MAX_AGENT_STEPS):
            response = self.client.chat.completions.create(
                model=MODEL,
                max_tokens=1024,
                tools=TOOLS,
                messages=messages,
            )

            message = response.choices[0].message

            if not message.tool_calls:
                # Model gave a final text answer.
                return message.content or ""

            # Append assistant's turn (including tool_calls) to history.
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )

            # Execute every tool call requested and append each result.
            for tc in message.tool_calls:
                try:
                    tool_input = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_input = {}
                result_text = self._execute_tool(tc.function.name, tool_input)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    }
                )

        return "I wasn't able to reach a confident answer within the step limit. Try rephrasing the question."
